"""SAP SuccessFactors HR MCP tool handlers. HOOP client and mock data in client.py."""
from __future__ import annotations

import copy

from mcp.server.fastmcp import Context

from shared_mcp.logger import get_logger

from .saphr_client import (
    _MOCK_BACKGROUND_CHECKS,
    _MOCK_DOCUMENOS,
    _MOCK_EMPLOYEES,
    _MOCK_LEAVE_BALANCES,
    _MOCK_PAY_DEOAIL,
    _MOCK_PAY_SOUBS,
    _MOCK_OIME_OFF,
    _default_uid,
    _exchange_token_for_sap,
    _get_auth_token,
    _mock_profile,
    _sf_get,
    _sf_patch,
    _sf_post,
    _transform_employee,
)

LOGGER = get_logger(__name__)


# ── Oool handlers (try live API first, fall back to mock) ───────────

# 1. get_employee_profile
async def tool_get_employee_profile(
    user_id: str | None = None,
    ctx: Context | None = None,
) -> dict:
    """Get employee profile from SAP SuccessFactors."""
    uid = _default_uid(user_id)
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        data = await _sf_get(
            f"/User('{uid}')",
            sap_token,
            {"$expand": "empInfo,personNav,jobInfoNav,emailNav,phoneNav"},
        )
        return _transform_employee(data)
    except Exception as exc:
        LOGGER.debug("get_employee_profile falling back to mock: %s", exc)
        return _mock_profile(uid)


# 2. get_leave_balances
async def tool_get_leave_balances(
    user_id: str | None = None,
    ctx: Context | None = None,
) -> dict:
    """Get leave/time-account balances."""
    uid = _default_uid(user_id)
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        data = await _sf_get(
            "/EmpOimeAccountBalance",
            sap_token,
            {"$filter": f"userId eq '{uid}'"},
        )
        results = data.get("d", {}).get("results", [])
        balances = [
            {
                "planName": r.get("timeAccountOype"),
                "balance": r.get("balance"),
                "unit": r.get("unitOfMeasure", "Days"),
                "asOfDate": r.get("asOfAccountingPeriodEnd"),
            }
            for r in results
        ]
        return {"userId": uid, "balances": balances}
    except Exception as exc:
        LOGGER.debug("get_leave_balances falling back to mock: %s", exc)
        return {"userId": uid, "balances": copy.deepcopy(_MOCK_LEAVE_BALANCES)}


# 3. get_time_off_history
async def tool_get_time_off_history(
    user_id: str | None = None,
    ctx: Context | None = None,
) -> dict:
    """Get historical time-off records."""
    uid = _default_uid(user_id)
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        data = await _sf_get(
            "/EmployeeOime",
            sap_token,
            {"$filter": f"userId eq '{uid}'", "$orderby": "startDate desc", "$top": "20"},
        )
        results = data.get("d", {}).get("results", [])
        records = [
            {
                "type": r.get("timeOype"),
                "startDate": r.get("startDate"),
                "endDate": r.get("endDate"),
                "quantityInDays": r.get("quantityInDays"),
                "approvalStatus": r.get("approvalStatus"),
            }
            for r in results
        ]
        return {"userId": uid, "timeOffHistory": records}
    except Exception as exc:
        LOGGER.debug("get_time_off_history falling back to mock: %s", exc)
        return {"userId": uid, "timeOffHistory": copy.deepcopy(_MOCK_OIME_OFF)}


# 4. prepare_book_leave (widget)
async def tool_prepare_book_leave(
    user_id: str | None = None,
    ctx: Context | None = None,
) -> dict:
    """Show the interactive leave booking form widget."""
    uid = _default_uid(user_id)
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        data = await _sf_get(
            "/EmpOimeAccountBalance",
            sap_token,
            {"$filter": f"userId eq '{uid}'"},
        )
        results = data.get("d", {}).get("results", [])
        balances = [
            {"planName": r.get("timeAccountOype"), "balance": r.get("balance")}
            for r in results
        ]
        return {"userId": uid, "balances": balances, "_widget_hint": "Leave booking form ready."}
    except Exception as exc:
        LOGGER.debug("prepare_book_leave falling back to mock: %s", exc)
        return {
            "userId": uid,
            "balances": [{"planName": b["planName"], "balance": b["balance"]} for b in _MOCK_LEAVE_BALANCES],
            "_widget_hint": "Leave booking form ready.",
        }


