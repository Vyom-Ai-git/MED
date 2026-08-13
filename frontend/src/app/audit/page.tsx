"use client";

import { useState, useEffect } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { api, ApiError } from "@/lib/api";

import {
  History,
  Search,
  Filter,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
  CheckCircle,
  XCircle,
  FileText,
  User as UserIcon,
  X,
  ArrowRight,
} from "lucide-react";

interface AuditLog {
  id: number;
  organization_id: number;
  branch_id?: number;
  user_id?: number;
  user_name?: string;
  user_email?: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  event_type?: string;
  description?: string;
  old_values?: Record<string, any>;
  new_values?: Record<string, any>;
  metadata_json?: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
  success: boolean;
  failure_reason?: string;
  created_at: string;
}

interface AuditLogListResponse {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
}

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [entityType, setEntityType] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Selected Log Drawer
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      params.append("page", page.toString());
      params.append("page_size", pageSize.toString());
      if (searchTerm.trim()) params.append("q", searchTerm.trim());
      if (entityType) params.append("entity_type", entityType);
      if (actionFilter) params.append("action", actionFilter);

      const res = await api.get<AuditLogListResponse>(`/audit?${params.toString()}`);
      setLogs(res.items);
      setTotal(res.total);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Failed to load audit logs");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [page, entityType, actionFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchLogs();
  };

  const formatTimestamp = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  const getActionBadgeClass = (action: string) => {
    if (action.includes("APPROVED") || action.includes("SUCCESS") || action.includes("CREATED") || action.includes("GENERATED")) {
      return "bg-emerald-50 text-emerald-700 border-emerald-200/60";
    }
    if (action.includes("FAILURE") || action.includes("REJECTED") || action.includes("DEACTIVATED")) {
      return "bg-rose-50 text-rose-700 border-rose-200/60";
    }
    if (action.includes("RETURNED") || action.includes("UPDATED")) {
      return "bg-amber-50 text-amber-700 border-amber-200/60";
    }
    return "bg-slate-100 text-slate-700 border-slate-200/60";
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-6">

        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <History className="w-6 h-6 text-teal-600" />
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Audit Trail</h1>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              System activity and laboratory traceability registry
            </p>
          </div>
          <button
            onClick={fetchLogs}
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-white border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-sm transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-teal-600" : ""}`} />
            Refresh Log
          </button>
        </div>

        {/* Filter Bar */}
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm space-y-3">
          <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row gap-3">
            <div className="flex-1 relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                placeholder="Search by Entity ID, Action, Description or User..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
              />
            </div>
            <div className="flex gap-2">
              <select
                value={entityType}
                onChange={(e) => {
                  setEntityType(e.target.value);
                  setPage(1);
                }}
                className="px-3 py-2 text-xs border border-slate-200 rounded-lg bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
              >
                <option value="">All Entity Types</option>
                <option value="PATIENT">PATIENT</option>
                <option value="ORDER">ORDER</option>
                <option value="SAMPLE">SAMPLE</option>
                <option value="RESULT">RESULT</option>
                <option value="VERIFICATION">VERIFICATION</option>
                <option value="REPORT">REPORT</option>
                <option value="USER">USER</option>
                <option value="AUTHENTICATION">AUTHENTICATION</option>
              </select>

              <select
                value={actionFilter}
                onChange={(e) => {
                  setActionFilter(e.target.value);
                  setPage(1);
                }}
                className="px-3 py-2 text-xs border border-slate-200 rounded-lg bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
              >
                <option value="">All Actions</option>
                <option value="LOGIN_SUCCESS">LOGIN_SUCCESS</option>
                <option value="LOGIN_FAILURE">LOGIN_FAILURE</option>
                <option value="PATIENT_CREATED">PATIENT_CREATED</option>
                <option value="ORDER_CREATED">ORDER_CREATED</option>

                <option value="SAMPLE_CREATED">SAMPLE_CREATED</option>
                <option value="SAMPLE_COLLECTED">SAMPLE_COLLECTED</option>
                <option value="SAMPLE_REJECTED">SAMPLE_REJECTED</option>
                <option value="RESULT_SUBMITTED">RESULT_SUBMITTED</option>
                <option value="RESULT_APPROVED">RESULT_APPROVED</option>
                <option value="RESULT_RETURNED_FOR_CORRECTION">RESULT_RETURNED_FOR_CORRECTION</option>
                <option value="REPORT_GENERATED">REPORT_GENERATED</option>
                <option value="REPORT_DOWNLOADED">REPORT_DOWNLOADED</option>
                <option value="USER_CREATED">USER_CREATED</option>
              </select>

              <button
                type="submit"
                className="px-4 py-2 bg-teal-600 text-white rounded-lg text-xs font-semibold hover:bg-teal-700 transition"
              >
                Search
              </button>
            </div>
          </form>
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-rose-50 border border-rose-200 text-rose-800 p-4 rounded-xl text-xs flex items-center gap-3">
            <ShieldAlert className="w-5 h-5 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Logs Table */}
        <div className="bg-white border border-slate-200/80 rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 border-b border-slate-200/80 uppercase font-extrabold text-[10px] text-slate-500 tracking-wider">
                <tr>
                  <th className="px-5 py-3.5">Timestamp</th>
                  <th className="px-5 py-3.5">User</th>
                  <th className="px-5 py-3.5">Action</th>
                  <th className="px-5 py-3.5">Entity</th>
                  <th className="px-5 py-3.5">Entity ID</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {loading && logs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-5 py-12 text-center text-slate-400">
                      <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-teal-600" />
                      Loading audit logs...
                    </td>
                  </tr>
                ) : logs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-5 py-12 text-center text-slate-400">
                      No audit records found.
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-50/70 transition">
                      <td className="px-5 py-3.5 whitespace-nowrap text-slate-900 font-mono text-[11px]">
                        {formatTimestamp(log.created_at)}
                      </td>
                      <td className="px-5 py-3.5 whitespace-nowrap">
                        {log.user_name ? (
                          <div>
                            <span className="font-semibold text-slate-800 block">{log.user_name}</span>
                            <span className="text-[10px] text-slate-400 block">{log.user_email}</span>
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">System / Unauthenticated</span>
                        )}
                      </td>
                      <td className="px-5 py-3.5 whitespace-nowrap">
                        <span
                          className={`inline-flex px-2 py-0.5 rounded border text-[10px] font-bold tracking-tight uppercase ${getActionBadgeClass(
                            log.action
                          )}`}
                        >
                          {log.action}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 whitespace-nowrap font-semibold text-slate-700">
                        {log.entity_type}
                      </td>
                      <td className="px-5 py-3.5 whitespace-nowrap font-mono text-slate-600">
                        {log.entity_id || "—"}
                      </td>
                      <td className="px-5 py-3.5 whitespace-nowrap">
                        {log.success ? (
                          <span className="inline-flex items-center gap-1 text-emerald-700 font-bold text-[11px]">
                            <CheckCircle className="w-3.5 h-3.5 text-emerald-600" /> Success
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-rose-700 font-bold text-[11px]">
                            <XCircle className="w-3.5 h-3.5 text-rose-600" /> Failed
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3.5 whitespace-nowrap text-right">
                        <button
                          onClick={() => setSelectedLog(log)}
                          className="px-2.5 py-1 text-xs font-semibold text-teal-700 hover:text-teal-900 hover:bg-teal-50 rounded border border-teal-200 transition"
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div className="bg-slate-50 px-5 py-3 border-t border-slate-200/80 flex items-center justify-between">
            <span className="text-xs text-slate-500 font-medium">
              Showing {logs.length > 0 ? (page - 1) * pageSize + 1 : 0} to{" "}
              {Math.min(page * pageSize, total)} of {total} audit records
            </span>

            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1 || loading}
                onClick={() => setPage((p) => Math.max(p - 1, 1))}
                className="p-1.5 rounded border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 transition"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>

              <span className="text-xs font-bold text-slate-700 px-2">
                Page {page} of {totalPages}
              </span>

              <button
                disabled={page >= totalPages || loading}
                onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                className="p-1.5 rounded border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 transition"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
          </div>
        </div>
      </div>

      {/* Audit Detail Drawer */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex justify-end">
          <div className="w-full max-w-2xl bg-white h-full shadow-2xl flex flex-col border-l border-slate-200">
            {/* Drawer Header */}
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div>
                <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block">
                  Audit Entry Details #{selectedLog.id}
                </span>
                <h2 className="text-lg font-bold text-slate-900 mt-0.5">{selectedLog.action}</h2>
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Drawer Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Metadata Grid */}
              <div className="grid grid-cols-2 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200/60 text-xs">
                <div>
                  <span className="text-slate-400 block font-semibold text-[10px] uppercase">Timestamp</span>
                  <span className="font-mono text-slate-800 font-bold">
                    {formatTimestamp(selectedLog.created_at)}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block font-semibold text-[10px] uppercase">Status</span>
                  <span className="font-bold">
                    {selectedLog.success ? (
                      <span className="text-emerald-700">Success</span>
                    ) : (
                      <span className="text-rose-700">Failed: {selectedLog.failure_reason}</span>
                    )}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block font-semibold text-[10px] uppercase">User</span>
                  <span className="font-semibold text-slate-800">
                    {selectedLog.user_name || "System / Unauthenticated"}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block font-semibold text-[10px] uppercase">Entity</span>
                  <span className="font-mono text-slate-800">
                    {selectedLog.entity_type} ({selectedLog.entity_id || "N/A"})
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block font-semibold text-[10px] uppercase">Client IP</span>
                  <span className="font-mono text-slate-700">{selectedLog.ip_address || "N/A"}</span>
                </div>
                <div>
                  <span className="text-slate-400 block font-semibold text-[10px] uppercase">Event Type</span>
                  <span className="font-mono text-slate-700">{selectedLog.event_type || "N/A"}</span>
                </div>
              </div>

              {/* Description */}
              {selectedLog.description && (
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                    Description
                  </h3>
                  <p className="text-xs text-slate-700 bg-slate-50 p-3 rounded-lg border border-slate-200/60">
                    {selectedLog.description}
                  </p>
                </div>
              )}

              {/* State Change Comparison (Old vs New Values) */}
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                  State Delta Snapshot
                </h3>
                {selectedLog.old_values || selectedLog.new_values ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Old Values */}
                    <div className="bg-rose-50/50 border border-rose-200/60 rounded-xl p-3.5">
                      <span className="text-[11px] font-bold text-rose-800 block mb-2">Previous State</span>
                      {selectedLog.old_values ? (
                        <pre className="text-[11px] font-mono text-rose-950 overflow-x-auto whitespace-pre-wrap bg-white/80 p-2.5 rounded border border-rose-200/40">
                          {JSON.stringify(selectedLog.old_values, null, 2)}
                        </pre>
                      ) : (
                        <span className="text-xs text-slate-400 italic">No previous state recorded</span>
                      )}
                    </div>

                    {/* New Values */}
                    <div className="bg-emerald-50/50 border border-emerald-200/60 rounded-xl p-3.5">
                      <span className="text-[11px] font-bold text-emerald-800 block mb-2">New State</span>
                      {selectedLog.new_values ? (
                        <pre className="text-[11px] font-mono text-emerald-950 overflow-x-auto whitespace-pre-wrap bg-white/80 p-2.5 rounded border border-emerald-200/40">
                          {JSON.stringify(selectedLog.new_values, null, 2)}
                        </pre>
                      ) : (
                        <span className="text-xs text-slate-400 italic">No new state recorded</span>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="bg-slate-50 border border-slate-200/60 p-4 rounded-xl text-xs text-slate-400 italic text-center">
                    No state change recorded.
                  </div>
                )}
              </div>

              {/* Metadata JSON */}
              {selectedLog.metadata_json && Object.keys(selectedLog.metadata_json).length > 0 && (
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                    Metadata JSON
                  </h3>
                  <pre className="text-[11px] font-mono bg-slate-900 text-slate-100 p-3.5 rounded-xl overflow-x-auto">
                    {JSON.stringify(selectedLog.metadata_json, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
