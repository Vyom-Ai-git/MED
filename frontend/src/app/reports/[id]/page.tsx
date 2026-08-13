"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { AppLayout } from "@/components/layout/AppLayout";
import { Card, Badge, Button, Toast } from "@/components/ui/primitives";
import {
  FileText,
  ArrowLeft,
  Download,
  CheckCircle2,
  Calendar,
  User,
  FolderOpen,
  FileCheck,
  ShieldCheck,
  HardDrive,
  RefreshCw,
} from "lucide-react";

interface ReportDetail {
  id: number;
  report_number: string;
  order_id: number;
  patient_id: number;
  status: string;
  version: number;
  file_name: string;
  file_size: number;
  mime_type: string;
  checksum: string;
  generated_at: string;
  generated_by_name?: string;
  order?: {
    order_number: string;
    created_at: string;
    tests: string[];
    patient?: {
      patient_id: string;
      first_name: string;
      last_name: string;
      phone: string;
      gender: string;
    };
  };
  patient?: {
    patient_id: string;
    first_name: string;
    last_name: string;
    phone: string;
    gender: string;
  };
}

export default function ReportDetailPage() {
  const params = useParams();
  const router = useRouter();
  const reportId = params.id;
  const { user } = useAuth();

  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<ReportDetail>(`/reports/${reportId}`);
      setReport(data);
    } catch (err: any) {
      setError(err.detail || err.message || "Failed to load report detail");
    } finally {
      setLoading(false);
    }
  }, [reportId]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  const handleDownloadPDF = async () => {
    if (!report) return;
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/reports/${report.id}/download`, {
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
      a.download = `${report.report_number}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err: any) {
      setError(err.message || "Download failed");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <RefreshCw className="w-8 h-8 text-teal-600 animate-spin" />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="p-6">
        <Toast message={error || "Report not found"} type="error" onClose={() => setError(null)} />
        <Link href="/reports">
          <Button variant="outline" className="mt-4">
            <ArrowLeft className="w-4 h-4 mr-2" /> Return to Reports Registry
          </Button>
        </Link>
      </div>
    );
  }

  const patient = report.patient || report.order?.patient;

  return (
    <div className="flex flex-col gap-6 max-w-5xl mx-auto">
        {/* Header Navigation */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link href="/reports">
              <button className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-all">
                <ArrowLeft className="w-4 h-4 text-slate-600" />
              </button>
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-black text-slate-900 tracking-tight">Diagnostic Report</h1>
                <span className="font-mono text-sm font-extrabold text-teal-700 bg-teal-50 px-2.5 py-0.5 rounded border border-teal-200">
                  {report.report_number}
                </span>
              </div>
              <p className="text-xs font-semibold text-slate-500 mt-0.5">
                Official clinical document generated from verified laboratory results
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Badge status={report.status} className="px-3 py-1 text-xs" />
            <Button
              variant="primary"
              onClick={handleDownloadPDF}
              className="bg-teal-600 hover:bg-teal-700 font-bold px-5 shadow-sm"
            >
              <Download className="w-4 h-4 mr-2" /> Download PDF Report
            </Button>
          </div>
        </div>

        {error && <Toast message={error} type="error" onClose={() => setError(null)} />}

        {/* Report Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card title="Patient Profile" className="border-slate-200/80">
            {patient ? (
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="font-black text-slate-900 text-sm">
                    {patient.first_name} {patient.last_name}
                  </span>
                  <span className="font-mono text-[11px] font-bold text-teal-700 bg-teal-50 px-2 py-0.5 rounded">
                    {patient.patient_id}
                  </span>
                </div>
                <div className="text-xs text-slate-600 font-semibold flex items-center justify-between">
                  <span>Gender:</span>
                  <span className="text-slate-900 font-bold">{patient.gender}</span>
                </div>
                <div className="text-xs text-slate-600 font-semibold flex items-center justify-between">
                  <span>Phone:</span>
                  <span className="text-slate-900 font-bold font-mono">{patient.phone}</span>
                </div>
              </div>
            ) : (
              <span className="text-xs text-slate-400">No patient attached</span>
            )}
          </Card>

          <Card title="Order Summary" className="border-slate-200/80">
            <div className="flex flex-col gap-2">
              <div className="text-xs text-slate-600 font-semibold flex items-center justify-between">
                <span>Order Number:</span>
                <span className="font-bold text-slate-900">{report.order?.order_number || `Order #${report.order_id}`}</span>
              </div>
              <div className="text-xs text-slate-600 font-semibold">
                <span>Diagnostic Tests:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {report.order?.tests?.map((t, idx) => (
                    <span key={idx} className="bg-slate-100 text-slate-800 text-[10px] font-bold px-2 py-0.5 rounded">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </Card>

          <Card title="Artifact Metadata" className="border-slate-200/80">
            <div className="flex flex-col gap-2 text-xs">
              <div className="flex items-center justify-between text-slate-600 font-semibold">
                <span>Generated Date:</span>
                <span className="font-mono font-bold text-slate-900">{new Date(report.generated_at).toLocaleString()}</span>
              </div>
              <div className="flex items-center justify-between text-slate-600 font-semibold">
                <span>Generated By:</span>
                <span className="font-bold text-slate-900">{report.generated_by_name || "System Reviewer"}</span>
              </div>
              <div className="flex items-center justify-between text-slate-600 font-semibold">
                <span>Version & Size:</span>
                <span className="font-mono font-bold text-slate-900">v{report.version} ({(report.file_size / 1024).toFixed(1)} KB)</span>
              </div>
              <div className="flex items-center justify-between text-slate-600 font-semibold truncate">
                <span>SHA-256 Checksum:</span>
                <span className="font-mono text-[10px] text-teal-700 truncate max-w-[120px]">{report.checksum}</span>
              </div>
            </div>
          </Card>
        </div>

        {/* Embedded PDF Viewer Component */}
        <Card title="Report Document Preview" subtitle="Authenticated PDF artifact rendered directly from secure backend storage">
          <div className="w-full h-[600px] border border-slate-200 rounded-lg overflow-hidden bg-slate-100 flex flex-col">
            <iframe
              src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/reports/${report.id}/download`}
              className="w-full h-full border-none"
              title={`Report PDF ${report.report_number}`}
            />
          </div>
        </Card>
    </div>
  );
}
