from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class DashboardSummaryResponse(BaseModel):
    patients_today: int = 0
    total_patients: int = 0
    new_patients_this_week: int = 0
    orders_today: int = 0
    orders_this_week: int = 0
    pending_orders: int = 0
    verified_orders: int = 0
    cancelled_orders: int = 0
    samples_today: int = 0
    samples_pending_collection: int = 0
    samples_processing: int = 0
    samples_urgent: int = 0
    pending_results: int = 0
    results_draft: int = 0
    results_entered: int = 0
    results_under_review: int = 0
    results_verified: int = 0
    results_correction_required: int = 0
    pending_verification: int = 0
    critical_results: int = 0
    reports_available: int = 0
    reports_today: int = 0
    reports_this_week: int = 0
    verified_today: int = 0

class WorkflowCountsResponse(BaseModel):
    orders: int = 0
    samples: int = 0
    processing: int = 0
    results_pending: int = 0
    verification: int = 0
    reports: int = 0

class WorkloadTimeSeriesItem(BaseModel):
    date: str
    count: int

class SampleStatusBreakdown(BaseModel):
    registered_count: int = 0
    registered_percent: float = 0.0
    collected_count: int = 0
    collected_percent: float = 0.0
    processing_count: int = 0
    processing_percent: float = 0.0
    completed_count: int = 0
    completed_percent: float = 0.0
    rejected_count: int = 0
    rejected_percent: float = 0.0
    recollection_required_count: int = 0
    recollection_required_percent: float = 0.0
    total_samples: int = 0

class PriorityWorkloadBreakdown(BaseModel):
    normal_count: int = 0
    urgent_count: int = 0

class ResultStatusBreakdown(BaseModel):
    draft_count: int = 0
    entered_count: int = 0
    under_review_count: int = 0
    verified_count: int = 0
    correction_required_count: int = 0

class DashboardWorkloadResponse(BaseModel):
    range_type: str
    orders: List[WorkloadTimeSeriesItem] = []
    samples: List[WorkloadTimeSeriesItem] = []
    sample_status: SampleStatusBreakdown
    priority_workload: PriorityWorkloadBreakdown
    result_status: ResultStatusBreakdown

class TATStageMetric(BaseModel):
    average_minutes: Optional[float] = None
    sample_count: int = 0

class DashboardTATResponse(BaseModel):
    sample_to_result: TATStageMetric
    result_to_verification: TATStageMetric
    verification_to_report: TATStageMetric

class CriticalResultItem(BaseModel):
    id: int
    sample_id: int
    sample_identifier: str
    patient_id: int
    patient_name: str
    test_name: str
    parameter_name: str
    result_value: str
    abnormal_flag: str
    critical_flag: bool
    status: str
    entered_at: Optional[datetime] = None

class DashboardCriticalResultsResponse(BaseModel):
    critical_results: List[CriticalResultItem] = []
    total_count: int = 0

class VerificationQueueWidgetItem(BaseModel):
    id: int
    sample_id: int
    sample_identifier: str
    patient_name: str
    order_number: str
    tests: List[str] = []
    has_critical: bool = False
    status: str
    entered_at: Optional[datetime] = None

class DashboardVerificationQueueResponse(BaseModel):
    queue: List[VerificationQueueWidgetItem] = []
    total_count: int = 0

class RecentActivityItem(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    timestamp: datetime
    user_name: Optional[str] = None
    description: Optional[str] = None

class DashboardActivityResponse(BaseModel):
    activities: List[RecentActivityItem] = []

class RecentReportItem(BaseModel):
    id: int
    report_number: str
    patient_name: str
    order_number: str
    generated_at: datetime
    status: str

class DashboardRecentReportsResponse(BaseModel):
    reports: List[RecentReportItem] = []
