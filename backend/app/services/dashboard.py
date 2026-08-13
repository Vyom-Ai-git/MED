import datetime
from datetime import timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, distinct, case, cast, Date, and_, or_, desc

from app.models.patient import Patient
from app.models.test import Test, TestParameter
from app.models.order import Order, OrderItem
from app.models.sample import Sample, Result
from app.models.result_verification import ResultVerification
from app.models.report import Report
from app.models.audit import AuditLog
from app.models.user import User

from app.schemas.dashboard import (
    DashboardSummaryResponse,
    WorkflowCountsResponse,
    DashboardWorkloadResponse,
    WorkloadTimeSeriesItem,
    SampleStatusBreakdown,
    PriorityWorkloadBreakdown,
    ResultStatusBreakdown,
    DashboardTATResponse,
    TATStageMetric,
    DashboardCriticalResultsResponse,
    CriticalResultItem,
    DashboardVerificationQueueResponse,
    VerificationQueueWidgetItem,
    DashboardActivityResponse,
    RecentActivityItem,
    DashboardRecentReportsResponse,
    RecentReportItem,
)


class DashboardService:
    @staticmethod
    def _get_date_range(range_type: str, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None):
        now = datetime.datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if range_type == "today":
            start_date = today_start
            end_date = now
        elif range_type == "7days":
            start_date = today_start - timedelta(days=6)
            end_date = now
        elif range_type == "30days":
            start_date = today_start - timedelta(days=29)
            end_date = now
        elif range_type == "custom" and start_date_str and end_date_str:
            try:
                start_date = datetime.datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
                end_date = datetime.datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                # Cap custom range to max 90 days for performance/security
                if (end_date - start_date).days > 90:
                    start_date = end_date - timedelta(days=90)
            except Exception:
                start_date = today_start - timedelta(days=6)
                end_date = now
        else:
            start_date = today_start - timedelta(days=6)
            end_date = now

        return start_date, end_date

    def get_summary_metrics(
        self, db: Session, org_id: int, branch_id: Optional[int] = None
    ) -> DashboardSummaryResponse:
        now = datetime.datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=6)

        # Patient metrics
        pat_q = db.query(Patient).filter(Patient.organization_id == org_id)
        total_patients = pat_q.count()
        patients_today = pat_q.filter(Patient.created_at >= today_start).count()
        new_patients_this_week = pat_q.filter(Patient.created_at >= week_start).count()

        # Order metrics
        ord_q = db.query(Order).filter(Order.organization_id == org_id)
        if branch_id:
            ord_q = ord_q.filter(Order.branch_id == branch_id)

        orders_today = ord_q.filter(Order.created_at >= today_start).count()
        orders_this_week = ord_q.filter(Order.created_at >= week_start).count()
        pending_orders = ord_q.filter(Order.status.in_(["Pending", "Sample Collected"])).count()
        verified_orders = ord_q.filter(Order.status.in_(["Verified", "Published"])).count()
        cancelled_orders = ord_q.filter(Order.status == "Cancelled").count()

        # Sample metrics
        smp_q = db.query(Sample).filter(Sample.organization_id == org_id)
        if branch_id:
            smp_q = smp_q.filter(Sample.branch_id == branch_id)

        samples_today = smp_q.filter(Sample.created_at >= today_start).count()
        samples_pending_collection = smp_q.filter(Sample.collection_status == "Registered").count()
        samples_processing = smp_q.filter(Sample.collection_status == "Processing").count()
        samples_urgent = smp_q.filter(
            Sample.priority == "Urgent",
            Sample.collection_status.notin_(["Completed", "Rejected", "Cancelled"]),
        ).count()

        # Result metrics
        res_q = db.query(Result).filter(Result.organization_id == org_id)
        pending_results = res_q.filter(Result.status.in_(["Draft", "Entered"])).count()
        results_draft = res_q.filter(Result.status == "Draft").count()
        results_entered = res_q.filter(Result.status == "Entered").count()
        results_under_review = res_q.filter(Result.status == "Under Review").count()
        results_verified = res_q.filter(Result.status == "Verified").count()
        results_correction_required = res_q.filter(Result.status == "Correction Required").count()

        # Verification metrics (count unique samples requiring verification)
        pending_verif_q = (
            db.query(func.count(distinct(Result.sample_id)))
            .filter(Result.organization_id == org_id)
            .filter(Result.status.in_(["Entered", "Under Review"]))
        )
        pending_verification = pending_verif_q.scalar() or 0

        verified_today_q = (
            db.query(func.count(distinct(Result.sample_id)))
            .filter(Result.organization_id == org_id)
            .filter(Result.status == "Verified")
            .filter(Result.verified_at >= today_start)
        )
        verified_today = verified_today_q.scalar() or 0

        # Critical results metrics (unverified active criticals)
        critical_results_q = (
            res_q.filter(Result.critical_flag == True)
            .filter(Result.status != "Verified")
        )
        critical_results = critical_results_q.count()

        # Report metrics
        rpt_q = db.query(Report).filter(Report.organization_id == org_id)
        if branch_id:
            rpt_q = rpt_q.filter(Report.branch_id == branch_id)

        reports_available = rpt_q.filter(Report.status == "Available").count()
        reports_today = rpt_q.filter(Report.generated_at >= today_start).count()
        reports_this_week = rpt_q.filter(Report.generated_at >= week_start).count()

        return DashboardSummaryResponse(
            patients_today=patients_today,
            total_patients=total_patients,
            new_patients_this_week=new_patients_this_week,
            orders_today=orders_today,
            orders_this_week=orders_this_week,
            pending_orders=pending_orders,
            verified_orders=verified_orders,
            cancelled_orders=cancelled_orders,
            samples_today=samples_today,
            samples_pending_collection=samples_pending_collection,
            samples_processing=samples_processing,
            samples_urgent=samples_urgent,
            pending_results=pending_results,
            results_draft=results_draft,
            results_entered=results_entered,
            results_under_review=results_under_review,
            results_verified=results_verified,
            results_correction_required=results_correction_required,
            pending_verification=pending_verification,
            critical_results=critical_results,
            reports_available=reports_available,
            reports_today=reports_today,
            reports_this_week=reports_this_week,
            verified_today=verified_today,
        )

    def get_workflow_counts(
        self, db: Session, org_id: int, branch_id: Optional[int] = None
    ) -> WorkflowCountsResponse:
        ord_q = db.query(Order).filter(Order.organization_id == org_id)
        if branch_id:
            ord_q = ord_q.filter(Order.branch_id == branch_id)
        orders_count = ord_q.count()

        smp_q = db.query(Sample).filter(Sample.organization_id == org_id)
        if branch_id:
            smp_q = smp_q.filter(Sample.branch_id == branch_id)
        samples_count = smp_q.count()
        processing_count = smp_q.filter(Sample.collection_status == "Processing").count()

        res_q = db.query(Result).filter(Result.organization_id == org_id)
        results_pending_count = res_q.filter(Result.status.in_(["Draft", "Entered"])).count()

        verification_count = (
            db.query(func.count(distinct(Result.sample_id)))
            .filter(Result.organization_id == org_id)
            .filter(Result.status.in_(["Entered", "Under Review"]))
            .scalar()
            or 0
        )

        rpt_q = db.query(Report).filter(Report.organization_id == org_id)
        if branch_id:
            rpt_q = rpt_q.filter(Report.branch_id == branch_id)
        reports_count = rpt_q.filter(Report.status == "Available").count()

        return WorkflowCountsResponse(
            orders=orders_count,
            samples=samples_count,
            processing=processing_count,
            results_pending=results_pending_count,
            verification=verification_count,
            reports=reports_count,
        )

    def get_workload_analytics(
        self,
        db: Session,
        org_id: int,
        range_type: str = "7days",
        start_date_str: Optional[str] = None,
        end_date_str: Optional[str] = None,
        branch_id: Optional[int] = None,
    ) -> DashboardWorkloadResponse:
        start_date, end_date = self._get_date_range(range_type, start_date_str, end_date_str)

        # Orders aggregation by date
        ord_q = db.query(
            cast(Order.created_at, Date).label("day"),
            func.count(Order.id).label("cnt")
        ).filter(
            Order.organization_id == org_id,
            Order.created_at >= start_date,
            Order.created_at <= end_date,
        )
        if branch_id:
            ord_q = ord_q.filter(Order.branch_id == branch_id)
        ord_counts = {str(r.day): r.cnt for r in ord_q.group_by(cast(Order.created_at, Date)).all()}

        # Samples aggregation by date
        smp_q = db.query(
            cast(Sample.created_at, Date).label("day"),
            func.count(Sample.id).label("cnt")
        ).filter(
            Sample.organization_id == org_id,
            Sample.created_at >= start_date,
            Sample.created_at <= end_date,
        )
        if branch_id:
            smp_q = smp_q.filter(Sample.branch_id == branch_id)
        smp_counts = {str(r.day): r.cnt for r in smp_q.group_by(cast(Sample.created_at, Date)).all()}

        # Build contiguous date list
        curr = start_date.date()
        end_curr = end_date.date()
        date_orders: List[WorkloadTimeSeriesItem] = []
        date_samples: List[WorkloadTimeSeriesItem] = []

        while curr <= end_curr:
            day_str = curr.isoformat()
            date_orders.append(WorkloadTimeSeriesItem(date=day_str, count=ord_counts.get(day_str, 0)))
            date_samples.append(WorkloadTimeSeriesItem(date=day_str, count=smp_counts.get(day_str, 0)))
            curr += timedelta(days=1)

        # Sample Status breakdown (all samples or filtered by range)
        status_smp_q = db.query(Sample).filter(Sample.organization_id == org_id)
        if branch_id:
            status_smp_q = status_smp_q.filter(Sample.branch_id == branch_id)

        total_samples = status_smp_q.count()
        reg_cnt = status_smp_q.filter(Sample.collection_status == "Registered").count()
        col_cnt = status_smp_q.filter(Sample.collection_status == "Collected").count()
        proc_cnt = status_smp_q.filter(Sample.collection_status == "Processing").count()
        comp_cnt = status_smp_q.filter(Sample.collection_status == "Completed").count()
        rej_cnt = status_smp_q.filter(Sample.collection_status == "Rejected").count()
        recol_cnt = status_smp_q.filter(Sample.recollection_required == True).count()

        def pct(val: int, total: int) -> float:
            return round((val / total) * 100.0, 1) if total > 0 else 0.0

        sample_status = SampleStatusBreakdown(
            registered_count=reg_cnt,
            registered_percent=pct(reg_cnt, total_samples),
            collected_count=col_cnt,
            collected_percent=pct(col_cnt, total_samples),
            processing_count=proc_cnt,
            processing_percent=pct(proc_cnt, total_samples),
            completed_count=comp_cnt,
            completed_percent=pct(comp_cnt, total_samples),
            rejected_count=rej_cnt,
            rejected_percent=pct(rej_cnt, total_samples),
            recollection_required_count=recol_cnt,
            recollection_required_percent=pct(recol_cnt, total_samples),
            total_samples=total_samples,
        )

        # Priority breakdown
        norm_cnt = status_smp_q.filter(Sample.priority == "Normal").count()
        urg_cnt = status_smp_q.filter(Sample.priority == "Urgent").count()
        priority_workload = PriorityWorkloadBreakdown(normal_count=norm_cnt, urgent_count=urg_cnt)

        # Result status breakdown
        res_q = db.query(Result).filter(Result.organization_id == org_id)
        result_status = ResultStatusBreakdown(
            draft_count=res_q.filter(Result.status == "Draft").count(),
            entered_count=res_q.filter(Result.status == "Entered").count(),
            under_review_count=res_q.filter(Result.status == "Under Review").count(),
            verified_count=res_q.filter(Result.status == "Verified").count(),
            correction_required_count=res_q.filter(Result.status == "Correction Required").count(),
        )

        return DashboardWorkloadResponse(
            range_type=range_type,
            orders=date_orders,
            samples=date_samples,
            sample_status=sample_status,
            priority_workload=priority_workload,
            result_status=result_status,
        )

    def get_tat_metrics(
        self,
        db: Session,
        org_id: int,
        range_type: str = "30days",
        start_date_str: Optional[str] = None,
        end_date_str: Optional[str] = None,
        branch_id: Optional[int] = None,
    ) -> DashboardTATResponse:
        start_date, end_date = self._get_date_range(range_type, start_date_str, end_date_str)

        # 1. Sample Collection -> Result Entry
        # Fetch non-null pairs from Sample & Result
        smp_res_q = (
            db.query(Sample.collected_at, Result.entered_at)
            .join(Result, Result.sample_id == Sample.id)
            .filter(
                Sample.organization_id == org_id,
                Sample.collected_at.isnot(None),
                Result.entered_at.isnot(None),
                Sample.created_at >= start_date,
            )
        )
        if branch_id:
            smp_res_q = smp_res_q.filter(Sample.branch_id == branch_id)

        s1_diffs = []
        for col_at, ent_at in smp_res_q.all():
            if col_at and ent_at and ent_at > col_at:
                diff_mins = (ent_at - col_at).total_seconds() / 60.0
                if diff_mins > 0:
                    s1_diffs.append(diff_mins)

        s1_metric = (
            TATStageMetric(average_minutes=round(sum(s1_diffs) / len(s1_diffs), 1), sample_count=len(s1_diffs))
            if s1_diffs else TATStageMetric(average_minutes=None, sample_count=0)
        )

        # 2. Result Entry -> Verification
        res_ver_q = (
            db.query(Result.entered_at, Result.verified_at)
            .filter(
                Result.organization_id == org_id,
                Result.entered_at.isnot(None),
                Result.verified_at.isnot(None),
                Result.updated_at >= start_date,
            )
        )
        s2_diffs = []
        for ent_at, ver_at in res_ver_q.all():
            if ent_at and ver_at and ver_at > ent_at:
                diff_mins = (ver_at - ent_at).total_seconds() / 60.0
                if diff_mins > 0:
                    s2_diffs.append(diff_mins)

        s2_metric = (
            TATStageMetric(average_minutes=round(sum(s2_diffs) / len(s2_diffs), 1), sample_count=len(s2_diffs))
            if s2_diffs else TATStageMetric(average_minutes=None, sample_count=0)
        )

        # 3. Verification -> Report Generation
        # Join Report and Order/Result
        ver_rpt_q = (
            db.query(Result.verified_at, Report.generated_at)
            .join(Report, Report.order_id == Result.sample_id) # Result joins sample/order
            .filter(
                Report.organization_id == org_id,
                Result.verified_at.isnot(None),
                Report.generated_at.isnot(None),
                Report.generated_at >= start_date,
            )
        )
        if branch_id:
            ver_rpt_q = ver_rpt_q.filter(Report.branch_id == branch_id)

        s3_diffs = []
        for ver_at, gen_at in ver_rpt_q.all():
            if ver_at and gen_at and gen_at > ver_at:
                diff_mins = (gen_at - ver_at).total_seconds() / 60.0
                if diff_mins > 0:
                    s3_diffs.append(diff_mins)

        s3_metric = (
            TATStageMetric(average_minutes=round(sum(s3_diffs) / len(s3_diffs), 1), sample_count=len(s3_diffs))
            if s3_diffs else TATStageMetric(average_minutes=None, sample_count=0)
        )

        return DashboardTATResponse(
            sample_to_result=s1_metric,
            result_to_verification=s2_metric,
            verification_to_report=s3_metric,
        )

    def get_critical_results(
        self, db: Session, org_id: int, branch_id: Optional[int] = None, limit: int = 10
    ) -> DashboardCriticalResultsResponse:
        results_q = (
            db.query(Result)
            .options(
                joinedload(Result.sample).joinedload(Sample.order).joinedload(Order.patient),
                joinedload(Result.test),
                joinedload(Result.parameter),
            )
            .filter(
                Result.organization_id == org_id,
                Result.critical_flag == True,
            )
            .order_by(desc(Result.updated_at))
        )

        total_count = results_q.count()
        items = results_q.limit(limit).all()

        critical_items: List[CriticalResultItem] = []
        for r in items:
            patient_name = "Unknown Patient"
            sample_identifier = "Unknown Sample"
            patient_id = 0

            if r.sample:
                sample_identifier = r.sample.sample_identifier
                if r.sample.order and r.sample.order.patient:
                    pat = r.sample.order.patient
                    patient_name = f"{pat.first_name} {pat.last_name}"
                    patient_id = pat.id

            test_name = r.test.name if r.test else "Unknown Test"
            param_name = r.parameter.name if r.parameter else "Unknown Parameter"

            raw_val = r.raw_value or (str(r.numeric_value) if r.numeric_value is not None else r.text_value or "")
            if r.unit:
                raw_val = f"{raw_val} {r.unit}"

            critical_items.append(
                CriticalResultItem(
                    id=r.id,
                    sample_id=r.sample_id,
                    sample_identifier=sample_identifier,
                    patient_id=patient_id,
                    patient_name=patient_name,
                    test_name=test_name,
                    parameter_name=param_name,
                    result_value=raw_val,
                    abnormal_flag=r.abnormal_flag or "NORMAL",
                    critical_flag=r.critical_flag,
                    status=r.status,
                    entered_at=r.entered_at,
                )
            )

        return DashboardCriticalResultsResponse(critical_results=critical_items, total_count=total_count)

    def get_verification_queue_widget(
        self, db: Session, org_id: int, branch_id: Optional[int] = None, limit: int = 5
    ) -> DashboardVerificationQueueResponse:
        samples_q = (
            db.query(Sample)
            .options(
                joinedload(Sample.order).joinedload(Order.patient),
                joinedload(Sample.results).joinedload(Result.test),
            )
            .join(Result, Result.sample_id == Sample.id)
            .filter(
                Sample.organization_id == org_id,
                Result.status.in_(["Entered", "Under Review"]),
            )
            .group_by(Sample.id)
            .order_by(desc(Sample.updated_at))
        )

        if branch_id:
            samples_q = samples_q.filter(Sample.branch_id == branch_id)

        total_count = samples_q.count()
        samples = samples_q.limit(limit).all()

        widget_items: List[VerificationQueueWidgetItem] = []
        for smp in samples:
            patient_name = "Unknown Patient"
            order_number = "Unknown Order"
            if smp.order:
                order_number = smp.order.order_number
                if smp.order.patient:
                    patient_name = f"{smp.order.patient.first_name} {smp.order.patient.last_name}"

            test_names = list({r.test.name for r in smp.results if r.test})
            has_crit = any(r.critical_flag for r in smp.results)
            first_entered = min([r.entered_at for r in smp.results if r.entered_at], default=None)

            widget_items.append(
                VerificationQueueWidgetItem(
                    id=smp.id,
                    sample_id=smp.id,
                    sample_identifier=smp.sample_identifier,
                    patient_name=patient_name,
                    order_number=order_number,
                    tests=test_names,
                    has_critical=has_crit,
                    status=smp.collection_status,
                    entered_at=first_entered,
                )
            )

        return DashboardVerificationQueueResponse(queue=widget_items, total_count=total_count)

    def get_recent_activity(
        self, db: Session, org_id: int, branch_id: Optional[int] = None, limit: int = 10
    ) -> DashboardActivityResponse:
        audits_q = (
            db.query(AuditLog)
            .options(joinedload(AuditLog.user))
            .filter(AuditLog.organization_id == org_id)
            .order_by(desc(AuditLog.created_at))
        )

        if branch_id:
            audits_q = audits_q.filter(AuditLog.branch_id == branch_id)

        audits = audits_q.limit(limit).all()

        activity_items: List[RecentActivityItem] = []
        for a in audits:
            u_name = None
            if a.user:
                u_name = a.user.name or a.user.email

            # Provide safe description without raw sensitive clinical payload
            safe_desc = a.description or f"{a.action} on {a.entity_type}"
            if "raw_value" in safe_desc.lower() or "result" in safe_desc.lower():
                safe_desc = f"{a.action} on {a.entity_type} {a.entity_id or ''}".strip()

            activity_items.append(
                RecentActivityItem(
                    id=a.id,
                    action=a.action,
                    entity_type=a.entity_type,
                    entity_id=a.entity_id,
                    timestamp=a.created_at,
                    user_name=u_name,
                    description=safe_desc,
                )
            )

        return DashboardActivityResponse(activities=activity_items)


    def get_recent_reports(
        self, db: Session, org_id: int, branch_id: Optional[int] = None, limit: int = 5
    ) -> DashboardRecentReportsResponse:
        reports_q = (
            db.query(Report)
            .options(
                joinedload(Report.patient),
                joinedload(Report.order),
            )
            .filter(Report.organization_id == org_id)
            .order_by(desc(Report.generated_at))
        )

        if branch_id:
            reports_q = reports_q.filter(Report.branch_id == branch_id)

        reports = reports_q.limit(limit).all()

        rpt_items: List[RecentReportItem] = []
        for r in reports:
            p_name = f"{r.patient.first_name} {r.patient.last_name}" if r.patient else "Unknown Patient"
            o_num = r.order.order_number if r.order else "Unknown Order"

            rpt_items.append(
                RecentReportItem(
                    id=r.id,
                    report_number=r.report_number,
                    patient_name=p_name,
                    order_number=o_num,
                    generated_at=r.generated_at,
                    status=r.status,
                )
            )

        return DashboardRecentReportsResponse(reports=rpt_items)


dashboard_service = DashboardService()
