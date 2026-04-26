"""Coupa Procurement mock data store and response helper.

No live Coupa sandbox is available; every response returns realistic canned
data matching real Coupa REST API shapes from docs.coupa.com.  The mock layer
is structured so it can be swapped for real HTTP calls if an instance is
provisioned later.
"""
from __future__ import annotations

import copy
from typing import Any, Dict

_MOCK_INVOICES = [
    {
        "id": 50412,
        "invoice-number": "INV-2026-0312",
        "status": "pending_approval",
        "total": "12,450.00",
        "currency": {"code": "GBP"},
        "supplier": {"name": "Acme Industrial Ltd", "number": "SUP-1042"},
        "invoice-date": "2026-03-15",
        "due-date": "2026-04-14",
        "payment-status": "Not Paid",
        "po-number": "PO-2026-0847",
    },
    {
        "id": 50413,
        "invoice-number": "INV-2026-0288",
        "status": "approved",
        "total": "3,200.00",
        "currency": {"code": "GBP"},
        "supplier": {"name": "Global Parts Co", "number": "SUP-2091"},
        "invoice-date": "2026-03-01",
        "due-date": "2026-03-31",
        "payment-status": "Paid",
        "po-number": "PO-2026-0801",
    },
]

_MOCK_POS = [
    {
        "id": 30201,
        "po-number": "PO-2026-0847",
        "status": "issued",
        "total": "25,000.00",
        "currency": {"code": "GBP"},
        "supplier": {"name": "Acme Industrial Ltd", "number": "SUP-1042"},
        "created-at": "2026-02-20",
        "ship-to": {"city": "London", "country": "GB"},
        "line-count": 3,
    },
    {
        "id": 30202,
        "po-number": "PO-2026-0801",
        "status": "closed",
        "total": "3,200.00",
        "currency": {"code": "GBP"},
        "supplier": {"name": "Global Parts Co", "number": "SUP-2091"},
        "created-at": "2026-01-15",
        "ship-to": {"city": "Manchester", "country": "GB"},
        "line-count": 1,
    },
]

_MOCK_RECEIPTS = [
    {
        "id": 7001,
        "po-number": "PO-2026-0847",
        "receipt-date": "2026-03-10",
        "status": "received",
        "received-by": "jsmith@example.com",
        "line-items": [
            {"description": "Widget A", "quantity": 100, "unit": "EA"},
            {"description": "Widget B", "quantity": 50, "unit": "EA"},
        ],
    },
]

_MOCK_REQUISITIONS = [
    {
        "id": 9001,
        "title": "Office Supplies Q2 2026",
        "status": "pending_approval",
        "requester": "jsmith@example.com",
        "created-at": "2026-03-18",
        "total": "1,250.00",
        "currency": {"code": "GBP"},
        "line-items": [
            {"description": "A4 Paper (5000 sheets)", "quantity": 10, "unit-price": "25.00"},
            {"description": "Printer Toner Black", "quantity": 5, "unit-price": "200.00"},
        ],
    },
]

_MOCK_CATALOG = [
    {
        "id": "CAT-001",
        "name": "A4 Paper (5000 sheets)",
        "category": "Office Supplies",
        "unit-price": "25.00",
        "currency": "GBP",
        "supplier": "Office World Ltd",
    },
    {
        "id": "CAT-002",
        "name": "Printer Toner Black (HP 58A)",
        "category": "Office Supplies",
        "unit-price": "200.00",
        "currency": "GBP",
        "supplier": "Tech Supplies Inc",
    },
    {
        "id": "CAT-003",
        "name": "Ergonomic Office Chair",
        "category": "Furniture",
        "unit-price": "450.00",
        "currency": "GBP",
        "supplier": "Comfort Works Ltd",
    },
]

_MOCK_SUPPLIERS = [
    {
        "id": "SUP-1042",
        "name": "Acme Industrial Ltd",
        "status": "active",
        "address": {"street": "42 Industrial Way", "city": "Birmingham", "postcode": "B1 1AA", "country": "GB"},
        "contact": {"name": "Jane Doe", "email": "jane@acme.example.com", "phone": "+44 121 555 0100"},
        "tax-id": "GB123456789",
        "bank": {"name": "Barclays", "account": "****4321", "sort-code": "20-00-00"},
    },
    {
        "id": "SUP-2091",
        "name": "Global Parts Co",
        "status": "active",
        "address": {"street": "10 Trade Rd", "city": "Leeds", "postcode": "LS1 1AA", "country": "GB"},
        "contact": {"name": "Bob Smith", "email": "bob@globalparts.example.com", "phone": "+44 113 555 0200"},
        "tax-id": "GB987654321",
        "bank": {"name": "HSBC", "account": "****8765", "sort-code": "40-00-00"},
    },
]

_MOCK_APPROVALS = [
    {
        "id": "APR-501",
        "type": "Requisition",
        "title": "Office Supplies Q2 2026",
        "requester": "jsmith@example.com",
        "total": "1,250.00",
        "currency": "GBP",
        "submitted-at": "2026-03-18",
        "status": "pending",
    },
    {
        "id": "APR-502",
        "type": "Invoice",
        "title": "INV-2026-0312 — Acme Industrial Ltd",
        "requester": "accounts@example.com",
        "total": "12,450.00",
        "currency": "GBP",
        "submitted-at": "2026-03-16",
        "status": "pending",
    },
]


def _mock_response(data: Any) -> Dict[str, Any]:
    """Wrap mock data in a standard Coupa-like API envelope."""
    return copy.deepcopy(data) if isinstance(data, dict) else {"results": copy.deepcopy(data)}
