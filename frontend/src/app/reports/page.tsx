"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { AppLayout } from "@/components/layout/AppLayout";
import { Card, Table, Badge, Button, Input, Select, Toast } from "@/components/ui/primitives";
import {
  FileText,
  Search,
  RefreshCw,
  Download,
  Eye,
  CheckCircle2,
  Clock,
  Calendar,
  FileCheck,
} from "lucide-react";

interface Report {
  id: number;
  report_number: string;
  order_id: number;
  patient_id: number;
  status: string;
  version: number;
  file_name: string;
  file_size: number;
  checksum: string;
  generated_at: string;
  generated_by_name?: string;
  order?: {
    order_number: string;
    patient?: {
      patient_id: string;
      first_name: string;
      last_name: string;
      phone: string;
    };
    tests: string[];
  };
}

interface ReportListResponse {
  items: Report[];
  total: number;
  page: number;
  page_size: number;
}

export default function ReportsRegistryPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<Report[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const loadReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const queryParams = new URLSearchParams();
      if (search) queryParams.append("q", search);
      if (statusFilter !== "all") queryParams.append("status", statusFilter);

      const data = await api.get<ReportListResponse>(`/reports?${queryParams.toString()}`);
      setItems(data.items || []);
      setTotal(data.total || 0);
    } catch (err: any) {
      setError(err.detail || err.message || "Error loading reports registry");
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const handleDownloadPDF = async (reportId: number, reportNumber: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/reports/${reportId}/download`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to download PDF report");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${reportNumber}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err: any) {
      setError(err.message || "Download failed");
    }
  };

  const columns = [
    {
      header: "Report Number",
      accessor: (row: Report) => (
        <div>
          <span className="font-mono font-bold text-teal-700 block text-xs">{row.report_number}</span>
          <span className="text-[10px] text-slate-400 font-semibold">Version {row.version}</span>
        </div>
      ),
    },
    {
      header: "Order / Date",
      accessor: (row: Report) => (
        <div>
          <span className="font-bold text-slate-900 block text-xs">{row.order?.order_number || `Order #${row.order_id}`}</span>
          <span className="text-[11px] text-slate-500 font-mono">
            {new Date(row.generated_at).toLocaleDateString()}
          </span>
        </div>
      ),
    },
    {
      header: "Patient",
      accessor: (row: Report) => (
        <div>
          {row.order?.patient ? (
            <>
              <span className="font-bold text-slate-900 block text-xs">
                {row.order.patient.first_name} {row.order.patient.last_name}
              </span>
              <span className="text-[11px] text-slate-500 font-mono">{row.order.patient.patient_id}</span>
            </>
          ) : (
            <span className="text-xs text-slate-400">Unknown Patient</span>
          )}
        </div>
      ),
    },
    {
      header: "Tests Included",
      accessor: (row: Report) => (
        <div className="flex flex-wrap gap-1">
          {row.order?.tests && row.order.tests.length > 0 ? (
            row.order.tests.map((t, idx) => (
              <span key={idx} className="bg-slate-100 text-slate-700 text-[10px] font-bold px-2 py-0.5 rounded">
                {t}
              </span>
            ))
          ) : (
            <span className="text-xs text-slate-400">Diagnostic Tests</span>
          )}
        </div>
      ),
    },
    {
      header: "Status",
      accessor: (row: Report) => (
        <Badge status={row.status} />
      ),
    },
    {
      header: "Actions",
      accessor: (row: Report) => (
        <div className="flex items-center gap-2">
          <Link href={`/reports/${row.id}`}>
            <Button variant="outline" size="sm" className="font-bold text-xs">
              <Eye className="w-3.5 h-3.5 mr-1" /> View
            </Button>
          </Link>
          <Button
            variant="primary"
            size="sm"
            onClick={() => handleDownloadPDF(row.id, row.report_number)}
            className="bg-teal-600 hover:bg-teal-700 font-bold text-xs shadow-xs"
          >
            <Download className="w-3.5 h-3.5 mr-1" /> PDF
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2.5">
              <FileCheck className="w-7 h-7 text-teal-600" />
              Reports Registry
            </h1>
            <p className="text-xs font-semibold text-slate-500 mt-1">
              Official diagnostic reports generated from verified laboratory results
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={loadReports} className="self-start sm:self-auto">
            <RefreshCw className="w-3.5 h-3.5 mr-1.5" /> Refresh Registry
          </Button>
        </div>

        {error && <Toast message={error} type="error" onClose={() => setError(null)} />}

        {/* Filters */}
        <Card className="p-4 border border-slate-200/80 bg-slate-50/40">
          <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
            <div className="flex-1 w-full md:w-auto">
              <Input
                placeholder="Search by report number, order number, or patient..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                icon={<Search className="w-4 h-4" />}
              />
            </div>
            <div className="w-44">
              <Select
                options={[
                  { value: "all", label: "All Statuses" },
                  { value: "Available", label: "Available" },
                  { value: "Generated", label: "Generated" },
                  { value: "Superseded", label: "Superseded" },
                ]}
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              />
            </div>
          </div>
        </Card>

        {/* Table */}
        <Table columns={columns} data={items} isLoading={loading} emptyMessage="No diagnostic reports generated yet." />
      </div>
  );
}
