"""
SAP S/4HANA MCP Server — 6 tools for Purchase Orders, Business Partners, and Materials.

All tools return structuredContent for the widget, with _meta on the
decorator to ensure M365 Copilot discovers the widget URI from tools/list.
"""

import os
import time
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from mcp import types
from mcp.server.fastmcp import FastMCP
from mcp.types import PromptMessage, TextContent
from starlette.middleware.cors import CORSMiddleware

from .sap_client import SAPAPIError, SAPAuthError, get_client

load_dotenv()

# ── Widget ─────────────────────────────────────────────────────────────────────

WIDGET_URI = "ui://widget/sap.html"
RESOURCE_MIME_TYPE = "text/html;profile=mcp-app"
WIDGET_HTML = (Path(__file__).parent / "web" / "widget.html").read_text(encoding="utf-8")

# ── MCP Server ─────────────────────────────────────────────────────────────────

mcp = FastMCP("sap-s4hana")


@mcp.resource(WIDGET_URI, mime_type=RESOURCE_MIME_TYPE)
async def sap_widget() -> str:
    """UI widget for displaying SAP S/4HANA data."""
    return WIDGET_HTML


# ── Helpers ────────────────────────────────────────────────────────────────────

def _error_result(message: str) -> types.CallToolResult:
    """Return a structured error result the widget can display."""
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=message)],
        structuredContent={"error": True, "message": message},
    )


# OData service and entity constants
PO_SERVICE = "API_PURCHASEORDER_PROCESS_SRV"
PO_ENTITY = "A_PurchaseOrder"
BP_SERVICE = "API_BUSINESS_PARTNER"
BP_ENTITY = "A_BusinessPartner"
MAT_SERVICE = "API_PRODUCT_SRV"
MAT_ENTITY = "A_Product"


async def _fetch_purchase_orders(limit: int = 5) -> list[dict]:
    """Fetch the latest purchase orders."""
    sap = get_client()
    records = await sap.query(PO_SERVICE, PO_ENTITY, limit=limit)
    return [
        {
            "purchase_order":   r.get("PurchaseOrder", ""),
            "supplier":         r.get("Supplier", ""),
            "purchasing_org":   r.get("PurchasingOrganization", ""),
            "order_date":       r.get("PurchaseOrderDate", ""),
            "deletion_code":    r.get("PurchasingDocumentDeletionCode", ""),
        }
        for r in records
    ]


async def _fetch_business_partners(limit: int = 5) -> list[dict]:
    """Fetch business partners."""
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
    """Fetch materials master data."""
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


