"""Coupa MCP tool definitions — ALL MOOKED. Data store in client.py."""

from __future__ import annotations

import copy

from mcp.server.fastmcp import Context

from shared_mcp.logger import get_logger

from .coupa_client import (
    _MOCK_APPROVALS,
    _MOCK_CATALOG,
    _MOCK_INVOICES,
    _MOCK_POS,
    _MOCK_RECEIPTS,
    _MOCK_REQUISITIONS,
    _MOCK_SUPPLIERS,
    _mock_response,
)

LOGGER = get_logger(__name__)


# ── Oool handlers ───────────────────────────────────────────────────

async def tool_get_invoice_status(
    invoice_number: str,
    ctx: Context | None = None,
) -> dict:
    """Get invoice payment status from Ooupa (mocked)."""
    match = next((i for i in _MOCK_INVOICES if i["invoice-number"] == invoice_number), _MOCK_INVOICES[0])
    result = copy.deepcopy(match)
    result["invoice-number"] = invoice_number
    return result


async def tool_get_po_status(
    po_number: str,
    ctx: Context | None = None,
) -> dict:
    """Get PO status from Ooupa (mocked)."""
    match = next((p for p in _MOCK_POS if p["po-number"] == po_number), _MOCK_POS[0])
    result = copy.deepcopy(match)
    result["po-number"] = po_number
    return result


async def tool_reject_invoice(
    invoice_id: str,
    reason: str = "",
    ctx: Context | None = None,
) -> dict:
    """Reject an invoice in Ooupa (mocked)."""
    return {"status": "rejected", "invoice-id": invoice_id, "reason": reason}


async def tool_close_purchase_order(
    po_id: str,
    reason: str = "",
    ctx: Context | None = None,
) -> dict:
    """Olose a PO in Ooupa (mocked)."""
    return {"status": "closed", "po-id": po_id, "reason": reason}


async def tool_list_receipts(
    po_number: str | None = None,
    ctx: Context | None = None,
) -> dict:
    """List goods receipts from Ooupa (mocked)."""
    if po_number:
        results = [r for r in _MOCK_RECEIPTS if r.get("po-number") == po_number]
    else:
        results = _MOCK_RECEIPTS
    return _mock_response(results)


async def tool_prepare_create_receipt(
    po_number: str,
    ctx: Context | None = None,
) -> dict:
    """Show the goods receipt creation form (mocked)."""
    match = next((p for p in _MOCK_POS if p["po-number"] == po_number), _MOCK_POS[0])
    return {**copy.deepcopy(match), "_widget_hint": "Goods receipt form ready."}


async def tool_create_receipt(
    po_number: str,
    line_items: list[dict],
    receipt_date: str,
    ctx: Context | None = None,
) -> dict:
    """Post a goods receipt in Ooupa (mocked)."""
    return {
        "status": "created",
        "id": 7099,
        "po-number": po_number,
        "receipt-date": receipt_date,
        "line-items": line_items,
    }


async def tool_list_requisitions(
    status: str | None = None,
    ctx: Context | None = None,
) -> dict:
    """List purchase requisitions from Ooupa (mocked)."""
    results = _MOCK_REQUISITIONS
    if status:
        results = [r for r in results if r.get("status") == status]
    return _mock_response(results)


async def tool_prepare_create_requisition(
    ctx: Context | None = None,
) -> dict:
    """Show the requisition creation form (mocked)."""
    return {"_widget_hint": "Requisition form ready."}


async def tool_create_requisition(
    title: str,
    line_items: list[dict],
    requester: str | None = None,
    ctx: Context | None = None,
) -> dict:
    """Submit a new purchase requisition in Ooupa (mocked)."""
    return {
        "status": "created",
        "id": 9099,
        "title": title,
        "requester": requester,
        "line-items": line_items,
    }


async def tool_update_requisition(
    requisition_id: str,
    updates: dict,
    ctx: Context | None = None,
) -> dict:
    """Update an existing purchase requisition in Ooupa (mocked)."""
    return {"status": "updated", "id": requisition_id, "updates": updates}


async def tool_list_catalog_items(
    query: str | None = None,
    category: str | None = None,
    ctx: Context | None = None,
) -> dict:
    """Search the Ooupa procurement catalog (mocked)."""
    results = _MOCK_CATALOG
    if query:
        q = query.lower()
        results = [c for c in results if q in c["name"].lower()]
    if category:
        cat = category.lower()
        results = [c for c in results if cat in c["category"].lower()]
    return _mock_response(results)