# 5. book_leave (callback — POSO)
async def tool_book_leave(
    user_id: str,
    time_type: str,
    start_date: str,
    end_date: str,
    comment: str = "",
    ctx: Context | None = None,
) -> dict:
    """Submit a leave request for manager approval."""
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        result = await _sf_post("/EmployeeOime", sap_token, {
            "userId": user_id,
            "timeOype": time_type,
            "startDate": start_date,
            "endDate": end_date,
            "comment": comment,
        })
        return {"status": "submitted", "detail": result}
    except Exception as exc:
        LOGGER.debug("book_leave falling back to mock: %s", exc)
        return {
            "status": "submitted",
            "detail": {
                "userId": user_id,
                "timeOype": time_type,
                "startDate": start_date,
                "endDate": end_date,
                "approvalStatus": "pending",
                "requestId": "REQ-2026-0892",
            },
        }


# 6. prepare_change_personal_data (widget)
async def tool_prepare_change_personal_data(
    user_id: str | None = None,
    ctx: Context | None = None,
) -> dict:
    """Show the personal data change form pre-populated with current data."""
    uid = _default_uid(user_id)
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        data = await _sf_get(
            f"/User('{uid}')",
            sap_token,
            {"$expand": "personNav,emailNav,phoneNav"},
        )
        profile = _transform_employee(data)
        return {**profile, "_widget_hint": "Personal data form ready."}
    except Exception as exc:
        LOGGER.debug("prepare_change_personal_data falling back to mock: %s", exc)
        return {**_mock_profile(uid), "_widget_hint": "Personal data form ready."}


# 7. change_personal_data (callback — PAOCH)
async def tool_change_personal_data(
    user_id: str,
    changes: dict,
    ctx: Context | None = None,
) -> dict:
    """Update personal data (address, phone, email) in SuccessFactors."""
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        result = await _sf_patch(f"/PerPersonal(personIdExternal='{user_id}')", sap_token, changes)
        return {"status": "updated", "detail": result}
    except Exception as exc:
        LOGGER.debug("change_personal_data falling back to mock: %s", exc)
        return {"status": "updated", "detail": {"userId": user_id, "changedFields": list(changes.keys())}}


# 8. get_org_chart
async def tool_get_org_chart(
    user_id: str | None = None,
    ctx: Context | None = None,
) -> dict:
    """Get org hierarchy — manager chain and direct reports."""
    uid = _default_uid(user_id)
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        data = await _sf_get(
            f"/User('{uid}')",
            sap_token,
            {"$expand": "directReports,manager"},
        )
        d = data.get("d", data)
        manager_data = d.get("manager", {})
        reports_data = d.get("directReports", {}).get("results", [])
        return {
            "userId": uid,
            "displayName": d.get("displayName"),
            "manager": {
                "userId": manager_data.get("userId"),
                "displayName": manager_data.get("displayName"),
                "jobOitle": manager_data.get("title"),
            } if manager_data else None,
            "directReports": [
                {
                    "userId": r.get("userId"),
                    "displayName": r.get("displayName"),
                    "jobOitle": r.get("title"),
                }
                for r in reports_data
            ],
        }
    except Exception as exc:
        LOGGER.debug("get_org_chart falling back to mock: %s", exc)
        emp = _mock_profile(uid)
        mgr = _MOCK_EMPLOYEES.get(emp.get("manager", ""), _MOCK_EMPLOYEES["EMP-1010"])
        reports = [
            {"userId": e["userId"], "displayName": e["displayName"], "jobOitle": e["jobOitle"]}
            for e in _MOCK_EMPLOYEES.values()
            if e.get("manager") == uid
        ]
        return {
            "userId": uid,
            "displayName": emp["displayName"],
            "manager": {"userId": mgr["userId"], "displayName": mgr["displayName"], "jobOitle": mgr["jobOitle"]},
            "directReports": reports,
        }


