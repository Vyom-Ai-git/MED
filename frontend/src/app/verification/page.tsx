"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { AppLayout } from "@/components/layout/AppLayout";
import { Card, Table, Badge, Button, Input, Select, Toast } from "@/components/ui/primitives";
import {
  CheckSquare,
  Search,
  Filter,
  RefreshCw,
  AlertTriangle,
  Clock,
  CheckCircle2,
  FileSearch,
  RotateCcw,
  ShieldAlert,
} from "lucide-react";

interface VerificationQueueItem {
  sample: {
    id: number;
    sample_identifier: string;
    sample_type: string;
    collection_status: string;
    priority: string;
    order?: {
      id: number;
      order_number: string;
      created_at: string;
      patient?: {
        patient_id: string;
        first_name: string;
        last_name: string;
        phone: string;
      };
      tests: string[];
    };
  };
  results: {
    id: number;
    parameter_name?: string;
    raw_value?: string;
    unit?: string;
    abnormal_flag: string;
    critical_flag: boolean;
    status: string;
  }[];
  verifications: {
    id: number;
    action: string;
    performed_by_name?: string;
    reason?: string;
    created_at: string;
  }[];
  has_critical: boolean;
  has_abnormal: boolean;
  status_summary: string;
}

interface QueueResponse {
  items: VerificationQueueItem[];
  total: number;
  page: number;
  page_size: number;
  pending_count: number;
  critical_count: number;
  correction_count: number;
  verified_today_count: number;
}