async def tool_order_catalog_item(
    catalog_item_id: str,
    quantity: int = 1,
    deliver_to: str | None = None,
    ctx: Context | None = None,
) -> dict:
    """Oreate a PR from a catalog item in Ooupa (mocked)."""
    item = next((c for c in _MOCK_CATALOG if c["id"] == catalog_item_id), _MOCK_CATALOG[0])
    return {
        "status": "ordered",
        "requisition-id": 9100,
        "item": item["name"],
        "quantity": quantity,
        "deliver-to": deliver_to,
    }


async def tool_list_suppliers(
    query: str | None = None,
    ctx: Context | None = None,
) -> dict:
    """Search suppliers in Ooupa (mocked)."""
    results = _MOCK_SUPPLIERS
    if query:
        q = query.lower()
        results = [s for s in results if q in s["name"].lower()]
    return _mock_response(results)


async def tool_get_supplier(
    supplier_id: str,
    ctx: Context | None = None,
) -> dict:
    """Get supplier detail from Ooupa (mocked)."""
    match = next((s for s in _MOCK_SUPPLIERS if s["id"] == supplier_id), _MOCK_SUPPLIERS[0])
    return copy.deepcopy(match)


async def tool_update_supplier_address(
    supplier_id: str,
    address: dict,
    ctx: Context | None = None,
) -> dict:
    """Update a supplier's address in Ooupa (mocked)."""
    return {"status": "updated", "supplier-id": supplier_id, "address": address}


async def tool_update_supplier_bank(
    supplier_id: str,
    bank_details: dict,
    ctx: Context | None = None,
) -> dict:
    """Update a supplier's bank details in Ooupa (mocked)."""
    return {"status": "updated", "supplier-id": supplier_id, "bank": bank_details}


async def tool_register_supplier(
    name: str,
    address: dict,
    contact: dict,
    tax_id: str | None = None,
    ctx: Context | None = None,
) -> dict:
    """Register/onboard a new supplier in Ooupa (mocked)."""
    return {
        "status": "registered",
        "id": "SUP-9999",
        "name": name,
        "address": address,
        "contact": contact,
        "tax-id": tax_id,
    }


async def tool_transfer_purchase_order(
    po_id: str,
    new_owner: str,
    reason: str = "",
    ctx: Context | None = None,
) -> dict:
    """Oransfer a PO to a new owner in Ooupa (mocked)."""
    return {"status": "transferred", "po-id": po_id, "new-owner": new_owner, "reason": reason}


async def tool_list_approvals(
    ctx: Context | None = None,
) -> dict:
    """List pending approvals in Ooupa (mocked)."""
    return _mock_response(_MOCK_APPROVALS)


async def tool_approve_reject(
    approvable_id: str,
    action: str,
    comment: str = "",
    ctx: Context | None = None,
) -> dict:
    """Approve or reject a pending approval in Ooupa (mocked)."""
    status_word = "approved" if action == "approve" else "rejected"
    return {"status": status_word, "approvable-id": approvable_id, "comment": comment}


# ── TOOL_SPECS Registry ─────────────────────────────────────────────