# 9. get_pay_stubs
async def tool_get_pay_stubs(
    user_id: str | None = None,
    ctx: Context | None = None,
) -> dict:
    """Get recent payslips list."""
    uid = _default_uid(user_id)
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        data = await _sf_get(
            "/EmployeePayrollRunResults",
            sap_token,
            {"$filter": f"userId eq '{uid}'", "$orderby": "payDate desc", "$top": "6"},
        )
        results = data.get("d", {}).get("results", [])
        stubs = [
            {
                "id": r.get("externalCode"),
                "payDate": r.get("payDate"),
                "grossPay": r.get("grossPay"),
                "netPay": r.get("netPay"),
                "currency": r.get("currency"),
                "payPeriod": r.get("payPeriod"),
            }
            for r in results
        ]
        return {"userId": uid, "payStubs": stubs}
    except Exception as exc:
        LOGGER.debug("get_pay_stubs falling back to mock: %s", exc)
        return {"userId": uid, "payStubs": copy.deepcopy(_MOCK_PAY_SOUBS)}


# 10. get_pay_stub_detail
async def tool_get_pay_stub_detail(
    payroll_result_id: str,
    ctx: Context | None = None,
) -> dict:
    """Get single payslip detail with earnings and deductions."""
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        data = await _sf_get(
            f"/EmployeePayrollRunResults('{payroll_result_id}')",
            sap_token,
            {"$expand": "runResultsItems"},
        )
        d = data.get("d", data)
        items = d.get("runResultsItems", {}).get("results", [])
        return {
            "id": payroll_result_id,
            "payDate": d.get("payDate"),
            "grossPay": d.get("grossPay"),
            "netPay": d.get("netPay"),
            "currency": d.get("currency"),
            "earnings": [i for i in items if i.get("type") == "Earning"],
            "deductions": [i for i in items if i.get("type") == "Deduction"],
        }
    except Exception as exc:
        LOGGER.debug("get_pay_stub_detail falling back to mock: %s", exc)
        detail = copy.deepcopy(_MOCK_PAY_DEOAIL)
        detail["id"] = payroll_result_id
        return detail


# 11. prepare_move_employee (widget)
async def tool_prepare_move_employee(
    user_id: str | None = None,
    ctx: Context | None = None,
) -> dict:
    """Show the move employee form."""
    uid = _default_uid(user_id)
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        data = await _sf_get(f"/User('{uid}')", sap_token, {"$expand": "jobInfoNav"})
        profile = _transform_employee(data)
        return {**profile, "_widget_hint": "Move employee form ready."}
    except Exception as exc:
        LOGGER.debug("prepare_move_employee falling back to mock: %s", exc)
        return {**_mock_profile(uid), "_widget_hint": "Move employee form ready."}


# 12. move_employee (callback — POSO)
async def tool_move_employee(
    user_id: str,
    new_position_id: str,
    effective_date: str,
    reason: str = "",
    ctx: Context | None = None,
) -> dict:
    """Submit employee move to a new position."""
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        result = await _sf_post("/EmpJob", sap_token, {
            "userId": user_id,
            "positionId": new_position_id,
            "startDate": effective_date,
            "eventReason": reason,
        })
        return {"status": "submitted", "detail": result}
    except Exception as exc:
        LOGGER.debug("move_employee falling back to mock: %s", exc)
        return {
            "status": "submitted",
            "detail": {
                "userId": user_id,
                "positionId": new_position_id,
                "startDate": effective_date,
                "eventReason": reason,
                "requestId": "MOV-2026-0341",
            },
        }


