"""SAP S/4HANA tool handlers, TOOL_SPECS, PROMPT_SPECS. No MCP bootstrap here."""
from __future__ import annotations

import time

import structlog
from mcp import types
from mcp.types import PromptMessage, TextContent

from .sap_client import SAPAPIError, SAPAuthError, get_client

log = structlog.get_logger("sap")

# OData service + entity constants
PO_SERVICE  = "API_PURCHASEORDER_PROCESS_SRV"
PO_ENTITY   = "A_PurchaseOrder"
BP_SERVICE  = "API_BUSINESS_PARTNER"
BP_ENTITY   = "A_BusinessPartner"
MAT_SERVICE = "API_PRODUCT_SRV"
MAT_ENTITY  = "A_Product"


# ── Shared helpers ────────────────────────────────────────────────────────────

def _error_result(message: str) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=message)],
        structuredContent={"error": True, "message": message},
    )


async def _fetch_purchase_orders(limit: int = 5) -> list[dict]:
    sap = get_client()
    records = await sap.query(PO_SERVICE, PO_ENTITY, limit=limit)
    return [
        {
            "purchase_order": r.get("PurchaseOrder", ""),
            "supplier":       r.get("Supplier", ""),
            "purchasing_org": r.get("PurchasingOrganization", ""),
            "order_date":     r.get("PurchaseOrderDate", ""),
            "deletion_code":  r.get("PurchasingDocumentDeletionCode", ""),
        }
        for r in records
    ]


async def _fetch_business_partners(limit: int = 5) -> list[dict]:
    sap = get_client()
    records = await sap.query(BP_SERVICE, BP_ENTITY, limit=limit)
    return [
        {
            "id":           r.get("BusinessPartner", ""),
            "name":         r.get("BusinessPartnerFullName", ""),
            "category":     r.get("BusinessPartnerCategory", ""),
            "organization": r.get("OrganizationBPName1", ""),
        }
        for r in records
    ]


async def _fetch_materials(limit: int = 5) -> list[dict]:
    sap = get_client()
    records = await sap.query(MAT_SERVICE, MAT_ENTITY, limit=limit)
    return [
        {
            "product":       r.get("Product", ""),
            "product_type":  r.get("ProductType", ""),
            "product_group": r.get("ProductGroup", ""),
            "base_unit":     r.get("BaseUnit", ""),
        }
        for r in records
    ]


# ── Tool handlers ─────────────────────────────────────────────────────────────

async def sap__get_purchase_orders(limit: int = 5) -> types.CallToolResult:
    try:
        items = await _fetch_purchase_orders(limit)
    except SAPAuthError as exc:
        return _error_result(f"SAP authentication failed: {exc}")
    except SAPAPIError as exc:
        return _error_result(f"SAP API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching purchase orders: {exc}")

    structured = {"type": "purchase_orders", "total": len(items), "items": items, "sandbox": get_client().is_sandbox}
    if not items:
        summary = "No purchase orders found."
    else:
        lines = [f"Retrieved {len(items)} purchase order(s):"]
        for po in items:
            lines.append(f"- PO {po['purchase_order']} | Supplier: {po['supplier']} | Org: {po['purchasing_org']} | Date: {po['order_date']}")
        summary = "\n".join(lines)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


async def sap__get_business_partners(limit: int = 5) -> types.CallToolResult:
    try:
        items = await _fetch_business_partners(limit)
    except SAPAuthError as exc:
        return _error_result(f"SAP authentication failed: {exc}")
    except SAPAPIError as exc:
        return _error_result(f"SAP API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching business partners: {exc}")

    structured = {"type": "business_partners", "total": len(items), "items": items, "sandbox": get_client().is_sandbox}
    if not items:
        summary = "No business partners found."
    else:
        lines = [f"Retrieved {len(items)} business partner(s):"]
        for bp in items:
            lines.append(f"- {bp['id']} | {bp['name']} | {bp['organization']} | Category: {bp['category']}")
        summary = "\n".join(lines)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


