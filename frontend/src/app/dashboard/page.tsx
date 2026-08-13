"use client";

import React, { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Card, Badge, Button } from "@/components/ui/primitives";
import {
  Users,
  FlaskConical,
  ShoppingCart,
  FileCheck,
  Clock,
  CheckCircle,
  AlertTriangle,
  AlertCircle,
  RefreshCw,
  Calendar,
  ChevronRight,
  FileText,
  ShieldAlert,
  Activity,
  Layers,
  ArrowUpRight,
  Filter,
  UserPlus,
  FilePlus,
  ClipboardList,
  Search,
  Zap,
} from "lucide-react";
import Link from "next/link";

interface DashboardSummary {
  patients_today: number;
  total_patients: number;
  new_patients_this_week: number;
  orders_today: number;
  orders_this_week: number;
  pending_orders: number;
  verified_orders: number;
  cancelled_orders: number;
  samples_today: number;
  samples_pending_collection: number;
  samples_processing: number;
  samples_urgent: number;
  pending_results: number;
  results_draft: number;
  results_entered: number;
  results_under_review: number;
  results_verified: number;
  results_correction_required: number;
  pending_verification: number;
  critical_results: number;
  reports_available: number;
  reports_today: number;
  reports_this_week: number;
  verified_today: number;
}

interface WorkflowCounts {
  orders: number;
  samples: number;
  processing: number;
  results_pending: number;
  verification: number;
  reports: number;
}

interface TimeSeriesItem {
  date: string;
  count: number;
}


interface DashboardWorkload {
  range_type: string;
  orders: TimeSeriesItem[];
  samples: TimeSeriesItem[];
  sample_status: {
    registered_count: number;
    registered_percent: number;
    collected_count: number;
    collected_percent: number;
    processing_count: number;
    processing_percent: number;
    completed_count: number;
    completed_percent: number;
    rejected_count: number;
    rejected_percent: number;
    recollection_required_count: number;
    recollection_required_percent: number;
    total_samples: number;
  };
  priority_workload: {
    normal_count: number;
    urgent_count: number;
  };
  result_status: {
    draft_count: number;
    entered_count: number;
    under_review_count: number;
    verified_count: number;
    correction_required_count: number;
  };
}

interface TATStage {
  average_minutes: number | null;
  sample_count: number;
}

interface DashboardTAT {
  sample_to_result: TATStage;
  result_to_verification: TATStage;
  verification_to_report: TATStage;
}

interface CriticalResult {
  id: number;
  sample_id: number;
  sample_identifier: string;
  patient_id: number;
  patient_name: string;
  test_name: string;
  parameter_name: string;
  result_value: string;
  abnormal_flag: string;
  critical_flag: boolean;
  status: string;
  entered_at: string | null;
}

interface VerificationQueueItem {
  id: number;
  sample_id: number;
  sample_identifier: string;
  patient_name: string;
  order_number: string;
  tests: string[];
  has_critical: boolean;
  status: string;
  entered_at: string | null;
}

interface RecentActivity {
  id: number;
  action: string;
  entity_type: string;
  entity_id: string | null;
  timestamp: string;
  user_name: string | null;
  description: string | null;
}

interface RecentReport {
  id: number;
  report_number: string;
  patient_name: string;
  order_number: string;
  generated_at: string;
  status: string;
}

interface UserSession {
  id: number;
  name: string;
  email: string;
  role: string; // admin, reviewer, technician, reception
}

