"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import {
  Table,
  Button,
  Card,
  Modal,
  Toast,
  Badge
} from "@/components/ui/primitives";
import {
  FileText,
  RefreshCw,
  ArrowLeft,
  AlertCircle,
  CheckCircle2,
  Clock,
  RotateCw,
  Info
} from "lucide-react";

interface IntegrationDeliveryItem {
  id: number;
  organization_id: number;
  event_id: string;
  event_type: string;
  destination: string;
  status: string;
  attempts: number;
  last_attempt_at: string | null;
  response_status: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

interface IntegrationDeliveryListResponse {
  items: IntegrationDeliveryItem[];
  total: number;
  page: number;
  page_size: number;
}

export default function IntegrationLogsPage() {
  const { user } = useAuth();

  const [logs, setLogs] = useState<IntegrationDeliveryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>("");

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selected item modal
  const [selectedLog, setSelectedLog] = useState<IntegrationDeliveryItem | null>(null);
  const [isRetrying, setIsRetrying] = useState<number | null>(null);

  // Notification Toasts
  const [toastSuccess, setToastSuccess] = useState<string | null>(null);
  const [toastError, setToastError] = useState<string | null>(null);

  const fetchLogs = async () => {
    setIsLoading(true);
    setError(null);
    try {
      let url = `/integrations/logs?page=${page}&page_size=${pageSize}`;
      if (statusFilter) {
        url += `&status=${statusFilter}`;
      }
      const data = await api.get<IntegrationDeliveryListResponse>(url);
      setLogs(data.items);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.detail || "Failed to load integration delivery logs.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [page, statusFilter]);

  const handleManualRetry = async (logId: number) => {
    setIsRetrying(logId);
    setToastSuccess(null);
    setToastError(null);
    try {
      const updated = await api.post<IntegrationDeliveryItem>(`/integrations/logs/${logId}/retry`, {});
      if (updated.status === "Sent") {
        setToastSuccess(`Event ${updated.event_id} successfully re-dispatched and delivered!`);
      } else {
        setToastError(`Retry attempted. Status: ${updated.status}. Error: ${updated.error_message || "Unknown error"}`);
      }
      if (selectedLog?.id === logId) {
        setSelectedLog(updated);
      }
      fetchLogs();
    } catch (err: any) {
      setToastError(err.detail || "Manual retry failed.");
    } finally {
      setIsRetrying(null);
    }
  };

  const columns = [
    {
      header: "Timestamp",
      accessor: (row: IntegrationDeliveryItem) => (
        <span className="text-xs font-semibold text-slate-600">
          {new Date(row.created_at).toLocaleString("en-US", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit"
          })}
        </span>
      ),
    },
    {
      header: "Event ID & Type",
      accessor: (row: IntegrationDeliveryItem) => (
        <div className="flex flex-col">
          <span className="font-mono text-xs font-bold text-slate-800">{row.event_id}</span>
          <span className="text-[11px] font-semibold text-teal-600">{row.event_type}</span>
        </div>
      ),
    },
    {
      header: "Status",
      accessor: (row: IntegrationDeliveryItem) => {
        const badgeClasses: Record<string, string> = {
          Sent: "bg-emerald-50 text-emerald-700 border-emerald-200",
          Pending: "bg-amber-50 text-amber-700 border-amber-200",
          Failed: "bg-rose-50 text-rose-700 border-rose-200"
        };
        return (
          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold border ${badgeClasses[row.status] || "bg-slate-50 text-slate-700"}`}>
            {row.status}
          </span>
        );
      },
    },
    {
      header: "Attempts",
      accessor: (row: IntegrationDeliveryItem) => (
        <span className="text-xs font-bold text-slate-700">{row.attempts}</span>
      ),
    },
    {
      header: "HTTP Code",
      accessor: (row: IntegrationDeliveryItem) => (
        <span className={`text-xs font-mono font-bold ${
          row.response_status && row.response_status < 300
            ? "text-emerald-600"
            : row.response_status
            ? "text-rose-600"
            : "text-slate-400"
        }`}>
          {row.response_status ?? "N/A"}
        </span>
      ),
    },
    {
      header: "Actions",
      accessor: (row: IntegrationDeliveryItem) => (
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSelectedLog(row)}
            className="p-1 hover:bg-slate-100 rounded text-slate-500 hover:text-teal-600 transition-colors"
            title="View Details"
          >
            <Info className="w-4 h-4" />
          </button>

          {row.status === "Failed" && (
            <button
              onClick={() => handleManualRetry(row.id)}
              disabled={isRetrying === row.id}
              className="p-1 hover:bg-slate-100 rounded text-slate-500 hover:text-emerald-600 transition-colors"
              title="Manual Retry"
            >
              <RotateCw className={`w-4 h-4 ${isRetrying === row.id ? "animate-spin text-emerald-600" : ""}`} />
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-6 w-full animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <Link href="/settings/integrations" className="inline-flex items-center gap-1.5 text-xs font-bold text-teal-600 hover:text-teal-700 mb-1.5">
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Integration Settings</span>
          </Link>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">Integration Outbound Delivery Logs</h1>
          <p className="text-xs text-slate-500 font-semibold mt-0.5">
            Complete operational log of outbound webhooks, HTTP response statuses, and retry records.
          </p>
        </div>

        <Button
          variant="outline"
          onClick={fetchLogs}
          isLoading={isLoading}
          className="flex items-center gap-2 text-xs font-semibold py-2 px-3.5"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Logs</span>
        </Button>
      </div>

      {/* Notifications */}
      {toastSuccess && (
        <Toast type="success" text={toastSuccess} onClose={() => setToastSuccess(null)} />
      )}
      {toastError && (
        <Toast type="error" text={toastError} onClose={() => setToastError(null)} />
      )}

      {/* Table Card with Filter Header */}
      <Card className="p-0 border border-slate-200/80 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 bg-slate-50/40 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="text-xs font-bold text-slate-700">Filter by Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="text-xs rounded-lg border border-slate-200 bg-white text-slate-800 font-semibold px-3 py-1.5 outline-none focus:border-teal-500"
            >
              <option value="">All Statuses</option>
              <option value="Sent">Sent</option>
              <option value="Pending">Pending</option>
              <option value="Failed">Failed</option>
            </select>
          </div>

          <span className="text-xs font-semibold text-slate-500">Total Logs: {total}</span>
        </div>

        {error ? (
          <div className="p-12 text-center">
            <div className="w-12 h-12 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-slate-900">Failed to load logs</h3>
            <p className="text-xs text-slate-500 mt-2">{error}</p>
          </div>
        ) : (
          <Table
            columns={columns}
            data={logs}
            isLoading={isLoading}
            emptyMessage="No integration delivery logs found matching the filter criteria."
          />
        )}
      </Card>

      {/* Details Modal */}
      {selectedLog && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedLog(null)}
          title={`Delivery Log Details: ${selectedLog.event_id}`}
          actions={
            <>
              {selectedLog.status === "Failed" && (
                <Button
                  variant="primary"
                  onClick={() => handleManualRetry(selectedLog.id)}
                  isLoading={isRetrying === selectedLog.id}
                  className="flex items-center gap-2"
                >
                  <RotateCw className="w-4 h-4" />
                  <span>Retry Dispatch Now</span>
                </Button>
              )}
              <Button variant="outline" onClick={() => setSelectedLog(null)}>
                Close
              </Button>
            </>
          }
        >
          <div className="flex flex-col gap-4 text-xs">
            <div className="grid grid-cols-2 gap-4 p-4 rounded-xl bg-slate-50 border border-slate-100">
              <div>
                <span className="block font-semibold text-slate-400 uppercase text-[10px]">Event Type</span>
                <span className="font-bold text-slate-900 mt-0.5 block">{selectedLog.event_type}</span>
              </div>
              <div>
                <span className="block font-semibold text-slate-400 uppercase text-[10px]">Status</span>
                <span className="font-bold text-slate-900 mt-0.5 block capitalize">{selectedLog.status}</span>
              </div>
              <div>
                <span className="block font-semibold text-slate-400 uppercase text-[10px]">HTTP Response Code</span>
                <span className="font-bold text-slate-900 mt-0.5 block font-mono">{selectedLog.response_status ?? "None"}</span>
              </div>
              <div>
                <span className="block font-semibold text-slate-400 uppercase text-[10px]">Attempts Count</span>
                <span className="font-bold text-slate-900 mt-0.5 block">{selectedLog.attempts}</span>
              </div>
            </div>

            <div>
              <span className="block font-semibold text-slate-500 mb-1">Target Destination:</span>
              <span className="block font-mono bg-slate-100 p-2.5 rounded-lg text-slate-800 font-semibold break-all">
                {selectedLog.destination}
              </span>
            </div>

            {selectedLog.error_message && (
              <div>
                <span className="block font-semibold text-rose-600 mb-1">Error Details:</span>
                <div className="p-3 rounded-lg bg-rose-50 border border-rose-100 text-rose-800 font-mono text-[11px] whitespace-pre-wrap">
                  {selectedLog.error_message}
                </div>
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}