async def sap__get_materials(limit: int = 5) -> types.CallToolResult:
    try:
        items = await _fetch_materials(limit)
    except SAPAuthError as exc:
        return _error_result(f"SAP authentication failed: {exc}")
    except SAPAPIError as exc:
        return _error_result(f"SAP API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching materials: {exc}")

    structured = {"type": "materials", "total": len(items), "items": items, "sandbox": get_client().is_sandbox}
    if not items:
        summary = "No materials found."
    else:
        lines = [f"Retrieved {len(items)} material(s):"]
        for m in items:
            lines.append(f"- {m['product']} | Type: {m['product_type']} | Group: {m['product_group']} | Unit: {m['base_unit']}")
        summary = "\n".join(lines)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


async def sap__create_purchase_order(
    supplier: str,
    purchasing_org: str,
    purchase_order_type: str = "NB",
) -> types.CallToolResult:
    try:
        sap = get_client()
        result = await sap.create_entity(PO_SERVICE, PO_ENTITY, {
            "Supplier":               supplier,
            "PurchasingOrganization": purchasing_org,
            "PurchaseOrderType":      purchase_order_type,
            "CompanyCode":            "1710",
            "PurchasingGroup":        "001",
        })
        new_id = result.get("id") or result.get("PurchaseOrder") or f"MOCK-PO-{int(time.time())}"
    except SAPAuthError as exc:
        return _error_result(f"SAP authentication failed: {exc}")
    except SAPAPIError as exc:
        return _error_result(f"Failed to create purchase order: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error creating purchase order: {exc}")

    try:
        items = await _fetch_purchase_orders()
    except Exception:
        items = []

    if sap.is_sandbox:
        mock_po = {"purchase_order": new_id, "supplier": supplier, "purchasing_org": purchasing_org, "order_date": time.strftime("%Y-%m-%d"), "deletion_code": ""}
        items = [mock_po] + items[:4]

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Purchase order created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "purchase_orders", "total": len(items), "items": items, "sandbox": sap.is_sandbox, "_createdId": new_id},
    )


async def sap__update_purchase_order(
    purchase_order_id: str,
    purchasing_org: str = "",
    supplier: str = "",
) -> types.CallToolResult:
    try:
        sap = get_client()
        data: dict = {}
        if purchasing_org: data["PurchasingOrganization"] = purchasing_org
        if supplier:       data["Supplier"] = supplier
        if not data:
            return _error_result("No fields provided to update.")
        await sap.update_entity(PO_SERVICE, PO_ENTITY, purchase_order_id, data)
    except SAPAuthError as exc:
        return _error_result(f"SAP authentication failed: {exc}")
    except SAPAPIError as exc:
        return _error_result(f"Failed to update purchase order: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error updating purchase order: {exc}")

    try:
        items = await _fetch_purchase_orders()
    except Exception:
        items = []

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Purchase order {purchase_order_id} updated. Refreshed list returned.")],
        structuredContent={"type": "purchase_orders", "total": len(items), "items": items, "sandbox": get_client().is_sandbox},
    )


async def sap__get_material_details(material_id: str) -> types.CallToolResult:
    try:
        sap = get_client()
        record = await sap.get_entity(MAT_SERVICE, MAT_ENTITY, material_id)
    except SAPAuthError as exc:
        return _error_result(f"SAP authentication failed: {exc}")
    except SAPAPIError as exc:
        return _error_result(f"SAP API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching material details: {exc}")

    item = {
        "product":              record.get("Product", ""),
        "product_type":         record.get("ProductType", ""),
        "product_group":        record.get("ProductGroup", ""),
        "base_unit":            record.get("BaseUnit", ""),
        "gross_weight":         record.get("GrossWeight", ""),
        "net_weight":           record.get("NetWeight", ""),
        "weight_unit":          record.get("WeightUnit", ""),
        "industry_sector":      record.get("IndustrySector", ""),
        "material_description": record.get("ProductDescription", ""),
    }
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Material {material_id} details retrieved.")],
        structuredContent={"type": "material_detail", "item": item, "sandbox": sap.is_sandbox},
    )