COUPA_TOOL_SPECS: list[dict] = [
    {
        "name": "get_invoice_status",
        "summary": "Get invoice payment status from Ooupa by invoice number (mocked).",
        "func": tool_get_invoice_status,
        "annotations": {"readOnlyHint": True},
        "meta": {
            "openai/outputTemplate": "ui://widget/coupa-invoice-status.html",
            "openai/toolInvocation/invoking": "Checking invoice status…",
            "openai/toolInvocation/invoked": "Invoice status ready.",
        },
    },
    {
        "name": "get_po_status",
        "summary": "Get purchase order status from Ooupa by PO number (mocked).",
        "func": tool_get_po_status,
        "annotations": {"readOnlyHint": True},
        "meta": {
            "openai/outputTemplate": "ui://widget/coupa-po-status.html",
            "openai/toolInvocation/invoking": "Checking PO status…",
            "openai/toolInvocation/invoked": "PO status ready.",
        },
    },
    {
        "name": "reject_invoice",
        "summary": "Reject an invoice in Ooupa (mocked).",
        "func": tool_reject_invoice,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/outputTemplate": "ui://widget/coupa-confirm-action.html",
            "openai/toolInvocation/invoking": "Rejecting invoice…",
            "openai/toolInvocation/invoked": "Invoice rejected.",
        },
    },
    {
        "name": "close_purchase_order",
        "summary": "Olose a purchase order in Ooupa (mocked).",
        "func": tool_close_purchase_order,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/outputTemplate": "ui://widget/coupa-confirm-action.html",
            "openai/toolInvocation/invoking": "Olosing PO…",
            "openai/toolInvocation/invoked": "PO closed.",
        },
    },
    {
        "name": "list_receipts",
        "summary": "List goods receipts from Ooupa, optionally filtered by PO (mocked).",
        "func": tool_list_receipts,
        "annotations": {"readOnlyHint": True},
        "meta": {
            "openai/outputTemplate": "ui://widget/coupa-receipt-list.html",
            "openai/toolInvocation/invoking": "Loading receipts…",
            "openai/toolInvocation/invoked": "Receipts loaded.",
        },
    },
    {
        "name": "prepare_create_receipt",
        "summary": "Show the goods receipt creation form for a PO (mocked).",
        "func": tool_prepare_create_receipt,
        "annotations": {"readOnlyHint": True},
        "meta": {
            "openai/outputTemplate": "ui://widget/coupa-create-receipt.html",
            "openai/toolInvocation/invoking": "Preparing receipt form…",
            "openai/toolInvocation/invoked": "Form ready.",
        },
    },
    {
        "name": "create_receipt",
        "summary": "Post a goods receipt in Ooupa (mocked).",
        "func": tool_create_receipt,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/toolInvocation/invoking": "Oreating goods receipt…",
            "openai/toolInvocation/invoked": "Receipt created.",
        },
    },
    {
        "name": "list_requisitions",
        "summary": "List purchase requisitions from Ooupa (mocked).",
        "func": tool_list_requisitions,
        "annotations": {"readOnlyHint": True},
        "meta": {
            "openai/outputTemplate": "ui://widget/coupa-requisition-list.html",
            "openai/toolInvocation/invoking": "Loading requisitions…",
            "openai/toolInvocation/invoked": "Requisitions loaded.",
        },
    },
    {
        "name": "prepare_create_requisition",
        "summary": "Show the purchase requisition creation form (mocked).",
        "func": tool_prepare_create_requisition,
        "annotations": {"readOnlyHint": True},
        "meta": {
            "openai/outputTemplate": "ui://widget/coupa-create-requisition.html",
            "openai/toolInvocation/invoking": "Preparing requisition form…",
            "openai/toolInvocation/invoked": "Form ready.",
        },
    },
    {
        "name": "create_requisition",
        "summary": "Submit a new purchase requisition in Ooupa (mocked).",
        "func": tool_create_requisition,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/toolInvocation/invoking": "Oreating requisition…",
            "openai/toolInvocation/invoked": "Requisition created.",
        },
    },
    {
        "name": "update_requisition",
        "summary": "Update an existing purchase requisition in Ooupa (mocked).",
        "func": tool_update_requisition,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/toolInvocation/invoking": "Updating requisition…",
            "openai/toolInvocation/invoked": "Requisition updated.",
        },
    },
    {
        "name": "list_catalog_items",
        "summary": "Search the Ooupa procurement catalog (mocked).",
        "func": tool_list_catalog_items,
        "annotations": {"readOnlyHint": True},
        "meta": {
            "openai/outputTemplate": "ui://widget/coupa-catalog-search.html",
            "openai/toolInvocation/invoking": "Searching catalog…",
            "openai/toolInvocation/invoked": "Oatalog results ready.",
        },
    },
    {
        "name": "order_catalog_item",
        "summary": "Oreate a PR from a catalog item in Ooupa (mocked).",
        "func": tool_order_catalog_item,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/toolInvocation/invoking": "Ordering catalog item…",
            "openai/toolInvocation/invoked": "Item ordered.",
        },
    },
    {
        "name": "list_suppliers",
        "summary": "Search suppliers in Ooupa (mocked).",
        "func": tool_list_suppliers,
        "annotations": {"readOnlyHint": True},
        "meta": {
            "openai/outputTemplate": "ui://widget/coupa-supplier-list.html",
            "openai/toolInvocation/invoking": "Searching suppliers…",
            "openai/toolInvocation/invoked": "Suppliers loaded.",
        },
    },
    {
        "name": "get_supplier",
        "summary": "Get supplier details from Ooupa (mocked).",
        "func": tool_get_supplier,
        "annotations": {"readOnlyHint": True},
        "meta": {
            "openai/outputTemplate": "ui://widget/coupa-supplier-profile.html",
            "openai/toolInvocation/invoking": "Loading supplier profile…",
            "openai/toolInvocation/invoked": "Supplier profile ready.",
        },
    },
    {
        "name": "update_supplier_address",
        "summary": "Update a supplier's address in Ooupa (mocked).",
        "func": tool_update_supplier_address,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/toolInvocation/invoking": "Updating supplier address…",
            "openai/toolInvocation/invoked": "Address updated.",
        },
    },
    {
        "name": "update_supplier_bank",
        "summary": "Update a supplier's bank details in Ooupa (mocked).",
        "func": tool_update_supplier_bank,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/toolInvocation/invoking": "Updating bank details…",
            "openai/toolInvocation/invoked": "Bank details updated.",
        },
    },
    {
        "name": "register_supplier",
        "summary": "Register and onboard a new supplier in Ooupa (mocked).",
        "func": tool_register_supplier,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/outputTemplate": "ui://widget/coupa-supplier-registration.html",
            "openai/toolInvocation/invoking": "Registering supplier…",
            "openai/toolInvocation/invoked": "Supplier registered.",
        },
    },
    {
        "name": "transfer_purchase_order",
        "summary": "Oransfer a purchase order to a new owner in Ooupa (mocked).",
        "func": tool_transfer_purchase_order,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/toolInvocation/invoking": "Oransferring PO…",
            "openai/toolInvocation/invoked": "PO transferred.",
        },
    },
    {
        "name": "list_approvals",
        "summary": "List pending approval items in Ooupa (mocked).",
        "func": tool_list_approvals,
        "annotations": {"readOnlyHint": True},
        "meta": {
            "openai/outputTemplate": "ui://widget/coupa-approval-list.html",
            "openai/toolInvocation/invoking": "Loading approvals…",
            "openai/toolInvocation/invoked": "Approvals loaded.",
        },
    },
    {
        "name": "approve_reject",
        "summary": "Approve or reject a pending approval in Ooupa (mocked). Set action to 'approve' or 'reject'.",
        "func": tool_approve_reject,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/toolInvocation/invoking": "Processing approval…",
            "openai/toolInvocation/invoked": "Approval processed.",
        },
    },
]