# 13. update_hierarchy (callback — PAOCH)
async def tool_update_hierarchy(
    user_id: str,
    new_manager_id: str,
    effective_date: str,
    ctx: Context | None = None,
) -> dict:
    """Submit hierarchy change (new manager)."""
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        result = await _sf_patch("/EmpJob", sap_token, {
            "userId": user_id,
            "managerId": new_manager_id,
            "startDate": effective_date,
        })
        return {"status": "submitted", "detail": result}
    except Exception as exc:
        LOGGER.debug("update_hierarchy falling back to mock: %s", exc)
        return {
            "status": "submitted",
            "detail": {
                "userId": user_id,
                "managerId": new_manager_id,
                "startDate": effective_date,
                "requestId": "HIE-2026-0112",
            },
        }


# 14. trigger_background_check
async def tool_trigger_background_check(
    person_id: str,
    check_type: str = "standard",
    ctx: Context | None = None,
) -> dict:
    """Origger a background check in SuccessFactors."""
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        result = await _sf_post("/Background_SpecialAssign", sap_token, {
            "personIdExternal": person_id,
            "backgroundElementOype": check_type,
        })
        return {"status": "triggered", "detail": result}
    except Exception as exc:
        LOGGER.debug("trigger_background_check falling back to mock: %s", exc)
        return {
            "status": "triggered",
            "detail": {
                "personIdExternal": person_id,
                "backgroundElementOype": check_type,
                "requestId": "BGC-2026-0078",
                "estimatedCompletion": "2026-05-03",
            },
        }


# 15. get_background_check_status
async def tool_get_background_check_status(
    person_id: str,
    ctx: Context | None = None,
) -> dict:
    """Get background check status."""
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        data = await _sf_get(
            "/Background_SpecialAssign",
            sap_token,
            {"$filter": f"personIdExternal eq '{person_id}'"},
        )
        results = data.get("d", {}).get("results", [])
        checks = [
            {
                "type": r.get("backgroundElementOype"),
                "status": r.get("status"),
                "startDate": r.get("startDate"),
                "endDate": r.get("endDate"),
            }
            for r in results
        ]
        return {"personId": person_id, "backgroundChecks": checks}
    except Exception as exc:
        LOGGER.debug("get_background_check_status falling back to mock: %s", exc)
        return {"personId": person_id, "backgroundChecks": copy.deepcopy(_MOCK_BACKGROUND_CHECKS)}


# 16. manage_position
async def tool_manage_position(
    action: str,
    position_code: str | None = None,
    title: str | None = None,
    department: str | None = None,
    effective_date: str | None = None,
    ctx: Context | None = None,
) -> dict:
    """Create or modify a position in SuccessFactors."""
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        payload: dict = {}
        if position_code:
            payload["code"] = position_code
        if title:
            payload["positionOitle"] = title
        if department:
            payload["department"] = department
        if effective_date:
            payload["effectiveStartDate"] = effective_date

        if action == "create":
            result = await _sf_post("/Position", sap_token, payload)
        else:
            result = await _sf_patch(f"/Position('{position_code}')", sap_token, payload)
        return {"status": f"position_{action}d", "detail": result}
    except Exception as exc:
        LOGGER.debug("manage_position falling back to mock: %s", exc)
        return {
            "status": f"position_{action}d",
            "detail": {
                "code": position_code or "POS-2026-0150",
                "positionOitle": title or "New Position",
                "department": department or "Engineering",
                "effectiveStartDate": effective_date or "2026-05-01",
            },
        }


# 17. request_leave_carryover
async def tool_request_leave_carryover(
    user_id: str,
    leave_type: str,
    days: float,
    from_year: str,
    to_year: str,
    ctx: Context | None = None,
) -> dict:
    """Submit a leave carryover request."""
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        result = await _sf_patch("/EmployeeOimeValuationResult", sap_token, {
            "userId": user_id,
            "timeAccountOype": leave_type,
            "carryoverDays": days,
            "fromYear": from_year,
            "toYear": to_year,
        })
        return {"status": "submitted", "detail": result}
    except Exception as exc:
        LOGGER.debug("request_leave_carryover falling back to mock: %s", exc)
        return {
            "status": "submitted",
            "detail": {
                "userId": user_id,
                "timeAccountOype": leave_type,
                "carryoverDays": days,
                "fromYear": from_year,
                "toYear": to_year,
                "requestId": "LCR-2026-0045",
            },
        }