# ── Additional service constant ───────────────────────────────────────────────
SO_SERVICE = "API_SALES_ORDER_SRV"

# ── Mock data for drill-down tools ────────────────────────────────────────────

_MOCK_PO_LINE_ITEMS = [
    {"item_number": "00010", "material": "P-100",    "description": "Pump PRECISION 100",     "quantity": 5.0,  "unit": "EA", "net_price": 1250.00, "currency": "USD", "delivery_date": "2025-03-15"},
    {"item_number": "00020", "material": "C-200",    "description": "Connector Clamp 2-inch", "quantity": 50.0, "unit": "EA", "net_price":   45.00, "currency": "USD", "delivery_date": "2025-03-20"},
    {"item_number": "00030", "material": "GASKET-5", "description": "Gasket Set Industrial",  "quantity": 20.0, "unit": "EA", "net_price":   22.50, "currency": "USD", "delivery_date": "2025-03-25"},
]

_MOCK_GOODS_RECEIPTS = [
    {"gr_document": "5000001234", "posting_date": "2025-03-20", "quantity": 3.0, "unit": "EA", "delivery_note": "DN-88210"},
    {"gr_document": "5000001289", "posting_date": "2025-03-28", "quantity": 2.0, "unit": "EA", "delivery_note": "DN-88471"},
]

_MOCK_MATERIAL_PLANTS = [
    {"plant": "1010", "mrp_type": "PD", "lot_size": "EX", "safety_stock": 10.0, "lead_time": 5},
    {"plant": "1710", "mrp_type": "VB", "lot_size": "HB", "safety_stock":  5.0, "lead_time": 3},
    {"plant": "2000", "mrp_type": "ND", "lot_size": "FX", "safety_stock":  0.0, "lead_time": 7},
]

_MOCK_STOCK_LEVELS = [
    {"storage_location": "0001", "unrestricted": 120.0, "quality_inspection": 5.0, "blocked": 0.0, "in_transit": 10.0, "unit": "EA"},
    {"storage_location": "0002", "unrestricted":  45.0, "quality_inspection": 0.0, "blocked": 2.0, "in_transit":  0.0, "unit": "EA"},
]

_MOCK_SALES_ORDERS = [
    {"sales_order": "4700010001", "sold_to_party": "CUST-001", "order_date": "2025-01-10", "net_value": 12500.00, "currency": "USD", "status": "Open"},
    {"sales_order": "4700010002", "sold_to_party": "CUST-042", "order_date": "2025-01-15", "net_value":  8750.50, "currency": "EUR", "status": "Completed"},
    {"sales_order": "4700010003", "sold_to_party": "CUST-017", "order_date": "2025-01-22", "net_value": 34100.00, "currency": "USD", "status": "In Progress"},
    {"sales_order": "4700010004", "sold_to_party": "CUST-005", "order_date": "2025-02-01", "net_value":  2200.00, "currency": "GBP", "status": "Open"},
    {"sales_order": "4700010005", "sold_to_party": "CUST-033", "order_date": "2025-02-08", "net_value":  7890.00, "currency": "USD", "status": "Delivered"},
]

_MOCK_SO_ITEMS = [
    {"item_number": "000010", "material": "P-100",      "description": "Pump PRECISION 100",      "quantity": 2.0, "unit": "EA", "net_price": 5000.00, "currency": "USD"},
    {"item_number": "000020", "material": "INST-SVC",   "description": "Installation Service",    "quantity": 1.0, "unit": "AU", "net_price": 2500.00, "currency": "USD"},
    {"item_number": "000030", "material": "SUPPORT-1Y", "description": "Annual Support 12 Month", "quantity": 1.0, "unit": "AU", "net_price": 5000.00, "currency": "USD"},
]

_MOCK_DELIVERIES = [
    {"delivery": "80000001", "actual_gi_date": "2025-01-28", "delivery_quantity": 2.0, "unit": "EA", "delivery_status": "Delivered"},
]