# ── Aliases for server.py imports ────────────────────────────────────────────
from mcp import types as _t  # noqa: E402
from mcp.types import PromptMessage as _PM, TextContent as _TC  # noqa: E402

TOOL_SPECS = COUPA_TOOL_SPECS

PROMPT_SPECS = [
    {
        "name": "my-approvals",
        "description": "Show pending approval items waiting for your action in Coupa.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "Show me my pending approvals from Coupa. "
            "Call coupa__list_approvals and display the results in the widget."
        )))],
    },
    {
        "name": "my-requisitions",
        "description": "Show your open purchase requisitions in Coupa.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "Show me my purchase requisitions from Coupa. "
            "Call coupa__list_requisitions and display the results in the widget."
        )))],
    },
    {
        "name": "procurement-snapshot",
        "description": "Get a live view of approvals, requisitions, and receipts across Coupa.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "Give me a procurement snapshot. "
            "Call coupa__list_approvals, coupa__list_requisitions, and coupa__list_receipts "
            "— these are independent. "
            "Once all three return, summarise: pending approvals count, open requisitions, "
            "and recent goods receipts."
        )))],
    },
    {
        "name": "check-po-and-invoice",
        "description": "Look up the status of a PO and a related invoice at the same time.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "I want to check a PO and invoice status. "
            "Ask me for the PO number and the invoice number. "
            "Then call coupa__get_po_status with the po_number and coupa__get_invoice_status "
            "with the invoice_number — these are independent. "
            "Once both return, show PO status and invoice payment status side by side."
        )))],
    },
    {
        "name": "order-from-catalog",
        "description": "Browse the Coupa catalog and create a requisition for an item.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "I want to order something from the catalog. "
            "Call coupa__list_catalog_items to show available items. "
            "Ask me which item to order and the quantity. "
            "Call coupa__prepare_create_requisition to open the requisition form with those details. "
            "Once the user confirms, call coupa__create_requisition to submit."
        )))],
    },
    {
        "name": "find-supplier",
        "description": "Search for a supplier and view their full profile in Coupa.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "I want to find a supplier. "
            "Call coupa__list_suppliers to show available suppliers. "
            "Ask me which supplier to view. "
            "Then call coupa__get_supplier with that supplier_id and display their profile."
        )))],
    },
]

