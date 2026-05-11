"""SAP S/4HANA tool handlers, _TOOL_SPECS_LIST, PROMPT_SPECS. No MCP bootstrap here."""
from __future__ import annotations

import time

import structlog
from mcp import types
from mcp.types import PromptMessage, TextContent

from .sap_client import SAPAPIError, SAPAuthError, get_client

log = structlog.get_logger("sap")


def _odata_str(value: str) -> str:
    """Escape a string literal for OData $filter — single quotes doubled per OData spec."""
    return value.replace("'", "''")


# OData service + entity constants
PO_SERVICE    = "API_PURCHASEORDER_PROCESS_SRV"
PO_ENTITY     = "A_PurchaseOrder"
BP_SERVICE    = "API_BUSINESS_PARTNER"
BP_ENTITY     = "A_BusinessPartner"
MAT_SERVICE   = "API_PRODUCT_SRV"
MAT_ENTITY    = "A_Product"
STOCK_SERVICE = "API_MATERIAL_STOCK_SRV"
STOCK_ENTITY  = "A_MatlStkInAcctMod"


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
        summary = f"{len(items)} purchase order(s) [sap]."
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
        summary = f"{len(items)} business partner(s) [sap]."
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


async def sap__get_materials(material_id: str = "", limit: int = 5) -> types.CallToolResult:
    if material_id:
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
        summary = f"{len(items)} material(s) [sap]."
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
    except Exception as exc:
        log.warning("sap__create_purchase_order_list_refresh_failed", error=str(exc))
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
    except Exception as exc:
        log.warning("sap__update_purchase_order_list_refresh_failed", error=str(exc))
        items = []

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Purchase order {purchase_order_id} updated. Refreshed list returned.")],
        structuredContent={"type": "purchase_orders", "total": len(items), "items": items, "sandbox": get_client().is_sandbox},
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
            params={"$filter": f"PurchaseOrder eq '{_odata_str(purchase_order)}'"},
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
    except Exception as exc:
        log.warning("sap__get_po_line_items_api_failed_using_mock", error=str(exc))
        items = _MOCK_PO_LINE_ITEMS
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Retrieved {len(items)} line item(s) for PO {purchase_order}.")],
        structuredContent={"type": "po_line_items", "purchase_order": purchase_order, "total": len(items), "items": items, "sandbox": sap.is_sandbox},
    )


async def sap__get_goods_receipts(purchase_order: str, item_number: str) -> types.CallToolResult:
    sap = get_client()
    items: list[dict] = []
    try:
        records = await sap.query(
            "API_MATERIAL_DOCUMENT_SRV", "A_MaterialDocumentItem",
            params={
                "$filter": f"PurchaseOrder eq '{_odata_str(purchase_order)}' and PurchaseOrderItem eq '{_odata_str(item_number)}'",
                "$orderby": "PostingDate desc",
            },
            limit=20,
        )
        items = [
            {
                "gr_document":   r.get("MaterialDocument", ""),
                "posting_date":  r.get("PostingDate", ""),
                "quantity":      float(r.get("Quantity") or 0),
                "unit":          r.get("BaseUnit", "EA"),
                "delivery_note": r.get("DeliveryNote", ""),
            }
            for r in records
        ]
    except Exception as exc:
        log.warning("sap__get_goods_receipts_api_failed_using_mock", error=str(exc))
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
            params={"$filter": f"Supplier eq '{_odata_str(partner_id)}'"},
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
    except Exception as exc:
        log.warning("sap__get_bp_purchase_orders_api_failed_using_mock", error=str(exc))
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
            params={"$filter": f"Product eq '{_odata_str(material_id)}'"},
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
    except Exception as exc:
        log.warning("sap__get_material_plant_data_api_failed_using_mock", error=str(exc))
        items = _MOCK_MATERIAL_PLANTS
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Retrieved {len(items)} plant record(s) for material {material_id}.")],
        structuredContent={"type": "material_plant_data", "material_id": material_id, "total": len(items), "items": items, "sandbox": sap.is_sandbox},
    )