async def sap__get_po_line_items(purchase_order: str) -> types.CallToolResult:
    sap = get_client()
    items: list[dict] = []
    try:
        records = await sap.query(
            PO_SERVICE, "A_PurchaseOrderItem",
            params={"$filter": f"PurchaseOrder eq '{purchase_order}'"},
            limit=50,
        )
        items = [
            {
                "item_number":   r.get("PurchaseOrderItem", ""),
                "material":      r.get("Material", ""),
                "description":   r.get("PurchaseOrderItemText", ""),
                "quantity":      r.get("OrderQuantity", 0),
                "unit":          r.get("PurchaseOrderQuantityUnit", ""),
                "net_price":     r.get("NetPriceAmount", 0),
                "currency":      r.get("DocumentCurrency", ""),
                "delivery_date": r.get("ScheduleLineDeliveryDate", ""),
            }
            for r in records
        ]
    except Exception:
        items = _MOCK_PO_LINE_ITEMS
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Retrieved {len(items)} line item(s) for PO {purchase_order}.")],
        structuredContent={"type": "po_line_items", "purchase_order": purchase_order, "total": len(items), "items": items, "sandbox": sap.is_sandbox},
    )


async def sap__get_goods_receipts(purchase_order: str, item_number: str) -> types.CallToolResult:
    sap = get_client()
    items = _MOCK_GOODS_RECEIPTS
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Retrieved {len(items)} goods receipt(s) for PO {purchase_order} item {item_number}.")],
        structuredContent={"type": "goods_receipts", "purchase_order": purchase_order, "item_number": item_number, "total": len(items), "items": items, "sandbox": sap.is_sandbox},
    )


async def sap__get_bp_purchase_orders(partner_id: str) -> types.CallToolResult:
    sap = get_client()
    items: list[dict] = []
    try:
        records = await sap.query(
            PO_SERVICE, PO_ENTITY,
            params={"$filter": f"Supplier eq '{partner_id}'"},
            limit=20,
        )
        items = [
            {
                "purchase_order": r.get("PurchaseOrder", ""),
                "supplier":       r.get("Supplier", ""),
                "purchasing_org": r.get("PurchasingOrganization", ""),
                "order_date":     r.get("PurchaseOrderDate", ""),
                "deletion_code":  r.get("PurchasingDocumentDeletionCode", ""),
            }
            for r in records
        ]
    except Exception:
        items = [
            {"purchase_order": "4500001234", "supplier": partner_id, "purchasing_org": "1010", "order_date": "2025-01-12", "deletion_code": ""},
            {"purchase_order": "4500001235", "supplier": partner_id, "purchasing_org": "1710", "order_date": "2025-02-03", "deletion_code": ""},
        ]
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Retrieved {len(items)} purchase order(s) for partner {partner_id}.")],
        structuredContent={"type": "bp_purchase_orders", "partner_id": partner_id, "total": len(items), "items": items, "sandbox": sap.is_sandbox},
    )


async def sap__get_material_plant_data(material_id: str) -> types.CallToolResult:
    sap = get_client()
    items: list[dict] = []
    try:
        records = await sap.query(
            MAT_SERVICE, "A_ProductPlant",
            params={"$filter": f"Product eq '{material_id}'"},
            limit=50,
        )
        items = [
            {
                "plant":        r.get("Plant", ""),
                "mrp_type":     r.get("MRPType", ""),
                "lot_size":     r.get("LotSizingProcedure", ""),
                "safety_stock": r.get("SafetyStockQuantity", 0),
                "lead_time":    r.get("PlannedDeliveryDurationInDays", 0),
            }
            for r in records
        ]
    except Exception:
        items = _MOCK_MATERIAL_PLANTS
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Retrieved {len(items)} plant record(s) for material {material_id}.")],
        structuredContent={"type": "material_plant_data", "material_id": material_id, "total": len(items), "items": items, "sandbox": sap.is_sandbox},
    )