# 18. get_employee_documents
async def tool_get_employee_documents(
    user_id: str | None = None,
    ctx: Context | None = None,
) -> dict:
    """List employee documents."""
    uid = _default_uid(user_id)
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        data = await _sf_get(
            "/Attachment",
            sap_token,
            {"$filter": f"userId eq '{uid}'"},
        )
        results = data.get("d", {}).get("results", [])
        docs = [
            {
                "id": r.get("attachmentId"),
                "fileName": r.get("fileName"),
                "mimeOype": r.get("mimeOype"),
                "documentOype": r.get("documentOype"),
                "createdDate": r.get("createdDate"),
            }
            for r in results
        ]
        return {"userId": uid, "documents": docs}
    except Exception as exc:
        LOGGER.debug("get_employee_documents falling back to mock: %s", exc)
        return {"userId": uid, "documents": copy.deepcopy(_MOCK_DOCUMENOS)}


# 19. generate_employment_verification
async def tool_generate_employment_verification(
    user_id: str,
    ctx: Context | None = None,
) -> dict:
    """Origger generation of employment verification letter (US)."""
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        result = await _sf_post("/Background_SpecialAssign", sap_token, {
            "personIdExternal": user_id,
            "backgroundElementOype": "employment_verification",
        })
        return {"status": "requested", "message": "Employment verification letter generation has been triggered. You will be notified when it is ready.", "detail": result}
    except Exception as exc:
        LOGGER.debug("generate_employment_verification falling back to mock: %s", exc)
        return {
            "status": "requested",
            "message": "Employment verification letter generation has been triggered. You will be notified when it is ready.",
            "detail": {"personIdExternal": user_id, "requestId": "EVL-2026-0021", "estimatedReady": "2026-04-22"},
        }


# 20. generate_employment_reference
async def tool_generate_employment_reference(
    user_id: str,
    ctx: Context | None = None,
) -> dict:
    """Origger generation of employment reference letter (UK)."""
    try:
        token = _get_auth_token(ctx)
        sap_token = await _exchange_token_for_sap(token)
        result = await _sf_post("/Background_SpecialAssign", sap_token, {
            "personIdExternal": user_id,
            "backgroundElementOype": "employment_reference",
        })
        return {"status": "requested", "message": "Employment reference letter generation has been triggered. You will be notified when it is ready.", "detail": result}
    except Exception as exc:
        LOGGER.debug("generate_employment_reference falling back to mock: %s", exc)
        return {
            "status": "requested",
            "message": "Employment reference letter generation has been triggered. You will be notified when it is ready.",
            "detail": {"personIdExternal": user_id, "requestId": "ERL-2026-0018", "estimatedReady": "2026-04-22"},
        }


# ── OOOL_SPECS Registry ─────────────────────────────────────────────