export default function DashboardPage() {
  const [user, setUser] = useState<UserSession | null>(null);
  const [rangeType, setRangeType] = useState<string>("7days");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [workload, setWorkload] = useState<DashboardWorkload | null>(null);
  const [tat, setTat] = useState<DashboardTAT | null>(null);
  const [criticals, setCriticals] = useState<CriticalResult[]>([]);
  const [vQueue, setVQueue] = useState<VerificationQueueItem[]>([]);
  const [activities, setActivities] = useState<RecentActivity[]>([]);
  const [reports, setReports] = useState<RecentReport[]>([]);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Read current logged in user from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem("labos_user");
      if (stored) {
        setUser(JSON.parse(stored));
      }
    } catch {
      // Fallback if parsing fails
    }
  }, []);

  const fetchDashboardData = useCallback(async (isManualRefresh = false) => {
    if (isManualRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    let workloadUrl = `/dashboard/workload?range_type=${rangeType}`;
    if (rangeType === "custom" && startDate && endDate) {
      workloadUrl += `&start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`;
    }
    const tatUrl = `/dashboard/tat?range_type=${rangeType === "custom" ? "custom" : rangeType}`;

    try {
      const [
        summaryRes,
        workloadRes,
        tatRes,
        criticalRes,
        vQueueRes,
        activityRes,
        reportRes,
      ] = await Promise.allSettled([
        api.get<DashboardSummary>("/dashboard/summary"),
        api.get<DashboardWorkload>(workloadUrl),
        api.get<DashboardTAT>(tatUrl),
        api.get<{ critical_results: CriticalResult[] }>("/dashboard/critical"),
        api.get<{ queue: VerificationQueueItem[] }>("/dashboard/verification-queue"),
        api.get<{ activities: RecentActivity[] }>("/dashboard/activity"),
        api.get<{ reports: RecentReport[] }>("/dashboard/recent-reports"),
      ]);

      if (summaryRes.status === "fulfilled") setSummary(summaryRes.value);
      if (workloadRes.status === "fulfilled") setWorkload(workloadRes.value);
      if (tatRes.status === "fulfilled") setTat(tatRes.value);
      if (criticalRes.status === "fulfilled") setCriticals(criticalRes.value.critical_results || []);
      if (vQueueRes.status === "fulfilled") setVQueue(vQueueRes.value.queue || []);
      if (activityRes.status === "fulfilled") setActivities(activityRes.value.activities || []);
      if (reportRes.status === "fulfilled") setReports(reportRes.value.reports || []);

      if (
        summaryRes.status === "rejected" &&
        workloadRes.status === "rejected" &&
        tatRes.status === "rejected"
      ) {
        setError("Unable to load laboratory operational metrics. Ensure backend server is running.");
      }
    } catch (err: any) {
      setError(err?.detail || "An unexpected error occurred while fetching dashboard data.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [rangeType, startDate, endDate]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const role = (user?.role || "admin").toLowerCase();

  const formatTAT = (minutes: number | null) => {
    if (minutes === null || minutes === undefined) {
      return "Not enough data";
    }
    if (minutes < 1) return "< 1 minute";
    const hrs = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    if (hrs === 0) return `${mins}m`;
    return `${hrs}h ${mins}m`;
  };

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return isoString;
    }
  };

  // Skeleton view during initial loading
  if (isLoading) {
    return (
      <div className="flex flex-col gap-6 w-full animate-pulse">
        <div className="flex items-center justify-between">
          <div className="h-8 w-48 bg-slate-200 rounded-lg" />
          <div className="h-9 w-32 bg-slate-200 rounded-lg" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white border border-slate-200 rounded-xl p-6 h-28" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl h-72" />
          <div className="bg-white border border-slate-200 rounded-xl h-72" />
        </div>
      </div>
    );
  }

  // Full page error fallback if completely unavailable
  if (error && !summary) {
    return (
      <div className="flex flex-col items-center justify-center py-16 bg-white border border-slate-200 rounded-xl p-8 max-w-lg mx-auto w-full text-center">
        <div className="w-12 h-12 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center mb-4">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h3 className="text-base font-bold text-slate-900">Dashboard Unavailable</h3>
        <p className="text-sm text-slate-500 mt-2">{error}</p>
        <button
          onClick={() => fetchDashboardData(true)}
          className="mt-5 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-2 mx-auto"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Retry Loading
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      {/* Top Header & Range Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">
              {role === "admin" && "Laboratory Operations Dashboard"}
              {role === "reviewer" && "Reviewer Operational Workstation"}
              {role === "technician" && "Technician Operational Workstation"}
              {role === "reception" && "Reception Operations Desk"}
            </h1>
            <span className="text-[11px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
              {role}
            </span>
          </div>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            Real-time database analytics and workflow tracking for {user?.name || "Laboratory User"}.
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Range Selector */}
          <div className="flex items-center bg-slate-100/80 p-1 rounded-xl border border-slate-200">
            {["today", "7days", "30days", "custom"].map((r) => (
              <button
                key={r}
                onClick={() => setRangeType(r)}
                className={`px-3 py-1.2 text-xs font-bold rounded-lg transition-all ${
                  rangeType === r
                    ? "bg-white text-teal-700 shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {r === "today" && "Today"}
                {r === "7days" && "7 Days"}
                {r === "30days" && "30 Days"}
                {r === "custom" && "Custom"}
              </button>
            ))}
          </div>

          {rangeType === "custom" && (
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="text-xs font-semibold px-2 py-1 border border-slate-200 rounded-lg outline-none focus:ring-1 focus:ring-teal-500"
              />
              <span className="text-xs font-bold text-slate-400">to</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="text-xs font-semibold px-2 py-1 border border-slate-200 rounded-lg outline-none focus:ring-1 focus:ring-teal-500"
              />
            </div>
          )}

          {/* Refresh Button */}
          <button
            onClick={() => fetchDashboardData(true)}
            disabled={isRefreshing}
            className="p-2 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 transition-colors shadow-sm disabled:opacity-50"
            title="Refresh metrics"
            aria-label="Refresh metrics"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin text-teal-600" : ""}`} />
          </button>
        </div>
      </div>

      {/* Role-Based Quick Actions Bar */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        <span className="text-xs font-bold text-slate-400 uppercase tracking-wider whitespace-nowrap mr-1">
          Quick Actions:
        </span>
        {role === "admin" && (
          <>
            <Link href="/patients" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-bold text-slate-700 hover:bg-teal-50 hover:text-teal-700 hover:border-teal-200 transition-all shadow-2xs">
              <UserPlus className="w-3.5 h-3.5 text-teal-600" /> Register Patient
            </Link>
            <Link href="/orders" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-bold text-slate-700 hover:bg-teal-50 hover:text-teal-700 hover:border-teal-200 transition-all shadow-2xs">
              <FilePlus className="w-3.5 h-3.5 text-indigo-600" /> Create Order
            </Link>
            <Link href="/samples" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-bold text-slate-700 hover:bg-teal-50 hover:text-teal-700 hover:border-teal-200 transition-all shadow-2xs">
              <FlaskConical className="w-3.5 h-3.5 text-emerald-600" /> Register Sample
            </Link>
            <Link href="/verification" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-bold text-slate-700 hover:bg-teal-50 hover:text-teal-700 hover:border-teal-200 transition-all shadow-2xs">
              <ShieldAlert className="w-3.5 h-3.5 text-amber-600" /> Open Verification
            </Link>
            <Link href="/reports" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-bold text-slate-700 hover:bg-teal-50 hover:text-teal-700 hover:border-teal-200 transition-all shadow-2xs">
              <FileText className="w-3.5 h-3.5 text-blue-600" /> View Reports
            </Link>
            <Link href="/settings/integrations" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-bold text-slate-700 hover:bg-teal-50 hover:text-teal-700 hover:border-teal-200 transition-all shadow-2xs">
              <Zap className="w-3.5 h-3.5 text-amber-500" /> Automation
            </Link>
            <Link href="/audit" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-bold text-slate-700 hover:bg-teal-50 hover:text-teal-700 hover:border-teal-200 transition-all shadow-2xs">
              <Activity className="w-3.5 h-3.5 text-slate-600" /> View Audit
            </Link>
          </>
        )}
        {role === "reviewer" && (
          <>
            <Link href="/verification" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-teal-600 text-white rounded-lg text-xs font-bold hover:bg-teal-700 transition-all shadow-xs">
              <ShieldAlert className="w-3.5 h-3.5" /> Review Results
            </Link>
            <Link href="/reports" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-bold text-slate-700 hover:bg-slate-50 transition-all shadow-2xs">
              <FileText className="w-3.5 h-3.5 text-blue-600" /> View Reports
            </Link>
          </>
        )}
        {role === "technician" && (
          <>
            <Link href="/samples" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-bold hover:bg-emerald-700 transition-all shadow-xs">
              <FlaskConical className="w-3.5 h-3.5" /> Register Sample
            </Link>
            <Link href="/worklist" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-bold text-slate-700 hover:bg-slate-50 transition-all shadow-2xs">
              <ClipboardList className="w-3.5 h-3.5 text-teal-600" /> Open Worklist
            </Link>
            <Link href="/results" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-bold text-slate-700 hover:bg-slate-50 transition-all shadow-2xs">
              <FileCheck className="w-3.5 h-3.5 text-indigo-600" /> Enter Results
            </Link>
          </>
        )}
        {role === "reception" && (
          <>
            <Link href="/patients" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-teal-600 text-white rounded-lg text-xs font-bold hover:bg-teal-700 transition-all shadow-xs">
              <UserPlus className="w-3.5 h-3.5" /> Register Patient
            </Link>
            <Link href="/orders" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-bold text-slate-700 hover:bg-slate-50 transition-all shadow-2xs">
              <FilePlus className="w-3.5 h-3.5 text-indigo-600" /> Create Order
            </Link>
            <Link href="/patients" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-bold text-slate-700 hover:bg-slate-50 transition-all shadow-2xs">
              <Users className="w-3.5 h-3.5 text-slate-600" /> View Patients
            </Link>
            <Link href="/orders" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-bold text-slate-700 hover:bg-slate-50 transition-all shadow-2xs">
              <ShoppingCart className="w-3.5 h-3.5 text-slate-600" /> View Orders
            </Link>
          </>
        )}
      </div>

      {/* ========================================================= */}
      {/* KPI CARDS SECTION (Role-Adapted)                          */}
      {/* ========================================================= */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {role === "admin" && (
          <>
            <Card className="p-5 border border-slate-200/80 shadow-2xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Total Patients</span>
                  <div className="text-2xl font-black text-slate-900 mt-1 tracking-tight">{summary?.total_patients ?? 0}</div>
                  <span className="text-[11px] font-semibold text-slate-500 mt-0.5 block">
                    {summary?.patients_today ?? 0} new today
                  </span>
                </div>
                <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-100 text-blue-600 flex items-center justify-center">
                  <Users className="w-5 h-5" />
                </div>
              </div>
            </Card>

            <Card className="p-5 border border-slate-200/80 shadow-2xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Orders Today</span>
                  <div className="text-2xl font-black text-slate-900 mt-1 tracking-tight">{summary?.orders_today ?? 0}</div>
                  <span className="text-[11px] font-semibold text-amber-600 mt-0.5 block">
                    {summary?.pending_orders ?? 0} pending
                  </span>
                </div>
                <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center">
                  <ShoppingCart className="w-5 h-5" />
                </div>
              </div>
            </Card>

            <Card className="p-5 border border-slate-200/80 shadow-2xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Samples Today</span>
                  <div className="text-2xl font-black text-slate-900 mt-1 tracking-tight">{summary?.samples_today ?? 0}</div>
                  <span className="text-[11px] font-semibold text-teal-600 mt-0.5 block">
                    {summary?.samples_processing ?? 0} processing
                  </span>
                </div>
                <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-100 text-teal-600 flex items-center justify-center">
                  <FlaskConical className="w-5 h-5" />
                </div>
              </div>
            </Card>

            <Card className="p-5 border border-slate-200/80 shadow-2xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Pending Verification</span>
                  <div className="text-2xl font-black text-amber-600 mt-1 tracking-tight">{summary?.pending_verification ?? 0}</div>
                  <span className="text-[11px] font-semibold text-rose-600 mt-0.5 block">
                    {summary?.critical_results ?? 0} critical
                  </span>
                </div>
                <div className="w-10 h-10 rounded-xl bg-amber-50 border border-amber-100 text-amber-600 flex items-center justify-center">
                  <ShieldAlert className="w-5 h-5" />
                </div>
              </div>
            </Card>
          </>
        )}

        {role === "reviewer" && (
          <>
            <Card className="p-5 border border-amber-200/80 bg-amber-50/20 shadow-2xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-amber-700 uppercase tracking-wider">Pending Verification</span>
                  <div className="text-3xl font-black text-amber-900 mt-1 tracking-tight">{summary?.pending_verification ?? 0}</div>
                  <span className="text-[11px] font-medium text-amber-700 mt-0.5 block">Awaiting review</span>
                </div>
                <div className="w-10 h-10 rounded-xl bg-amber-100 border border-amber-200 text-amber-700 flex items-center justify-center">
                  <ShieldAlert className="w-5 h-5" />
                </div>
              </div>
            </Card>

            <Card className="p-5 border border-rose-200/80 bg-rose-50/20 shadow-2xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-rose-700 uppercase tracking-wider">Critical Results</span>
                  <div className="text-3xl font-black text-rose-900 mt-1 tracking-tight">{summary?.critical_results ?? 0}</div>
                  <span className="text-[11px] font-medium text-rose-700 mt-0.5 block">Requires immediate action</span>
                </div>
                <div className="w-10 h-10 rounded-xl bg-rose-100 border border-rose-200 text-rose-700 flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5" />
                </div>
              </div>
            </Card>

            <Card className="p-5 border border-indigo-200/80 bg-indigo-50/20 shadow-2xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-indigo-700 uppercase tracking-wider">Correction Required</span>
                  <div className="text-3xl font-black text-indigo-900 mt-1 tracking-tight">{summary?.results_correction_required ?? 0}</div>
                  <span className="text-[11px] font-medium text-indigo-700 mt-0.5 block">Returned for amendment</span>
                </div>
                <div className="w-10 h-10 rounded-xl bg-indigo-100 border border-indigo-200 text-indigo-700 flex items-center justify-center">
                  <FileCheck className="w-5 h-5" />
                </div>
              </div>
            </Card>

            <Card className="p-5 border border-emerald-200/80 bg-emerald-50/20 shadow-2xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-emerald-700 uppercase tracking-wider">Verified Today</span>
                  <div className="text-3xl font-black text-emerald-900 mt-1 tracking-tight">{summary?.verified_today ?? 0}</div>
                  <span className="text-[11px] font-medium text-emerald-700 mt-0.5 block">Signed off today</span>
                </div>
                <div className="w-10 h-10 rounded-xl bg-emerald-100 border border-emerald-200 text-emerald-700 flex items-center justify-center">
                  <CheckCircle className="w-5 h-5" />
                </div>
              </div>
            </Card>
          </>
        )}

        {role === "technician" && (
          <>
            <Card className="p-5 border border-slate-200/80 shadow-2xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Pending Collection</span>
                  <div className="text-2xl font-black text-slate-900 mt-1 tracking-tight">{summary?.samples_pending_collection ?? 0}</div>
                  <span className="text-[11px] font-semibold text-slate-500 mt-0.5 block">Registered samples</span>
                </div>
                <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center">
                  <Clock className="w-5 h-5" />
                </div>
              </div>
            </Card>

            <Card className="p-5 border border-teal-200/80 bg-teal-50/20 shadow-2xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-teal-700 uppercase tracking-wider">Samples Processing</span>
                  <div className="text-2xl font-black text-teal-900 mt-1 tracking-tight">{summary?.samples_processing ?? 0}</div>
                  <span className="text-[11px] font-semibold text-teal-700 mt-0.5 block">In progress</span>
                </div>
                <div className="w-10 h-10 rounded-xl bg-teal-100 text-teal-700 flex items-center justify-center">
                  <FlaskConical className="w-5 h-5" />
                </div>
              </div>
            </Card>

            <Card className="p-5 border border-amber-200/80 bg-amber-50/20 shadow-2xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-amber-700 uppercase tracking-wider">Results Pending</span>
                  <div className="text-2xl font-black text-amber-900 mt-1 tracking-tight">{summary?.pending_results ?? 0}</div>
                  <span className="text-[11px] font-semibold text-amber-700 mt-0.5 block">Needs entry</span>
                </div>
                <div className="w-10 h-10 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center">
                  <FileCheck className="w-5 h-5" />
                </div>
              </div>
            </Card>

            <Card className="p-5 border border-rose-200/80 bg-rose-50/20 shadow-2xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-rose-700 uppercase tracking-wider">Urgent Samples</span>
                  <div className="text-2xl font-black text-rose-900 mt-1 tracking-tight">{summary?.samples_urgent ?? 0}</div>
                  <span className="text-[11px] font-semibold text-rose-700 mt-0.5 block">STAT priority</span>
                </div>
                <div className="w-10 h-10 rounded-xl bg-rose-100 text-rose-700 flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5" />
                </div>
              </div>
            </Card>
          </>
        )}

        {role === "reception" && (
          <>
            <Card className="p-5 border border-slate-200/80 shadow-2xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Patients Today</span>
                  <div className="text-2xl font-black text-slate-900 mt-1 tracking-tight">{summary?.patients_today ?? 0}</div>
                  <span className="text-[11px] font-semibold text-slate-500 mt-0.5 block">Total: {summary?.total_patients ?? 0}</span>
                </div>
                <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                  <Users className="w-5 h-5" />
                </div>
              </div>
            </Card>

            <Card className="p-5 border border-slate-200/80 shadow-2xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Orders Today</span>
                  <div className="text-2xl font-black text-slate-900 mt-1 tracking-tight">{summary?.orders_today ?? 0}</div>
                  <span className="text-[11px] font-semibold text-amber-600 mt-0.5 block">{summary?.pending_orders ?? 0} pending</span>
                </div>
                <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                  <ShoppingCart className="w-5 h-5" />
                </div>
              </div>
            </Card>

            <Card className="p-5 border border-slate-200/80 shadow-2xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Pending Collection</span>
                  <div className="text-2xl font-black text-slate-900 mt-1 tracking-tight">{summary?.samples_pending_collection ?? 0}</div>
                  <span className="text-[11px] font-semibold text-slate-500 mt-0.5 block">Awaiting phlebotomy</span>
                </div>
                <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                  <Clock className="w-5 h-5" />
                </div>
              </div>
            </Card>

            <Card className="p-5 border border-slate-200/80 shadow-2xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Reports Available</span>
                  <div className="text-2xl font-black text-teal-700 mt-1 tracking-tight">{summary?.reports_available ?? 0}</div>
                  <span className="text-[11px] font-semibold text-teal-600 mt-0.5 block">Ready for patient</span>
                </div>
                <div className="w-10 h-10 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center">
                  <FileText className="w-5 h-5" />
                </div>
              </div>
            </Card>
          </>
        )}
      </div>

      {/* ========================================================= */}
      {/* PROMINENT CRITICAL RESULTS ALERT SECTION (All / Reviewer)  */}
      {/* ========================================================= */}
      {criticals.length > 0 && (role === "admin" || role === "reviewer" || role === "technician") && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-5 shadow-xs">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-rose-600 animate-ping" />
              <h2 className="text-sm font-extrabold text-rose-900 tracking-tight flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-rose-600" />
                Critical Results Requiring Immediate Action ({criticals.length})
              </h2>
            </div>
            {(role === "admin" || role === "reviewer") && (
              <Link href="/verification" className="text-xs font-bold text-rose-700 hover:text-rose-900 underline flex items-center gap-1">
                Open Verification Queue <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-rose-200 text-[11px] font-bold text-rose-700 uppercase">
                  <th className="pb-2">Sample ID</th>
                  <th className="pb-2">Patient</th>
                  <th className="pb-2">Test / Parameter</th>
                  <th className="pb-2">Result Value</th>
                  <th className="pb-2">Flag</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rose-100 text-xs">
                {criticals.map((c) => (
                  <tr key={c.id} className="hover:bg-rose-100/50">
                    <td className="py-2.5 font-bold text-slate-900">{c.sample_identifier}</td>
                    <td className="py-2.5 font-semibold text-slate-800">{c.patient_name}</td>
                    <td className="py-2.5 text-slate-700">
                      <span className="font-semibold">{c.test_name}</span> — {c.parameter_name}
                    </td>
                    <td className="py-2.5 font-black text-rose-700">{c.result_value}</td>
                    <td className="py-2.5">
                      <span className="px-2 py-0.5 rounded text-[10px] font-black bg-rose-600 text-white uppercase">
                        CRITICAL {c.abnormal_flag}
                      </span>
                    </td>
                    <td className="py-2.5">
                      <Badge status={c.status} />
                    </td>
                    <td className="py-2.5 text-right">
                      {(role === "admin" || role === "reviewer") ? (
                        <Link
                          href={`/verification/${c.sample_id}`}
                          className="px-2.5 py-1 bg-rose-600 hover:bg-rose-700 text-white rounded font-bold text-[11px] inline-flex items-center gap-1 shadow-2xs"
                        >
                          Review <ArrowUpRight className="w-3 h-3" />
                        </Link>
                      ) : (
                        <span className="text-[11px] text-slate-400 font-medium">Under Review</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* OPERATIONAL WORKFLOW FUNNEL (Admin / Technician)           */}
      {/* ========================================================= */}
      {(role === "admin" || role === "technician") && (
        <Card title="Operational Workflow Funnel" subtitle="Real-time count of items progressing through laboratory pipeline">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 py-2">
            {[
              { label: "Orders", count: summary?.orders_today ?? 0, color: "border-indigo-200 bg-indigo-50/40 text-indigo-700" },
              { label: "Samples", count: summary?.samples_today ?? 0, color: "border-slate-200 bg-slate-50 text-slate-700" },
              { label: "Processing", count: summary?.samples_processing ?? 0, color: "border-teal-200 bg-teal-50/40 text-teal-700" },
              { label: "Results Pending", count: summary?.pending_results ?? 0, color: "border-amber-200 bg-amber-50/40 text-amber-700" },
              { label: "Verification", count: summary?.pending_verification ?? 0, color: "border-purple-200 bg-purple-50/40 text-purple-700" },
              { label: "Reports", count: summary?.reports_today ?? 0, color: "border-emerald-200 bg-emerald-50/40 text-emerald-700" },
            ].map((stage, idx, arr) => (
              <div key={idx} className={`p-3 rounded-xl border flex flex-col items-center justify-center text-center ${stage.color}`}>
                <span className="text-[10px] font-extrabold uppercase tracking-wider opacity-80">{stage.label}</span>
                <span className="text-xl font-black mt-1 tracking-tight">{stage.count}</span>
                {idx < arr.length - 1 && (
                  <span className="text-[10px] text-slate-400 mt-1 hidden lg:block">→ next</span>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* ========================================================= */}
      {/* WORKLOAD CHARTS & BREAKDOWNS                              */}
      {/* ========================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Workload Time-Series Chart */}
        <Card
          title="Daily Workload Volume"
          subtitle={`Orders & Samples volume (${rangeType === "7days" ? "Last 7 Days" : rangeType})`}
          className="lg:col-span-2"
        >
          {workload?.orders && workload.orders.length > 0 ? (
            <div className="flex flex-col gap-4">
              <div className="h-48 flex items-end justify-between gap-2 pt-6 pb-2 px-2 border-b border-slate-100">
                {workload.orders.map((ord, idx) => {
                  const smpCount = workload.samples[idx]?.count ?? 0;
                  const maxVal = Math.max(
                    ...workload.orders.map((o) => o.count),
                    ...workload.samples.map((s) => s.count),
                    1
                  );
                  const ordHeightPct = Math.round((ord.count / maxVal) * 100);
                  const smpHeightPct = Math.round((smpCount / maxVal) * 100);

                  return (
                    <div key={ord.date} className="flex-1 flex flex-col items-center gap-1 group">
                      <div className="w-full flex items-end justify-center gap-1 h-36">
                        {/* Order Bar */}
                        <div
                          style={{ height: `${Math.max(ordHeightPct, 6)}%` }}
                          className="w-full max-w-[16px] bg-indigo-500 hover:bg-indigo-600 rounded-t-sm transition-all relative"
                          title={`Orders on ${ord.date}: ${ord.count}`}
                        >
                          <span className="opacity-0 group-hover:opacity-100 absolute -top-6 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-[9px] font-bold px-1 py-0.5 rounded pointer-events-none transition-opacity">
                            {ord.count}
                          </span>
                        </div>
                        {/* Sample Bar */}
                        <div
                          style={{ height: `${Math.max(smpHeightPct, 6)}%` }}
                          className="w-full max-w-[16px] bg-teal-500 hover:bg-teal-600 rounded-t-sm transition-all relative"
                          title={`Samples on ${ord.date}: ${smpCount}`}
                        >
                          <span className="opacity-0 group-hover:opacity-100 absolute -top-6 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-[9px] font-bold px-1 py-0.5 rounded pointer-events-none transition-opacity">
                            {smpCount}
                          </span>
                        </div>
                      </div>
                      <span className="text-[10px] font-semibold text-slate-400 tracking-tighter truncate w-full text-center">
                        {ord.date.slice(5)}
                      </span>
                    </div>
                  );
                })}
              </div>

              <div className="flex items-center justify-center gap-6 text-xs font-semibold text-slate-600">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-xs bg-indigo-500" />
                  <span>Orders</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-xs bg-teal-500" />
                  <span>Samples Collected</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-slate-400 text-xs font-medium">
              No workload data recorded for this time range.
            </div>
          )}
        </Card>

        {/* Turnaround Time (TAT) Widget */}
        <Card title="Laboratory Turnaround Time (TAT)" subtitle="Average duration across workflow stages">
          <div className="flex flex-col gap-4">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-700">Sample Collection → Result Entry</span>
                <span className="font-extrabold text-teal-700 text-sm">
                  {formatTAT(tat?.sample_to_result?.average_minutes ?? null)}
                </span>
              </div>
              <span className="text-[10px] text-slate-400 mt-1 block">
                Based on {tat?.sample_to_result?.sample_count ?? 0} samples
              </span>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-700">Result Entry → Verification</span>
                <span className="font-extrabold text-indigo-700 text-sm">
                  {formatTAT(tat?.result_to_verification?.average_minutes ?? null)}
                </span>
              </div>
              <span className="text-[10px] text-slate-400 mt-1 block">
                Based on {tat?.result_to_verification?.sample_count ?? 0} verifications
              </span>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-700">Verification → Report Generation</span>
                <span className="font-extrabold text-emerald-700 text-sm">
                  {formatTAT(tat?.verification_to_report?.average_minutes ?? null)}
                </span>
              </div>
              <span className="text-[10px] text-slate-400 mt-1 block">
                Based on {tat?.verification_to_report?.sample_count ?? 0} reports
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* ========================================================= */}
      {/* SAMPLE & RESULT BREAKDOWNS (Admin / Tech)                  */}
      {/* ========================================================= */}
      {(role === "admin" || role === "technician") && workload?.sample_status && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Sample Status Breakdown */}
          <Card title="Sample Operations Breakdown" subtitle="Distribution of current sample states">
            <div className="flex flex-col gap-2.5 text-xs">
              {[
                { label: "Registered", count: workload.sample_status.registered_count, pct: workload.sample_status.registered_percent, color: "bg-slate-400" },
                { label: "Collected", count: workload.sample_status.collected_count, pct: workload.sample_status.collected_percent, color: "bg-blue-500" },
                { label: "Processing", count: workload.sample_status.processing_count, pct: workload.sample_status.processing_percent, color: "bg-teal-500" },
                { label: "Completed", count: workload.sample_status.completed_count, pct: workload.sample_status.completed_percent, color: "bg-emerald-500" },
                { label: "Rejected", count: workload.sample_status.rejected_count, pct: workload.sample_status.rejected_percent, color: "bg-rose-500" },
                { label: "Recollection Req.", count: workload.sample_status.recollection_required_count, pct: workload.sample_status.recollection_required_percent, color: "bg-amber-500" },
              ].map((item) => (
                <div key={item.label} className="flex flex-col gap-1">
                  <div className="flex items-center justify-between font-semibold">
                    <span className="text-slate-700">{item.label}</span>
                    <span className="font-bold text-slate-900">
                      {item.count} ({item.pct}%)
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                    <div style={{ width: `${item.pct}%` }} className={`h-full ${item.color}`} />
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Priority Workload Breakdown */}
          <Card title="Priority Workload" subtitle="Normal vs STAT priority samples">
            <div className="flex flex-col gap-4 py-2">
              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-slate-600" />
                  <span className="text-xs font-bold text-slate-700">Normal Priority</span>
                </div>
                <span className="text-base font-extrabold text-slate-900">{workload.priority_workload.normal_count}</span>
              </div>

              <div className="flex items-center justify-between p-3 rounded-xl bg-rose-50 border border-rose-100">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-rose-600" />
                  <span className="text-xs font-bold text-rose-900">Urgent (STAT) Priority</span>
                </div>
                <span className="text-base font-extrabold text-rose-700">{workload.priority_workload.urgent_count}</span>
              </div>
            </div>
          </Card>

          {/* Result Workload Breakdown */}
          <Card title="Result Workload" subtitle="Result state categories">
            <div className="flex flex-col gap-2.5 text-xs">
              {[
                { label: "Draft", count: workload.result_status.draft_count, color: "text-slate-600" },
                { label: "Entered", count: workload.result_status.entered_count, color: "text-indigo-600" },
                { label: "Under Review", count: workload.result_status.under_review_count, color: "text-amber-600" },
                { label: "Verified", count: workload.result_status.verified_count, color: "text-emerald-600" },
                { label: "Correction Required", count: workload.result_status.correction_required_count, color: "text-rose-600" },
              ].map((r) => (
                <div key={r.label} className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100/60">
                  <span className="font-bold text-slate-700">{r.label}</span>
                  <span className={`font-black ${r.color}`}>{r.count}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* ========================================================= */}
      {/* VERIFICATION QUEUE & RECENT REPORTS                       */}
      {/* ========================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pending Verification Queue */}
        <Card
          title="Pending Verification Queue"
          subtitle="Samples waiting for reviewer sign-off"
          headerAction={
            (role === "admin" || role === "reviewer") ? (
              <Link href="/verification" className="text-xs font-bold text-teal-600 hover:text-teal-700 flex items-center gap-1">
                View All Queue <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            ) : undefined
          }
          className="lg:col-span-2"
        >
          {vQueue.length === 0 ? (
            <div className="text-center py-10 text-slate-400 text-xs font-medium">
              No samples currently awaiting verification.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-100 text-xs font-semibold text-slate-400">
                    <th className="pb-3">Sample ID</th>
                    <th className="pb-3">Patient</th>
                    <th className="pb-3">Order</th>
                    <th className="pb-3">Tests</th>
                    <th className="pb-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs">
                  {vQueue.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50/50">
                      <td className="py-3 font-bold text-slate-900 flex items-center gap-1.5">
                        {item.sample_identifier}
                        {item.has_critical && (
                          <span className="px-1.5 py-0.2 rounded text-[9px] font-black bg-rose-600 text-white">
                            CRITICAL
                          </span>
                        )}
                      </td>
                      <td className="py-3 text-slate-700 font-semibold">{item.patient_name}</td>
                      <td className="py-3 text-slate-500 font-mono text-[11px]">{item.order_number}</td>
                      <td className="py-3 text-slate-600 truncate max-w-[150px]">
                        {item.tests.join(", ") || "Parameters"}
                      </td>
                      <td className="py-3 text-right">
                        {(role === "admin" || role === "reviewer") ? (
                          <Link
                            href={`/verification/${item.sample_id}`}
                            className="px-3 py-1 bg-teal-600 hover:bg-teal-700 text-white rounded-md text-xs font-bold transition-all inline-flex items-center gap-1 shadow-2xs"
                          >
                            Review <ArrowUpRight className="w-3.5 h-3.5" />
                          </Link>
                        ) : (
                          <span className="text-slate-400 text-xs">Pending Review</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Recent Generated Reports */}
        <Card
          title="Recent Reports"
          subtitle="Latest generated PDF reports"
          headerAction={
            <Link href="/reports" className="text-xs font-bold text-teal-600 hover:text-teal-700">
              View All
            </Link>
          }
        >
          {reports.length === 0 ? (
            <div className="text-center py-10 text-slate-400 text-xs font-medium">
              No reports generated recently.
            </div>
          ) : (
            <div className="flex flex-col divide-y divide-slate-100 text-xs">
              {reports.map((rpt) => (
                <div key={rpt.id} className="py-3 flex items-center justify-between">
                  <div>
                    <span className="font-bold text-slate-800 block">{rpt.report_number}</span>
                    <span className="text-slate-500 text-[11px] block">{rpt.patient_name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge status={rpt.status} />
                    <Link
                      href={`/reports`}
                      className="text-xs font-bold text-teal-600 hover:text-teal-700 p-1 hover:bg-teal-50 rounded"
                      title="View Report"
                    >
                      <ArrowUpRight className="w-4 h-4" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* ========================================================= */}
      {/* RECENT AUDIT ACTIVITY FEED (Admin / Reviewer)            */}
      {/* ========================================================= */}
      {(role === "admin" || role === "reviewer") && (
        <Card title="Recent Laboratory Audit Activity" subtitle="Safe operational events audit feed">
          {activities.length === 0 ? (
            <div className="text-center py-8 text-slate-400 text-xs font-medium">
              No recent audit activity logged.
            </div>
          ) : (
            <div className="flex flex-col divide-y divide-slate-100 text-xs">
              {activities.map((act) => (
                <div key={act.id} className="py-2.5 flex items-center justify-between hover:bg-slate-50/50 px-2 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-teal-500" />
                    <div>
                      <span className="font-bold text-slate-800">{act.description}</span>
                      <span className="text-slate-400 text-[11px] block mt-0.5">
                        By {act.user_name || "System"} • Entity: {act.entity_type} {act.entity_id ? `#${act.entity_id}` : ""}
                      </span>
                    </div>
                  </div>
                  <span className="text-[11px] font-semibold text-slate-400">
                    {formatDate(act.timestamp)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