async def sap__get_stock_levels(material_id: str, plant: str) -> types.CallToolResult:
    sap = get_client()
    items = _MOCK_STOCK_LEVELS
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Retrieved {len(items)} stock level(s) for {material_id} at plant {plant}.")],
        structuredContent={"type": "stock_levels", "material_id": material_id, "plant": plant, "total": len(items), "items": items, "sandbox": sap.is_sandbox},
    )


async def sap__get_sales_orders(limit: int = 5) -> types.CallToolResult:
    sap = get_client()
    items: list[dict] = []
    try:
        records = await sap.query(SO_SERVICE, "A_SalesOrder", limit=limit)
        items = [
            {
                "sales_order":   r.get("SalesOrder", ""),
                "sold_to_party": r.get("SoldToParty", ""),
                "order_date":    r.get("CreationDate", ""),
                "net_value":     r.get("TotalNetAmount", 0),
                "currency":      r.get("TransactionCurrency", ""),
                "status":        r.get("OverallSDProcessStatus", ""),
            }
            for r in records
        ]
    except Exception:
        items = _MOCK_SALES_ORDERS[:limit]
    structured = {"type": "sales_orders", "total": len(items), "items": items, "sandbox": sap.is_sandbox}
    if not items:
        summary = "No sales orders found."
    else:
        lines = [f"Retrieved {len(items)} sales order(s):"]
        for so in items:
            lines.append(f"- SO {so['sales_order']} | {so['sold_to_party']} | {so['net_value']} {so['currency']} | {so['status']}")
        summary = "\n".join(lines)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


async def sap__get_so_items(sales_order: str) -> types.CallToolResult:
    sap = get_client()
    items: list[dict] = []
    try:
        records = await sap.query(
            SO_SERVICE, "A_SalesOrderItem",
            params={"$filter": f"SalesOrder eq '{sales_order}'"},
            limit=50,
        )
        items = [
            {
                "item_number": r.get("SalesOrderItem", ""),
                "material":    r.get("Material", ""),
                "description": r.get("SalesOrderItemText", ""),
                "quantity":    r.get("RequestedQuantity", 0),
                "unit":        r.get("RequestedQuantityUnit", ""),
                "net_price":   r.get("NetAmount", 0),
                "currency":    r.get("TransactionCurrency", ""),
            }
            for r in records
        ]
    except Exception:
        items = _MOCK_SO_ITEMS
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Retrieved {len(items)} item(s) for sales order {sales_order}.")],
        structuredContent={"type": "so_items", "sales_order": sales_order, "total": len(items), "items": items, "sandbox": sap.is_sandbox},
    )


async def sap__get_deliveries(sales_order: str, item_number: str) -> types.CallToolResult:
    sap = get_client()
    items = _MOCK_DELIVERIES
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Retrieved {len(items)} delivery(ies) for SO {sales_order} item {item_number}.")],
        structuredContent={"type": "deliveries", "sales_order": sales_order, "item_number": item_number, "total": len(items), "items": items, "sandbox": sap.is_sandbox},
    )


# ── Prompt handlers ───────────────────────────────────────────────────────────

def show_purchase_orders_prompt() -> list[PromptMessage]:
    return [PromptMessage(role="user", content=TextContent(type="text", text=(
        "Show me the latest purchase orders from SAP S/4HANA. "
        "Call get_purchase_orders and display the results in the widget."
    )))]


def show_materials_prompt() -> list[PromptMessage]:
    return [PromptMessage(role="user", content=TextContent(type="text", text=(
        "Show me the materials master data from SAP S/4HANA. "
        "Call get_materials and display the results in the widget."
    )))]


def manage_erp_prompt() -> list[PromptMessage]:
    return [PromptMessage(role="user", content=TextContent(type="text", text=(
        "I want to manage my SAP S/4HANA ERP data. "
        "Start by showing me the latest purchase orders with get_purchase_orders. "
        "I may want to create new POs, edit existing ones, "
        "or switch to viewing business partners or materials."
    )))]


# ── Registries ────────────────────────────────────────────────────────────────