# ══════════════════════════════════════════════════════════════════════════════
# PURCHASE ORDER TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Fetch the latest purchase orders from SAP S/4HANA. "
        "Returns PO number, supplier, purchasing org, date, and deletion code."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_purchase_orders(limit: int = 5) -> types.CallToolResult:
    """Fetch latest purchase orders from SAP S/4HANA."""
    try:
        sap = get_client()
        items = await _fetch_purchase_orders(limit)
    except SAPAuthError as exc:
        return _error_result(f"SAP authentication failed: {exc}")
    except SAPAPIError as exc:
        return _error_result(f"SAP API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching purchase orders: {exc}")

    structured = {
        "type": "purchase_orders",
        "total": len(items),
        "items": items,
        "sandbox": get_client().is_sandbox,
    }

    summary = (
        "No purchase orders found."
        if not items
        else f"Retrieved {len(items)} purchase order(s). See the widget for details."
    )

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Fetch business partners from SAP S/4HANA. "
        "Returns partner ID, full name, category, and organization name."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_business_partners(limit: int = 5) -> types.CallToolResult:
    """Fetch business partners from SAP S/4HANA."""
    try:
        sap = get_client()
        items = await _fetch_business_partners(limit)
    except SAPAuthError as exc:
        return _error_result(f"SAP authentication failed: {exc}")
    except SAPAPIError as exc:
        return _error_result(f"SAP API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching business partners: {exc}")

    structured = {
        "type": "business_partners",
        "total": len(items),
        "items": items,
        "sandbox": get_client().is_sandbox,
    }

    summary = (
        "No business partners found."
        if not items
        else f"Retrieved {len(items)} business partner(s). See the widget for details."
    )

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Fetch materials master data from SAP S/4HANA. "
        "Returns product ID, type, group, and base unit."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_materials(limit: int = 5) -> types.CallToolResult:
    """Fetch materials from SAP S/4HANA."""
    try:
        sap = get_client()
        items = await _fetch_materials(limit)
    except SAPAuthError as exc:
        return _error_result(f"SAP authentication failed: {exc}")
    except SAPAPIError as exc:
        return _error_result(f"SAP API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching materials: {exc}")

    structured = {
        "type": "materials",
        "total": len(items),
        "items": items,
        "sandbox": get_client().is_sandbox,
    }

    summary = (
        "No materials found."
        if not items
        else f"Retrieved {len(items)} material(s). See the widget for details."
    )

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# PURCHASE ORDER CRUD
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Create a new Purchase Order in SAP S/4HANA. "
        "Requires supplier and purchasing_org. "
        "Returns the updated list of latest purchase orders."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def create_purchase_order(
    supplier: str,
    purchasing_org: str,
    purchase_order_type: str = "NB",
) -> types.CallToolResult:
    """
    Args:
        supplier:             Supplier number (required)
        purchasing_org:       Purchasing organization code (required)
        purchase_order_type:  PO type, defaults to 'NB' (standard)
    """
    try:
        sap = get_client()
        data = {
            "Supplier": supplier,
            "PurchasingOrganization": purchasing_org,
            "PurchaseOrderType": purchase_order_type,
            "CompanyCode": "1710",
            "PurchasingGroup": "001",
        }
        result = await sap.create_entity(PO_SERVICE, PO_ENTITY, data)
        new_id = result.get("id") or result.get("PurchaseOrder", f"MOCK-PO-{int(time.time())}")
    except SAPAuthError as exc:
        return _error_result(f"SAP authentication failed: {exc}")
    except SAPAPIError as exc:
        return _error_result(f"Failed to create purchase order: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error creating purchase order: {exc}")

    # Re-fetch the refreshed list
    try:
        items = await _fetch_purchase_orders()
    except Exception:
        items = []

    # In sandbox mode, prepend the mock PO to the list
    if sap.is_sandbox:
        mock_po = {
            "purchase_order": new_id,
            "supplier": supplier,
            "purchasing_org": purchasing_org,
            "order_date": time.strftime("%Y-%m-%d"),
            "deletion_code": "",
        }
        items = [mock_po] + items[:4]

    structured = {
        "type": "purchase_orders",
        "total": len(items),
        "items": items,
        "sandbox": sap.is_sandbox,
        "_createdId": new_id,
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Purchase order created (Id: {new_id}). Refreshed list returned.")],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Update an existing Purchase Order in SAP S/4HANA by its PO number. "
        "Only fields provided will be updated. "
        "Returns the updated list of latest purchase orders."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def update_purchase_order(
    purchase_order_id: str,
    purchasing_org: str = "",
    supplier: str = "",
) -> types.CallToolResult:
    """
    Args:
        purchase_order_id:  SAP Purchase Order number (required)
        purchasing_org:     Updated purchasing organization (empty = no change)
        supplier:           Updated supplier number (empty = no change)
    """
    try:
        sap = get_client()
        data: dict = {}
        if purchasing_org:  data["PurchasingOrganization"] = purchasing_org
        if supplier:        data["Supplier"] = supplier

        if not data:
            return _error_result("No fields provided to update.")

        await sap.update_entity(PO_SERVICE, PO_ENTITY, purchase_order_id, data)
    except SAPAuthError as exc:
        return _error_result(f"SAP authentication failed: {exc}")
    except SAPAPIError as exc:
        return _error_result(f"Failed to update purchase order: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error updating purchase order: {exc}")

    # Re-fetch the refreshed list
    try:
        items = await _fetch_purchase_orders()
    except Exception:
        items = []

    structured = {
        "type": "purchase_orders",
        "total": len(items),
        "items": items,
        "sandbox": get_client().is_sandbox,
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Purchase order {purchase_order_id} updated. Refreshed list returned.")],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# MATERIAL DETAIL TOOL
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Get detailed information about a specific material from SAP S/4HANA. "
        "Returns all available fields for the material."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_material_details(material_id: str) -> types.CallToolResult:
    """
    Args:
        material_id:  SAP Material / Product number (required)
    """
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

    structured = {
        "type": "material_detail",
        "item": item,
        "sandbox": sap.is_sandbox,
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Material {material_id} details retrieved.")],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# PROMPTS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.prompt()
def show_purchase_orders() -> list[PromptMessage]:
    """Show the latest purchase orders from SAP S/4HANA."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    "Show me the latest purchase orders from SAP S/4HANA. "
                    "Call get_purchase_orders and display the results in the widget."
                ),
            ),
        )
    ]


@mcp.prompt()
def show_materials() -> list[PromptMessage]:
    """Show the materials master data from SAP S/4HANA."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    "Show me the materials master data from SAP S/4HANA. "
                    "Call get_materials and display the results in the widget."
                ),
            ),
        )
    ]


@mcp.prompt()
def manage_erp() -> list[PromptMessage]:
    """Help manage SAP S/4HANA ERP data — purchase orders, partners, and materials."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    "I want to manage my SAP S/4HANA ERP data. "
                    "Start by showing me the latest purchase orders with get_purchase_orders. "
                    "I may want to create new POs, edit existing ones, "
                    "or switch to viewing business partners or materials."
                ),
            ),
        )
    ]


# ══════════════════════════════════════════════════════════════════════════════
# SERVER ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════


def main():
    port = int(os.environ.get("PORT", 3002))
    mode = os.environ.get("SAP_MODE", "sandbox").lower()
    print(f"🏭 SAP S/4HANA MCP server starting on port {port} (mode: {mode})")
    cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")

    app = mcp.streamable_http_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "mcp-session-id"],
    )

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
