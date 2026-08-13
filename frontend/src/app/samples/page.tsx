"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { Button, Card, Badge, Modal, Toast } from "@/components/ui/primitives";
import {
  Layers, Search, Filter, RefreshCw, ChevronLeft, ChevronRight,
  Eye, XCircle, CheckCircle2, Clock, AlertTriangle, Plus, FileText
} from "lucide-react";

interface PatientSummary {
  id: number;
  patient_id: string;
  first_name: string;
  last_name: string;
  phone: string;
  gender: string;
}

interface OrderSummary {
  id: number;
  order_number: string;
  created_at: string;
  patient?: PatientSummary;
  tests: string[];
}

interface Sample {
  id: number;
  organization_id: number;
  order_id: number;
  sample_identifier: string;
  sample_type: string;
  collection_status: string;
  priority: string;
  collected_at?: string;
  processing_started_at?: string;
  processing_completed_at?: string;
  rejection_reason?: string;
  recollection_required: boolean;
  notes?: string;
  created_at: string;
  order?: OrderSummary;
}

interface SampleListResponse {
  items: Sample[];
  total: number;
  page: number;
  page_size: number;
}

const STATUS_OPTIONS = ["", "Registered", "Collected", "Processing", "Completed", "Rejected", "Recollection Required"];
const SAMPLE_TYPES = ["", "Blood", "Serum", "Plasma", "Urine", "Stool", "Swab", "Other"];

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    "Registered": "bg-slate-100 text-slate-700 border-slate-200",
    "Collected": "bg-blue-100 text-blue-800 border-blue-200",
    "Processing": "bg-violet-100 text-violet-800 border-violet-200",
    "Completed": "bg-emerald-100 text-emerald-800 border-emerald-200",
    "Rejected": "bg-rose-100 text-rose-800 border-rose-200",
    "Recollection Required": "bg-amber-100 text-amber-800 border-amber-200",
    "Cancelled": "bg-slate-100 text-slate-500 border-slate-200",
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${map[status] || "bg-slate-100 text-slate-700 border-slate-200"}`}>
      {status}
    </span>
  );
}

export default function SamplesPage() {
  const router = useRouter();
  const { user } = useAuth();

  const [samplesData, setSamplesData] = useState<SampleListResponse>({ items: [], total: 0, page: 1, page_size: 10 });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Rejection modal
  const [rejectTarget, setRejectTarget] = useState<Sample | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [isRejecting, setIsRejecting] = useState(false);

  // Status transition loading
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  const canManageSamples = user?.role === "admin" || user?.role === "technician";

  const fetchSamples = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        page_size: pageSize.toString(),
      });
      if (searchQuery.trim()) params.set("q", searchQuery.trim());
      if (statusFilter) params.set("status", statusFilter);
      if (priorityFilter) params.set("priority", priorityFilter);
      if (typeFilter) params.set("sample_type", typeFilter);

      const data = await api.get<SampleListResponse>(`/samples?${params}`);
      setSamplesData(data);
    } catch (err: any) {
      setError(err.detail || "Failed to load sample registry.");
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, searchQuery, statusFilter, priorityFilter, typeFilter]);

  useEffect(() => {
    fetchSamples();
  }, [fetchSamples]);

  const handleStatusChange = async (sample: Sample, nextStatus: string) => {
    setUpdatingId(sample.id);
    try {
      await api.patch(`/samples/${sample.id}/status`, { status: nextStatus });
      setSuccessMessage(`Sample ${sample.sample_identifier} status updated to ${nextStatus}.`);
      fetchSamples();
    } catch (err: any) {
      setError(err.detail || "Failed to update sample status.");
    } finally {
      setUpdatingId(null);
    }
  };

  const handleRejectSubmit = async () => {
    if (!rejectTarget || !rejectReason.trim()) return;
    setIsRejecting(true);
    try {
      await api.post(`/samples/${rejectTarget.id}/reject`, { rejection_reason: rejectReason.trim() });
      setSuccessMessage(`Sample ${rejectTarget.sample_identifier} rejected. Recollection required.`);
      setRejectTarget(null);
      setRejectReason("");
      fetchSamples();
    } catch (err: any) {
      setError(err.detail || "Failed to reject sample.");
    } finally {
      setIsRejecting(false);
    }
  };

  const totalPages = Math.ceil(samplesData.total / pageSize);

  return (
    <div className="flex flex-col gap-6 w-full animate-in fade-in duration-200">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-teal-600 font-black uppercase tracking-wider">
              Laboratory Specimen Registry
            </span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight mt-0.5">
            Samples Tracker
          </h1>
          <p className="text-xs font-semibold text-slate-500 mt-1">
            Track laboratory specimens from collection through processing and recollection.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            onClick={fetchSamples}
            className="border-slate-200/80 bg-white hover:bg-slate-50 font-bold text-xs shadow-sm h-9"
          >
            <RefreshCw className="w-3.5 h-3.5 mr-1.5" /> Refresh
          </Button>
        </div>
      </div>

      {/* Toast Notifications */}
      {successMessage && <Toast message={successMessage} type="success" onClose={() => setSuccessMessage(null)} />}
      {error && <Toast message={error} type="error" onClose={() => setError(null)} />}

      {/* Filter Bar */}
      <Card className="p-4 border border-slate-200/80 shadow-sm flex flex-col md:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search Sample ID, Order #, Patient name or phone..."
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
            className="w-full pl-9 pr-4 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
          />
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setCurrentPage(1); }}
            className="px-3 py-2 text-xs border border-slate-200 rounded-lg bg-white font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
          >
            <option value="">All Statuses</option>
            {STATUS_OPTIONS.filter(Boolean).map(s => <option key={s} value={s}>{s}</option>)}
          </select>

          <select
            value={typeFilter}
            onChange={(e) => { setTypeFilter(e.target.value); setCurrentPage(1); }}
            className="px-3 py-2 text-xs border border-slate-200 rounded-lg bg-white font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
          >
            <option value="">All Sample Types</option>
            {SAMPLE_TYPES.filter(Boolean).map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
      </Card>

      {/* Samples Table */}
      <Card className="p-0 border border-slate-200/80 shadow-sm overflow-hidden flex flex-col">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/80 text-[10px] font-black text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">Priority</th>
                <th className="py-3 px-4">Sample ID</th>
                <th className="py-3 px-4">Order #</th>
                <th className="py-3 px-4">Patient</th>
                <th className="py-3 px-4">Sample Type</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Collected At</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <div className="w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                    Loading sample registry...
                  </td>
                </tr>
              ) : samplesData.items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500">
                    <Layers className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                    No laboratory samples found matching filters.
                  </td>
                </tr>
              ) : (
                samplesData.items.map((sample) => (
                  <tr key={sample.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4">
                      {sample.priority === "Urgent" ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-black bg-rose-100 text-rose-800 border border-rose-200">
                          URGENT
                        </span>
                      ) : (
                        <span className="text-[11px] font-semibold text-slate-500">Normal</span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-extrabold text-slate-900 tracking-tight">
                      {sample.sample_identifier}
                    </td>
                    <td className="py-3 px-4 font-bold text-teal-700">
                      {sample.order?.order_number || `#${sample.order_id}`}
                    </td>
                    <td className="py-3 px-4">
                      {sample.order?.patient ? (
                        <div>
                          <div className="font-bold text-slate-800">
                            {sample.order.patient.first_name} {sample.order.patient.last_name}
                          </div>
                          <div className="text-[10px] text-slate-400">{sample.order.patient.patient_id}</div>
                        </div>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-semibold text-slate-700">
                      {sample.sample_type}
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={sample.collection_status} />
                    </td>
                    <td className="py-3 px-4 text-slate-500 font-medium text-[11px]">
                      {sample.collected_at
                        ? new Date(sample.collected_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", day: "numeric", month: "short" })
                        : "Not collected"}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          variant="secondary"
                          size="sm"
                          className="h-7 px-2.5 text-[11px] font-bold border-slate-200"
                          onClick={() => router.push(`/samples/${sample.id}`)}
                        >
                          <Eye className="w-3 h-3 mr-1" /> View
                        </Button>

                        {canManageSamples && sample.collection_status === "Registered" && (
                          <Button
                            variant="primary"
                            size="sm"
                            isLoading={updatingId === sample.id}
                            className="h-7 px-2.5 text-[11px] font-bold bg-teal-600 hover:bg-teal-700 text-white"
                            onClick={() => handleStatusChange(sample, "Collected")}
                          >
                            Collect
                          </Button>
                        )}

                        {canManageSamples && sample.collection_status === "Collected" && (
                          <Button
                            variant="primary"
                            size="sm"
                            isLoading={updatingId === sample.id}
                            className="h-7 px-2.5 text-[11px] font-bold bg-violet-600 hover:bg-violet-700 text-white"
                            onClick={() => handleStatusChange(sample, "Processing")}
                          >
                            Process
                          </Button>
                        )}

                        {canManageSamples && ["Registered", "Collected", "Processing"].includes(sample.collection_status) && (
                          <Button
                            variant="secondary"
                            size="sm"
                            className="h-7 px-2 text-[11px] font-bold text-rose-700 hover:bg-rose-50 border-rose-200"
                            onClick={() => setRejectTarget(sample)}
                          >
                            Reject
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 bg-slate-50/50">
            <span className="text-xs font-semibold text-slate-500">
              Page {currentPage} of {totalPages} ({samplesData.total} total samples)
            </span>
            <div className="flex items-center gap-1.5">
              <Button
                variant="secondary"
                size="sm"
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage(prev => prev - 1)}
                className="h-7 px-2"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage(prev => prev + 1)}
                className="h-7 px-2"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Reject Sample Modal */}
      {rejectTarget && (
        <Modal
          isOpen={true}
          onClose={() => setRejectTarget(null)}
          title={`Reject Sample: ${rejectTarget.sample_identifier}`}
          actions={
            <>
              <Button variant="outline" onClick={() => setRejectTarget(null)}>Cancel</Button>
              <Button
                variant="primary"
                className="bg-rose-600 hover:bg-rose-700 text-white font-bold"
                isLoading={isRejecting}
                onClick={handleRejectSubmit}
              >
                Reject Specimen
              </Button>
            </>
          }
        >
          <div className="flex flex-col gap-4">
            <p className="text-xs text-slate-600 font-medium">
              Specify the laboratory reason for rejecting specimen <strong className="text-slate-900">{rejectTarget.sample_identifier}</strong>. This will set status to Rejected and trigger a recollection requirement.
            </p>
            <div>
              <label className="block text-xs font-bold text-slate-800 mb-1">Rejection Reason *</label>
              <select
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-rose-500/20"
              >
                <option value="">Select reason...</option>
                <option value="Insufficient sample volume">Insufficient sample volume</option>
                <option value="Hemolyzed sample">Hemolyzed sample</option>
                <option value="Incorrect container / tube type">Incorrect container / tube type</option>
                <option value="Improper labeling / missing identifier">Improper labeling / missing identifier</option>
                <option value="Contaminated sample">Contaminated sample</option>
                <option value="Clotted blood sample">Clotted blood sample</option>
                <option value="Other">Other (specify in notes)</option>
              </select>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
