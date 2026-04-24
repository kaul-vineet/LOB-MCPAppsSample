"""Pydantic models for Workday tool IO."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class WorkerSummary(BaseModel):
    workday_id: str = Field(..., alias="workdayId")
    worker_id: Optional[str] = Field(None, alias="workerId")
    name: Optional[str] = None
    email: Optional[str] = None
    worker_type: Optional[str] = Field(None, alias="workerType")
    business_title: Optional[str] = Field(None, alias="businessTitle")
    location: Optional[str] = None
    location_id: Optional[str] = Field(None, alias="locationId")
    country: Optional[str] = None
    country_code: Optional[str] = Field(None, alias="countryCode")
    supervisory_organization: Optional[str] = Field(None, alias="supervisoryOrganization")
    job_type: Optional[str] = Field(None, alias="jobType")
    job_profile: Optional[str] = Field(None, alias="jobProfile")
    primary_job_id: Optional[str] = Field(None, alias="primaryJobId")
    primary_job_descriptor: Optional[str] = Field(None, alias="primaryJobDescriptor")


class LeaveBalance(BaseModel):
    plan_name: str
    plan_id: str
    balance: str
    unit: str
    effective_date: Optional[str] = None
    time_off_types: Optional[str] = None


class AbsenceType(BaseModel):
    name: str
    id: str
    unit: str
    category: Optional[str] = None
    group: Optional[str] = None


class TimeOffEntry(BaseModel):
    date: str
    time_off_type: str
    quantity: str | int | float
    unit: str
    status: str
    comment: Optional[str] = None


class LeaveOfAbsence(BaseModel):
    id: str
    leave_type: str
    status: str
    first_day_of_leave: Optional[str] = None
    last_day_of_work: Optional[str] = None
    estimated_last_day: Optional[str] = None
    comment: Optional[str] = None


class TimeOffRequestDay(BaseModel):
    date: str
    start: str
    end: str
    daily_quantity: str
    comment: Optional[str] = None
    time_off_type_id: str = Field(..., alias="timeOffTypeId")


class BookingResult(BaseModel):
    success: bool
    message: str
    days_booked: int
    total_quantity: float
    business_process: Optional[str] = None
    status: Optional[str] = None
    transaction_status: Optional[str] = None


class InboxTask(BaseModel):
    assigned: Optional[str] = None
    due: Optional[str] = None
    initiator: Optional[str] = None
    status: Optional[str] = None
    step_type: Optional[str] = None
    subject: Optional[str] = None
    overall_process: Optional[str] = None
    descriptor: Optional[str] = None


class LearningAssignment(BaseModel):
    assignment_status: Optional[str] = None
    due_date: Optional[str] = None
    learning_content: Optional[str] = None
    overdue: bool = False
    required: bool = False
    workday_id: Optional[str] = None


class PaySlip(BaseModel):
    gross: Optional[str] = None
    status: Optional[str] = None
    net: Optional[str] = None
    date: Optional[str] = None
    descriptor: Optional[str] = None


class RequestLeaveParameters(BaseModel):
    start_date: str = Field(..., alias="startDate")
    end_date: str = Field(..., alias="endDate")
    quantity: str
    unit: str
    reason: str
    time_off_type_id: str = Field(..., alias="timeOffTypeId")
