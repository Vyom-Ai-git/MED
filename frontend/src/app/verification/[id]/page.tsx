"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { AppLayout } from "@/components/layout/AppLayout";
import { Card, Badge, Button, Modal, Toast } from "@/components/ui/primitives";
import {
  CheckSquare,
  ArrowLeft,
  UserCheck,
  AlertTriangle,
  RotateCcw,
  CheckCircle2,
  Clock,
  FlaskConical,
  User,
  Calendar,
  FileText,
  ShieldAlert,
  History,
} from "lucide-react";

interface VerificationDetail {
  sample: {
    id: number;
    sample_identifier: string;
    sample_type: string;
    collection_status: string;
    priority: string;
    collected_at?: string;
    processing_started_at?: string;
    processing_completed_at?: string;
    order?: {
      id: number;
      order_number: string;
      created_at: string;
      patient?: {
        patient_id: string;
        first_name: string;
        last_name: string;
        phone: string;
        gender: string;
        date_of_birth: string;
      };
      tests: string[];
    };
  };
  results: {
    id: number;
    parameter_id: number;
    parameter_name?: string;
    parameter_code?: string;
    data_type?: string;
    raw_value?: string;
    numeric_value?: number;
    unit?: string;
    reference_low?: number;
    reference_high?: number;
    abnormal_flag: string;
    critical_flag: boolean;
    status: string;
    entered_by?: number;
    entered_at?: string;
    verified_by?: number;
    verified_at?: string;
    correction_reason?: string;
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

export default function VerificationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const sampleId = params.id;
  const { user } = useAuth();

  const [detail, setDetail] = useState<VerificationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Modals & Action States
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [showReturnModal, setShowReturnModal] = useState(false);
  const [correctionReason, setCorrectionReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const isReviewerOrAdmin = user?.role === "admin" || user?.role === "reviewer";

  const loadDetail = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<VerificationDetail>(`/verification/${sampleId}`);
      setDetail(data);
    } catch (err: any) {
      setError(err.detail || err.message || "Failed to load verification record");
    } finally {
      setLoading(false);
    }
  }, [sampleId]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  const handleApprove = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await api.post(`/verification/${sampleId}/approve`, { reason: "Approved by authorized reviewer" });
      setSuccess("Laboratory results successfully verified and approved!");
      setShowApproveModal(false);
      loadDetail();
    } catch (err: any) {
      setError(err.detail || err.message || "Approval failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReturn = async () => {
    if (!correctionReason.trim()) {
      setError("Correction reason is required before returning results.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.post(`/verification/${sampleId}/return`, { reason: correctionReason.trim() });
      setSuccess("Results returned to technician for correction.");
      setShowReturnModal(false);
      setCorrectionReason("");
      loadDetail();
    } catch (err: any) {
      setError(err.detail || err.message || "Return for correction failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="flex justify-center items-center h-64">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 border-2 border-teal-600 border-t-transparent rounded-full animate-spin"></div>
            <span className="text-sm font-semibold text-slate-600">Loading verification details...</span>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (!detail) {
    return (
      <AppLayout>
        <div className="p-6">
          <Toast message={error || "Verification record not found"} type="error" onClose={() => setError(null)} />
          <Link href="/verification">
            <Button variant="outline" className="mt-4">
              <ArrowLeft className="w-4 h-4 mr-2" /> Return to Queue
            </Button>
          </Link>
        </div>
      </AppLayout>
    );
  }

  const { sample, results, verifications, has_critical, has_abnormal, status_summary } = detail;
  const patient = sample.order?.patient;
  const isVerified = results.length > 0 && results.every((r) => r.status === "Verified");
  const isCorrection = status_summary === "Correction Required";

  return (
    <div className="flex flex-col gap-6 max-w-5xl mx-auto">
        {/* Header Navigation */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link href="/verification">
              <button className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-all">
                <ArrowLeft className="w-4 h-4 text-slate-600" />
              </button>
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-black text-slate-900 tracking-tight">Review Results</h1>
                <span className="font-mono text-sm font-extrabold text-teal-700 bg-teal-50 px-2.5 py-0.5 rounded border border-teal-200">
                  {sample.sample_identifier}
                </span>
              </div>
              <p className="text-xs font-semibold text-slate-500 mt-0.5">
                Specimen inspection and clinical verification console
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {has_critical && (
              <span className="inline-flex items-center gap-1.5 bg-rose-600 text-white font-black text-xs uppercase px-3 py-1 rounded shadow-sm animate-pulse">
                <AlertTriangle className="w-4 h-4" /> CRITICAL RESULT
              </span>
            )}
            <Badge status={status_summary} className="px-3 py-1 text-xs" />
          </div>
        </div>

        {error && <Toast message={error} type="error" onClose={() => setError(null)} />}
        {success && <Toast message={success} type="success" onClose={() => setSuccess(null)} />}

        {/* Correction Warning Banner */}
        {isCorrection && (
          <Card className="border-amber-300 bg-amber-50/50 p-4">
            <div className="flex items-start gap-3">
              <RotateCcw className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-bold text-amber-900 uppercase tracking-wide">Returned for Correction</h4>
                <p className="text-xs text-amber-800 font-semibold mt-1">
                  Reason: <span className="font-black underline">{results[0]?.correction_reason || "Correction requested"}</span>
                </p>
                {user?.role === "technician" && (
                  <Link href={`/results/${sample.id}`}>
                    <Button variant="outline" size="sm" className="mt-3 bg-white border-amber-300 text-amber-900 font-bold">
                      Re-open & Edit Results
                    </Button>
                  </Link>
                )}
              </div>
            </div>
          </Card>
        )}

        {/* Verified Banner */}
        {isVerified && (
          <Card className="border-emerald-300 bg-emerald-50/50 p-4">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-700 shrink-0" />
              <div>
                <h4 className="text-sm font-bold text-emerald-900 uppercase tracking-wide">Results Verified & Authorized</h4>
                <p className="text-xs text-emerald-800 font-semibold mt-0.5">
                  Verified at: {results[0]?.verified_at ? new Date(results[0].verified_at).toLocaleString() : "Authorized"}
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* Metadata Section: Patient, Order, Specimen */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Patient Card */}
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
                  <span>Gender / Age:</span>
                  <span className="text-slate-900 font-bold">{patient.gender}</span>
                </div>
                <div className="text-xs text-slate-600 font-semibold flex items-center justify-between">
                  <span>Phone:</span>
                  <span className="text-slate-900 font-bold font-mono">{patient.phone}</span>
                </div>
              </div>
            ) : (
              <span className="text-xs text-slate-400">No patient record attached</span>
            )}
          </Card>

          {/* Specimen Card */}
          <Card title="Specimen Summary" className="border-slate-200/80">
            <div className="flex flex-col gap-2">
              <div className="text-xs text-slate-600 font-semibold flex items-center justify-between">
                <span>Sample ID:</span>
                <span className="font-mono font-bold text-teal-700">{sample.sample_identifier}</span>
              </div>
              <div className="text-xs text-slate-600 font-semibold flex items-center justify-between">
                <span>Sample Type:</span>
                <span className="text-slate-900 font-bold">{sample.sample_type}</span>
              </div>
              <div className="text-xs text-slate-600 font-semibold flex items-center justify-between">
                <span>Priority:</span>
                <span className={`font-extrabold uppercase ${sample.priority === "Urgent" ? "text-rose-600" : "text-slate-700"}`}>
                  {sample.priority}
                </span>
              </div>
            </div>
          </Card>

          {/* Order Card */}
          <Card title="Order Info" className="border-slate-200/80">
            <div className="flex flex-col gap-2">
              <div className="text-xs text-slate-600 font-semibold flex items-center justify-between">
                <span>Order #:</span>
                <span className="font-bold text-slate-900">{sample.order?.order_number || "N/A"}</span>
              </div>
              <div className="text-xs text-slate-600 font-semibold">
                <span>Ordered Tests:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {sample.order?.tests?.map((t, idx) => (
                    <span key={idx} className="bg-slate-100 text-slate-800 text-[10px] font-bold px-2 py-0.5 rounded">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* Results Parameters Table */}
        <Card title="Laboratory Test Results" subtitle="Raw values, snapshotted reference limits, and calculated flags">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-extrabold text-slate-500 uppercase tracking-wider">
                  <th className="px-4 py-3">Parameter Name</th>
                  <th className="px-4 py-3">Result Value</th>
                  <th className="px-4 py-3">Unit</th>
                  <th className="px-4 py-3">Reference Range</th>
                  <th className="px-4 py-3">Flag</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {results.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/50">
                    <td className="px-4 py-3 font-bold text-slate-900">
                      {r.parameter_name} {r.parameter_code ? `(${r.parameter_code})` : ""}
                    </td>
                    <td className="px-4 py-3 font-mono font-black text-slate-900 text-sm">
                      {r.raw_value || "—"}
                    </td>
                    <td className="px-4 py-3 text-slate-500 font-medium">{r.unit || "—"}</td>
                    <td className="px-4 py-3 text-slate-600 font-mono">
                      {r.reference_low !== undefined && r.reference_high !== undefined
                        ? `${r.reference_low} – ${r.reference_high}`
                        : "N/A"}
                    </td>
                    <td className="px-4 py-3">
                      {r.critical_flag ? (
                        <span className="inline-flex items-center gap-1 bg-rose-600 text-white font-black text-[10px] uppercase px-2 py-0.5 rounded animate-pulse">
                          <AlertTriangle className="w-3 h-3" /> CRITICAL
                        </span>
                      ) : r.abnormal_flag === "LOW" ? (
                        <span className="bg-amber-100 text-amber-800 font-extrabold text-[10px] uppercase px-2 py-0.5 rounded border border-amber-300">
                          LOW
                        </span>
                      ) : r.abnormal_flag === "HIGH" ? (
                        <span className="bg-amber-100 text-amber-800 font-extrabold text-[10px] uppercase px-2 py-0.5 rounded border border-amber-300">
                          HIGH
                        </span>
                      ) : (
                        <span className="bg-emerald-50 text-emerald-700 font-bold text-[10px] uppercase px-2 py-0.5 rounded border border-emerald-200">
                          NORMAL
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Badge status={r.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Verification Audit Trail */}
        {verifications.length > 0 && (
          <Card title="Verification Audit History" subtitle="Immutable record of reviewer actions and return reasons">
            <div className="flex flex-col gap-3">
              {verifications.map((v) => (
                <div key={v.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200/80 flex flex-col gap-1 text-xs">
                  <div className="flex items-center justify-between font-bold">
                    <span className={`uppercase ${v.action === "Approved" ? "text-emerald-700" : "text-amber-800"}`}>
                      {v.action}
                    </span>
                    <span className="text-slate-500 text-[11px] font-mono">
                      {new Date(v.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="text-slate-700 font-medium">
                    By: <span className="font-bold">{v.performed_by_name || `User #${v.id}`}</span>
                  </div>
                  {v.reason && (
                    <div className="text-slate-600 bg-white p-2 rounded border border-slate-200/60 mt-1 font-mono text-[11px]">
                      "{v.reason}"
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Reviewer Action Bar */}
        {isReviewerOrAdmin && !isVerified && (
          <div className="sticky bottom-6 bg-white p-4 rounded-xl border border-slate-200 shadow-xl flex items-center justify-between gap-4">
            <div className="text-xs font-bold text-slate-600">
              Authorized Reviewer Action Console
            </div>
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                onClick={() => setShowReturnModal(true)}
                className="border-amber-300 text-amber-900 hover:bg-amber-50 font-bold"
              >
                <RotateCcw className="w-4 h-4 mr-1.5" /> Return for Correction
              </Button>
              <Button
                variant="primary"
                onClick={() => setShowApproveModal(true)}
                className="bg-teal-600 hover:bg-teal-700 font-bold px-6 shadow-md"
              >
                <CheckCircle2 className="w-4 h-4 mr-1.5" /> Approve Results
              </Button>
            </div>
          </div>
        )}

        {/* Approve Modal */}
        <Modal
          isOpen={showApproveModal}
          onClose={() => setShowApproveModal(false)}
          title="Approve Laboratory Results"
          actions={
            <>
              <Button variant="outline" onClick={() => setShowApproveModal(false)} disabled={submitting}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleApprove} isLoading={submitting} className="bg-teal-600 hover:bg-teal-700">
                Approve & Authorize
              </Button>
            </>
          }
        >
          <div className="flex flex-col gap-3 text-sm">
            <p className="font-semibold text-slate-700">
              You are about to authorize results for specimen{" "}
              <span className="font-mono font-bold text-teal-700">{sample.sample_identifier}</span>.
            </p>
            <p className="text-xs text-slate-500">
              Upon approval, these results will be locked against technician edits and marked eligible for final report publishing.
            </p>
          </div>
        </Modal>

        {/* Return for Correction Modal */}
        <Modal
          isOpen={showReturnModal}
          onClose={() => setShowReturnModal(false)}
          title="Return Results for Correction"
          actions={
            <>
              <Button variant="outline" onClick={() => setShowReturnModal(false)} disabled={submitting}>
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={handleReturn}
                isLoading={submitting}
                disabled={!correctionReason.trim()}
              >
                Return for Correction
              </Button>
            </>
          }
        >
          <div className="flex flex-col gap-3 text-sm">
            <p className="font-semibold text-slate-700">
              Provide a required explanation for returning specimen{" "}
              <span className="font-mono font-bold text-teal-700">{sample.sample_identifier}</span> to the technician.
            </p>
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Correction Reason <span className="text-rose-600">*</span>
              </label>
              <textarea
                className="w-full text-xs p-3 rounded-lg border border-slate-200 outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500"
                rows={3}
                placeholder="e.g. Platelet count appears improbable relative to previous baseline, please re-check dilution..."
                value={correctionReason}
                onChange={(e) => setCorrectionReason(e.target.value)}
              />
            </div>
          </div>
        </Modal>
      </div>
  );
}