export default function VerificationQueuePage() {
  const { user } = useAuth();
  const [items, setItems] = useState<VerificationQueueItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Summary Metrics
  const [pendingCount, setPendingCount] = useState(0);
  const [criticalCount, setCriticalCount] = useState(0);
  const [correctionCount, setCorrectionCount] = useState(0);
  const [verifiedTodayCount, setVerifiedTodayCount] = useState(0);

  // Filters
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [criticalOnly, setCriticalOnly] = useState(false);

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const queryParams = new URLSearchParams();
      if (search) queryParams.append("q", search);
      if (statusFilter !== "all") queryParams.append("result_status", statusFilter);
      if (priorityFilter !== "all") queryParams.append("priority", priorityFilter);
      if (criticalOnly) queryParams.append("critical_only", "true");

      const data = await api.get<QueueResponse>(`/verification?${queryParams.toString()}`);
      setItems(data.items || []);
      setTotal(data.total || 0);
      setPendingCount(data.pending_count || 0);
      setCriticalCount(data.critical_count || 0);
      setCorrectionCount(data.correction_count || 0);
      setVerifiedTodayCount(data.verified_today_count || 0);
    } catch (err: any) {
      setError(err.detail || err.message || "Error loading verification queue");
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, priorityFilter, criticalOnly]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  const columns = [
    {
      header: "Priority",
      accessor: (row: VerificationQueueItem) => (
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold uppercase ${
            row.sample.priority === "Urgent"
              ? "bg-rose-100 text-rose-800 border border-rose-300"
              : "bg-slate-100 text-slate-700 border border-slate-200"
          }`}
        >
          {row.sample.priority}
        </span>
      ),
    },
    {
      header: "Specimen / Order",
      accessor: (row: VerificationQueueItem) => (
        <div>
          <span className="font-mono font-bold text-teal-700 block text-xs">{row.sample.sample_identifier}</span>
          <span className="text-[11px] text-slate-500 font-semibold">
            {row.sample.order?.order_number || `Order #${row.sample.id}`}
          </span>
        </div>
      ),
    },
    {
      header: "Patient",
      accessor: (row: VerificationQueueItem) => (
        <div>
          {row.sample.order?.patient ? (
            <>
              <span className="font-bold text-slate-900 block text-xs">
                {row.sample.order.patient.first_name} {row.sample.order.patient.last_name}
              </span>
              <span className="text-[11px] text-slate-500 font-mono">{row.sample.order.patient.patient_id}</span>
            </>
          ) : (
            <span className="text-xs text-slate-400">Unknown</span>
          )}
        </div>
      ),
    },
    {
      header: "Tests",
      accessor: (row: VerificationQueueItem) => (
        <div className="flex flex-wrap gap-1">
          {row.sample.order?.tests && row.sample.order.tests.length > 0 ? (
            row.sample.order.tests.map((t, idx) => (
              <span key={idx} className="bg-slate-100 text-slate-700 text-[10px] font-bold px-2 py-0.5 rounded">
                {t}
              </span>
            ))
          ) : (
            <span className="text-xs text-slate-400">No test info</span>
          )}
        </div>
      ),
    },
    {
      header: "Flags & Status",
      accessor: (row: VerificationQueueItem) => (
        <div className="flex items-center gap-1.5 flex-wrap">
          {row.has_critical && (
            <span className="inline-flex items-center gap-1 bg-rose-600 text-white font-black text-[10px] uppercase px-2 py-0.5 rounded shadow-sm animate-pulse">
              <AlertTriangle className="w-3 h-3" /> CRITICAL
            </span>
          )}
          {row.has_abnormal && !row.has_critical && (
            <span className="inline-flex items-center gap-1 bg-amber-100 text-amber-800 font-bold text-[10px] uppercase px-2 py-0.5 rounded border border-amber-300">
              ABNORMAL
            </span>
          )}
          <Badge status={row.status_summary} />
        </div>
      ),
    },
    {
      header: "Action",
      accessor: (row: VerificationQueueItem) => (
        <Link href={`/verification/${row.sample.id}`}>
          <Button variant="primary" size="sm" className="bg-teal-600 hover:bg-teal-700 shadow-xs font-bold text-xs">
            <FileSearch className="w-3.5 h-3.5 mr-1" />
            Review Results
          </Button>
        </Link>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2.5">
              <CheckSquare className="w-7 h-7 text-teal-600" />
              Result Verification Queue
            </h1>
            <p className="text-xs font-semibold text-slate-500 mt-1">
              Authorized clinical reviewer console — inspect and approve laboratory results before report generation
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={loadQueue} className="self-start sm:self-auto">
            <RefreshCw className="w-3.5 h-3.5 mr-1.5" /> Refresh Queue
          </Button>
        </div>

        {error && <Toast message={error} type="error" onClose={() => setError(null)} />}

        {/* Metric Summary Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div onClick={() => { setStatusFilter("all"); setCriticalOnly(false); }} className="cursor-pointer">
            <Card className={`p-4 border transition-all ${statusFilter === "all" && !criticalOnly ? "border-teal-500 bg-teal-50/20 shadow-md" : "border-slate-200/80 hover:border-slate-300"}`}>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-slate-500 uppercase">Pending Review</span>
                <Clock className="w-4 h-4 text-teal-600" />
              </div>
              <div className="text-2xl font-black text-slate-900 mt-2">{pendingCount}</div>
            </Card>
          </div>

          <div onClick={() => { setCriticalOnly(true); }} className="cursor-pointer">
            <Card className={`p-4 border transition-all ${criticalOnly ? "border-rose-500 bg-rose-50/20 shadow-md" : "border-slate-200/80 hover:border-slate-300"}`}>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-rose-600 uppercase">Critical Results</span>
                <AlertTriangle className="w-4 h-4 text-rose-600" />
              </div>
              <div className="text-2xl font-black text-rose-900 mt-2">{criticalCount}</div>
            </Card>
          </div>

          <div onClick={() => { setStatusFilter("Correction Required"); setCriticalOnly(false); }} className="cursor-pointer">
            <Card className={`p-4 border transition-all ${statusFilter === "Correction Required" ? "border-amber-500 bg-amber-50/20 shadow-md" : "border-slate-200/80 hover:border-slate-300"}`}>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-amber-600 uppercase">Correction Required</span>
                <RotateCcw className="w-4 h-4 text-amber-600" />
              </div>
              <div className="text-2xl font-black text-amber-900 mt-2">{correctionCount}</div>
            </Card>
          </div>

          <div onClick={() => { setStatusFilter("Verified"); setCriticalOnly(false); }} className="cursor-pointer">
            <Card className={`p-4 border transition-all ${statusFilter === "Verified" ? "border-emerald-500 bg-emerald-50/20 shadow-md" : "border-slate-200/80 hover:border-slate-300"}`}>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-emerald-600 uppercase">Verified Today</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              </div>
              <div className="text-2xl font-black text-emerald-900 mt-2">{verifiedTodayCount}</div>
            </Card>
          </div>
        </div>

        {/* Filters */}
        <Card className="p-4 border border-slate-200/80 bg-slate-50/40">
          <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
            <div className="flex-1 w-full md:w-auto">
              <Input
                placeholder="Search patient, sample ID, or order number..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                icon={<Search className="w-4 h-4" />}
              />
            </div>
            <div className="flex flex-wrap gap-3 w-full md:w-auto items-center">
              <div className="w-36">
                <Select
                  options={[
                    { value: "all", label: "All Statuses" },
                    { value: "Entered", label: "Entered / Pending" },
                    { value: "Correction Required", label: "Correction Req." },
                    { value: "Verified", label: "Verified" },
                  ]}
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                />
              </div>
              <div className="w-36">
                <Select
                  options={[
                    { value: "all", label: "All Priorities" },
                    { value: "Normal", label: "Normal" },
                    { value: "Urgent", label: "Urgent" },
                  ]}
                  value={priorityFilter}
                  onChange={(e) => setPriorityFilter(e.target.value)}
                />
              </div>
              <button
                type="button"
                onClick={() => setCriticalOnly(!criticalOnly)}
                className={`px-3 py-2 text-xs font-bold rounded-lg border transition-all flex items-center gap-1.5 ${
                  criticalOnly
                    ? "bg-rose-600 text-white border-rose-600 shadow-xs"
                    : "bg-white text-slate-700 border-slate-200 hover:border-slate-300"
                }`}
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                Critical Only
              </button>
            </div>
          </div>
        </Card>

        {/* Table */}
        <Table columns={columns} data={items} isLoading={loading} emptyMessage="No laboratory results currently awaiting verification." />
      </div>
  );
}