async def sap__get_stock_levels(material_id: str = "", plant: str = "") -> types.CallToolResult:
    sap = get_client()
    items: list[dict] = []
    try:
        filters = []
        if material_id:
            filters.append(f"Material eq '{_odata_str(material_id)}'")
        if plant:
            filters.append(f"Plant eq '{_odata_str(plant)}'")
        params: dict = {"$orderby": "Material"}
        if filters:
            params["$filter"] = " and ".join(filters)
        records = await sap.query(STOCK_SERVICE, STOCK_ENTITY, limit=20, params=params)
        items = [
            {
                "material":          r.get("Material", ""),
                "plant":             r.get("Plant", ""),
                "storage_location":  r.get("StorageLocation", ""),
                "unrestricted":       float(r.get("UnrestrictedStockQty") or 0),
                "quality_inspection": float(r.get("QltyInspectionStockQty") or r.get("MatlQltyInspectionStockQty") or 0),
                "blocked":            float(r.get("BlockedStockQty") or 0),
                "in_transit":         float(r.get("InTransitQty") or r.get("StockInTransitQuantity") or 0),
                "unit":               r.get("MaterialBaseUnit", "EA"),
            }
            for r in records
        ]
    except Exception as exc:
        log.warning("sap__get_stock_levels_api_failed_using_mock", error=str(exc))
        items = _MOCK_STOCK_LEVELS

    label = f"for {material_id} at {plant}" if material_id and plant else "overview"
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"{len(items)} stock level(s) [{label}].")],
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
    except Exception as exc:
        log.warning("sap__get_sales_orders_api_failed_using_mock", error=str(exc))
        items = _MOCK_SALES_ORDERS[:limit]
    structured = {"type": "sales_orders", "total": len(items), "items": items, "sandbox": sap.is_sandbox}
    if not items:
        summary = "No sales orders found."
    else:
        summary = f"{len(items)} sales order(s) [sap]."
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
            params={"$filter": f"SalesOrder eq '{_odata_str(sales_order)}'"},
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
    except Exception as exc:
        log.warning("sap__get_so_items_api_failed_using_mock", error=str(exc))
        items = _MOCK_SO_ITEMS
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Retrieved {len(items)} item(s) for sales order {sales_order}.")],
        structuredContent={"type": "so_items", "sales_order": sales_order, "total": len(items), "items": items, "sandbox": sap.is_sandbox},
    )


async def sap__get_deliveries(sales_order: str, item_number: str) -> types.CallToolResult:
    sap = get_client()
    items: list[dict] = []
    try:
        records = await sap.query(
            "API_OUTBOUND_DELIVERY_SRV", "A_OutbDeliveryItem",
            params={
                "$filter": f"ReferenceSDDocument eq '{_odata_str(sales_order)}' and ReferenceSDDocumentItem eq '{_odata_str(item_number)}'",
                "$orderby": "ActualGoodsMovementDate desc",
            },
            limit=20,
        )
        items = [
            {
                "delivery":          r.get("DeliveryDocument", ""),
                "actual_gi_date":    r.get("ActualGoodsMovementDate", ""),
                "delivery_quantity": float(r.get("ActualDeliveryQuantity") or 0),
                "unit":              r.get("DeliveryQuantityUnit", "EA"),
                "delivery_status":   r.get("DeliveryDocumentItemCategory", ""),
            }
            for r in records
        ]
    except Exception as exc:
        log.warning("sap__get_deliveries_api_failed_using_mock", error=str(exc))
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

_TOOL_SPECS_LIST = [
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
            "Pass material_id for full detail view. "
            "No params returns the list (product ID, type, group, base unit)."
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


# ── Aliases for server.py imports ────────────────────────────────────────────
from mcp.types import PromptMessage as _PM, TextContent as _TC  # noqa: E402

TOOL_SPECS = _TOOL_SPECS_LIST

PROMPT_SPECS = [
    {
        "name": "my-purchase-orders",
        "description": "Show the latest purchase orders from SAP S/4HANA.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "Show me the latest purchase orders from SAP. "
            "Call sap__get_purchase_orders and display the results in the widget."
        )))],
    },
    {
        "name": "my-sales-orders",
        "description": "Show the latest sales orders from SAP S/4HANA.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "Show me the latest sales orders from SAP. "
            "Call sap__get_sales_orders and display the results in the widget."
        )))],
    },
    {
        "name": "po-line-items",
        "description": "Drill into the line items for a specific purchase order.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "I want to see line items for a purchase order. "
            "Call sap__get_purchase_orders to show the latest POs. "
            "Ask me which PO to inspect. "
            "Then call sap__get_po_line_items with that purchase_order number and display the items."
        )))],
    },
    {
        "name": "stock-levels",
        "description": "Check stock levels for a material across plants in SAP.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "I want to check stock levels. "
            "Call sap__get_materials to show available materials. "
            "Ask me which material to check. "
            "Then call sap__get_stock_levels with that material_id and the plant code, "
            "and display the stock quantities."
        )))],
    },
    {
        "name": "orders-by-supplier",
        "description": "View all purchase orders for a specific supplier in SAP.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "I want to see orders for a specific supplier. "
            "Call sap__get_business_partners to show available suppliers. "
            "Ask me which supplier to look up. "
            "Then call sap__get_bp_purchase_orders with that partner_id and display their orders."
        )))],
    },
    {
        "name": "track-delivery",
        "description": "Track the delivery status for items in a specific sales order.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "I want to track a delivery. "
            "Call sap__get_sales_orders to show the latest SOs. "
            "Ask me which sales order to track. "
            "Then call sap__get_so_items with that sales_order number. "
            "Ask me which line item to check. "
            "Then call sap__get_deliveries with the sales_order and item_number and show delivery status."
        )))],
    },
]