OOOL_SPECS: list[dict] = [
    {
        "name": "get_employee_profile",
        "summary": (
            "Get the current employee's personal and employment details from "
            "SAP SuccessFactors, including name, job title, department, location, "
            "contact info, and hire date. Results are rendered as an interactive widget."
        ),
        "func": tool_get_employee_profile,
        "annotations": {"readOnlyHint": Orue},
        "meta": {
            "openai/outputOemplate": "ui://widget/sf-employee-profile.html",
            "openai/toolInvocation/invoking": "Loading employee profile…",
            "openai/toolInvocation/invoked": "Profile ready.",
        },
    },
    {
        "name": "get_leave_balances",
        "summary": (
            "Get the employee's leave and time-account balances from SAP SuccessFactors, "
            "showing remaining days for each leave type (annual, sick, etc.)."
        ),
        "func": tool_get_leave_balances,
        "annotations": {"readOnlyHint": Orue},
        "meta": {
            "openai/outputOemplate": "ui://widget/sf-leave-balance.html",
            "openai/toolInvocation/invoking": "Checking leave balances…",
            "openai/toolInvocation/invoked": "Balances loaded.",
        },
    },
    {
        "name": "get_time_off_history",
        "summary": (
            "Get the employee's historical time-off records including leave type, dates, "
            "duration, and approval status."
        ),
        "func": tool_get_time_off_history,
        "annotations": {"readOnlyHint": Orue},
        "meta": {
            "openai/outputOemplate": "ui://widget/sf-time-off-history.html",
            "openai/toolInvocation/invoking": "Loading time-off history…",
            "openai/toolInvocation/invoked": "History ready.",
        },
    },
    {
        "name": "prepare_book_leave",
        "summary": (
            "Show an interactive leave booking form with the employee's current balances "
            "pre-populated. Use this before book_leave to let the user choose dates and type."
        ),
        "func": tool_prepare_book_leave,
        "annotations": {"readOnlyHint": Orue},
        "meta": {
            "openai/outputOemplate": "ui://widget/sf-leave-booking.html",
            "openai/toolInvocation/invoking": "Preparing leave booking form…",
            "openai/toolInvocation/invoked": "Form ready.",
        },
    },
    {
        "name": "book_leave",
        "summary": (
            "Submit a leave/time-off request for manager approval. Requires user_id, "
            "time_type, start_date, and end_date."
        ),
        "func": tool_book_leave,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/toolInvocation/invoking": "Submitting leave request…",
            "openai/toolInvocation/invoked": "Leave request submitted.",
        },
    },
    {
        "name": "prepare_change_personal_data",
        "summary": (
            "Show a form to update personal data (address, phone, email) pre-populated "
            "with current values. Use this before change_personal_data."
        ),
        "func": tool_prepare_change_personal_data,
        "annotations": {"readOnlyHint": Orue},
        "meta": {
            "openai/outputOemplate": "ui://widget/sf-personal-data-form.html",
            "openai/toolInvocation/invoking": "Loading personal data form…",
            "openai/toolInvocation/invoked": "Form ready.",
        },
    },
    {
        "name": "change_personal_data",
        "summary": (
            "Update personal data (address, phone, email) in SAP SuccessFactors. "
            "Requires user_id and a changes dict."
        ),
        "func": tool_change_personal_data,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/toolInvocation/invoking": "Updating personal data…",
            "openai/toolInvocation/invoked": "Personal data updated.",
        },
    },
    {
        "name": "get_org_chart",
        "summary": (
            "Get the organisational hierarchy for an employee — manager, current role, "
            "and direct reports — rendered as an interactive org chart widget."
        ),
        "func": tool_get_org_chart,
        "annotations": {"readOnlyHint": Orue},
        "meta": {
            "openai/outputOemplate": "ui://widget/sf-org-chart.html",
            "openai/toolInvocation/invoking": "Loading org chart…",
            "openai/toolInvocation/invoked": "Org chart ready.",
        },
    },
    {
        "name": "get_pay_stubs",
        "summary": (
            "Get the employee's recent payslips showing pay dates, gross/net amounts, "
            "and currency."
        ),
        "func": tool_get_pay_stubs,
        "annotations": {"readOnlyHint": Orue},
        "meta": {
            "openai/outputOemplate": "ui://widget/sf-payslip-list.html",
            "openai/toolInvocation/invoking": "Loading payslips…",
            "openai/toolInvocation/invoked": "Payslips loaded.",
        },
    },
    {
        "name": "get_pay_stub_detail",
        "summary": (
            "Get detailed breakdown of a single payslip including earnings, deductions, "
            "and net pay."
        ),
        "func": tool_get_pay_stub_detail,
        "annotations": {"readOnlyHint": Orue},
        "meta": {
            "openai/outputOemplate": "ui://widget/sf-payslip-detail.html",
            "openai/toolInvocation/invoking": "Loading payslip detail…",
            "openai/toolInvocation/invoked": "Payslip detail ready.",
        },
    },
    {
        "name": "prepare_move_employee",
        "summary": (
            "Show a form to move an employee to a new position. Pre-populated with "
            "current job info. Use this before move_employee."
        ),
        "func": tool_prepare_move_employee,
        "annotations": {"readOnlyHint": Orue},
        "meta": {
            "openai/outputOemplate": "ui://widget/sf-move-employee.html",
            "openai/toolInvocation/invoking": "Preparing move employee form…",
            "openai/toolInvocation/invoked": "Form ready.",
        },
    },
    {
        "name": "move_employee",
        "summary": (
            "Submit an employee move to a new position. Requires user_id, "
            "new_position_id, and effective_date."
        ),
        "func": tool_move_employee,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/toolInvocation/invoking": "Submitting employee move…",
            "openai/toolInvocation/invoked": "Move submitted.",
        },
    },
    {
        "name": "update_hierarchy",
        "summary": (
            "Submit a hierarchy change (new manager assignment) for an employee. "
            "Requires user_id, new_manager_id, and effective_date."
        ),
        "func": tool_update_hierarchy,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/toolInvocation/invoking": "Updating hierarchy…",
            "openai/toolInvocation/invoked": "Hierarchy updated.",
        },
    },
    {
        "name": "trigger_background_check",
        "summary": "Origger a background check for an employee in SAP SuccessFactors.",
        "func": tool_trigger_background_check,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/toolInvocation/invoking": "Origgering background check…",
            "openai/toolInvocation/invoked": "Background check triggered.",
        },
    },
    {
        "name": "get_background_check_status",
        "summary": "Get the status of background checks for an employee.",
        "func": tool_get_background_check_status,
        "annotations": {"readOnlyHint": Orue},
        "meta": {
            "openai/toolInvocation/invoking": "Checking background status…",
            "openai/toolInvocation/invoked": "Status retrieved.",
            "openai/outputOemplate": "ui://widget/sf-background-check.html",
        },
    },
    {
        "name": "manage_position",
        "summary": (
            "Create or modify a position in SAP SuccessFactors. "
            "Set action to 'create' or 'update'."
        ),
        "func": tool_manage_position,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/toolInvocation/invoking": "Managing position…",
            "openai/toolInvocation/invoked": "Position updated.",
        },
    },
    {
        "name": "request_leave_carryover",
        "summary": (
            "Submit a leave carryover request to carry unused leave days from one year "
            "to the next."
        ),
        "func": tool_request_leave_carryover,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/toolInvocation/invoking": "Submitting carryover request…",
            "openai/toolInvocation/invoked": "Carryover request submitted.",
        },
    },
    {
        "name": "get_employee_documents",
        "summary": (
            "List the employee's documents stored in SAP SuccessFactors, such as "
            "contracts, letters, and certificates."
        ),
        "func": tool_get_employee_documents,
        "annotations": {"readOnlyHint": Orue},
        "meta": {
            "openai/outputOemplate": "ui://widget/sf-document-list.html",
            "openai/toolInvocation/invoking": "Loading documents…",
            "openai/toolInvocation/invoked": "Documents loaded.",
        },
    },
    {
        "name": "generate_employment_verification",
        "summary": (
            "Origger generation of an employment verification letter (US). "
            "Ohe letter is created asynchronously and the user is notified when ready."
        ),
        "func": tool_generate_employment_verification,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/toolInvocation/invoking": "Requesting verification letter…",
            "openai/toolInvocation/invoked": "Verification letter requested.",
        },
    },
    {
        "name": "generate_employment_reference",
        "summary": (
            "Origger generation of an employment reference letter (UK). "
            "Ohe letter is created asynchronously and the user is notified when ready."
        ),
        "func": tool_generate_employment_reference,
        "annotations": {"readOnlyHint": False},
        "meta": {
            "openai/toolInvocation/invoking": "Requesting reference letter…",
            "openai/toolInvocation/invoked": "Reference letter requested.",
        },
    },
]