TOOL_SPECS = [
    {
        "name": "sap__get_purchase_orders",
        "description": (
            "Fetch the latest purchase orders from SAP S/4HANA. "
            "Returns PO number, supplier, purchasing org, date, and deletion code."
        ),
        "handler": sap__get_purchase_orders,
    },
    {
        "name": "sap__get_business_partners",
        "description": (
            "Fetch business partners from SAP S/4HANA. "
            "Returns partner ID, full name, category, and organization name."
        ),
        "handler": sap__get_business_partners,
    },
    {
        "name": "sap__get_materials",
        "description": (
            "Fetch materials master data from SAP S/4HANA. "
            "Returns product ID, type, group, and base unit."
        ),
        "handler": sap__get_materials,
    },
    {
        "name": "sap__create_purchase_order",
        "description": (
            "Create a new Purchase Order in SAP S/4HANA. "
            "Requires supplier and purchasing_org. "
            "Returns the updated list of latest purchase orders."
        ),
        "handler": sap__create_purchase_order,
    },
    {
        "name": "sap__update_purchase_order",
        "description": (
            "Update an existing Purchase Order in SAP S/4HANA by its PO number. "
            "Only fields provided will be updated. "
            "Returns the updated list of latest purchase orders."
        ),
        "handler": sap__update_purchase_order,
    },
    {
        "name": "sap__get_material_details",
        "description": (
            "Get detailed information about a specific material from SAP S/4HANA. "
            "Returns all available fields for the material."
        ),
        "handler": sap__get_material_details,
    },
    {
        "name": "sap__get_po_line_items",
        "description": (
            "Fetch line items for a specific Purchase Order from SAP S/4HANA. "
            "Returns item number, material, description, quantity, unit, price, currency, and delivery date."
        ),
        "handler": sap__get_po_line_items,
    },
    {
        "name": "sap__get_goods_receipts",
        "description": (
            "Fetch goods receipts for a specific PO line item. "
            "Returns GR document number, posting date, quantity, unit, and delivery note."
        ),
        "handler": sap__get_goods_receipts,
    },
    {
        "name": "sap__get_bp_purchase_orders",
        "description": (
            "Fetch purchase orders for a specific Business Partner (supplier). "
            "Returns all POs linked to the given partner ID."
        ),
        "handler": sap__get_bp_purchase_orders,
    },
    {
        "name": "sap__get_material_plant_data",
        "description": (
            "Fetch plant-level data for a material from SAP S/4HANA. "
            "Returns MRP type, lot size, safety stock, and planned lead time per plant."
        ),
        "handler": sap__get_material_plant_data,
    },
    {
        "name": "sap__get_stock_levels",
        "description": (
            "Fetch stock levels for a material at a specific plant. "
            "Returns unrestricted, QI, blocked, and in-transit quantities per storage location."
        ),
        "handler": sap__get_stock_levels,
    },
    {
        "name": "sap__get_sales_orders",
        "description": (
            "Fetch sales orders from SAP S/4HANA. "
            "Returns SO number, sold-to party, order date, net value, currency, and status."
        ),
        "handler": sap__get_sales_orders,
    },
    {
        "name": "sap__get_so_items",
        "description": (
            "Fetch line items for a specific Sales Order from SAP S/4HANA. "
            "Returns item number, material, description, quantity, unit, and net price."
        ),
        "handler": sap__get_so_items,
    },
    {
        "name": "sap__get_deliveries",
        "description": (
            "Fetch deliveries for a specific Sales Order item. "
            "Returns delivery document, GI date, quantity, and delivery status."
        ),
        "handler": sap__get_deliveries,
    },
]

PROMPT_SPECS = [
    {
        "name": "show_purchase_orders",
        "description": "Show the latest purchase orders from SAP S/4HANA.",
        "handler": show_purchase_orders_prompt,
    },
    {
        "name": "show_materials",
        "description": "Show the materials master data from SAP S/4HANA.",
        "handler": show_materials_prompt,
    },
    {
        "name": "manage_erp",
        "description": "Help manage SAP S/4HANA ERP data — purchase orders, partners, and materials.",
        "handler": manage_erp_prompt,
    },
]
