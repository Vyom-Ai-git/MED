"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { Button, Card, Toast } from "@/components/ui/primitives";
import {
  ArrowLeft, Layers, User, Calendar, Phone, Clock, AlertTriangle, CheckCircle2, FlaskConical, FileText
} from "lucide-react";

interface PatientSummary {
  id: number;
  patient_id: string;
  first_name: string;
  last_name: string;
  phone: string;
  gender: string;
  date_of_birth: string;
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

export default function SampleDetailPage() {
  const params = useParams();
  const router = useRouter();
  const sampleId = params.id;
  const { user } = useAuth();

  const [sample, setSample] = useState<Sample | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const fetchSample = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get<Sample>(`/samples/${sampleId}`);
      setSample(data);
    } catch (err: any) {
      setError(err.detail || "Failed to load sample details.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (sampleId) fetchSample();
  }, [sampleId]);

  const handleStatusChange = async (nextStatus: string) => {
    if (!sample) return;
    setIsUpdating(true);
    try {
      await api.patch(`/samples/${sample.id}/status`, { status: nextStatus });
      setSuccessMessage(`Sample status updated to ${nextStatus}.`);
      fetchSample();
    } catch (err: any) {
      setError(err.detail || "Failed to update status.");
    } finally {
      setIsUpdating(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 w-full">
        <div className="w-8 h-8 border-4 border-teal-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-xs text-slate-500 font-semibold mt-4">Loading sample record...</span>
      </div>
    );
  }

  if (error || !sample) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center max-w-md mx-auto">
        <div className="w-16 h-16 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center mb-4">
          <AlertTriangle className="w-8 h-8" />
        </div>
        <h2 className="text-lg font-black text-slate-900">Sample Not Found</h2>
        <p className="text-xs text-slate-500 mt-2">{error || "Sample does not exist or access is restricted."}</p>
        <Button variant="secondary" onClick={() => router.push("/samples")} className="mt-6 font-bold">
          Return to Samples Tracker
        </Button>
      </div>
    );
  }

  const patient = sample.order?.patient;

  return (
    <div className="flex flex-col gap-6 w-full animate-in fade-in duration-200">
      {/* Return & Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.push("/samples")}
          className="p-2 hover:bg-slate-100 rounded-lg text-slate-500 hover:text-slate-900 border border-slate-200/80 bg-white transition-all shadow-sm"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-teal-600 font-black uppercase tracking-wider">
              Specimen File
            </span>
            {sample.priority === "Urgent" && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-black bg-rose-100 text-rose-800 border border-rose-200">
                URGENT
              </span>
            )}
          </div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight mt-0.5">
            {sample.sample_identifier}
          </h1>
        </div>
      </div>

      {successMessage && <Toast message={successMessage} type="success" onClose={() => setSuccessMessage(null)} />}
      {error && <Toast message={error} type="error" onClose={() => setError(null)} />}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left Side — Sample & Patient Info */}
        <div className="flex flex-col gap-6 lg:col-span-1">
          {/* Sample Meta Card */}
          <Card className="p-5 border border-slate-200/80 shadow-sm flex flex-col gap-4">
            <h2 className="text-xs font-black text-slate-800 border-b border-slate-100 pb-2">
              Specimen Details
            </h2>

            <div className="flex flex-col gap-3 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400 font-semibold">Sample Type:</span>
                <span className="font-bold text-slate-900">{sample.sample_type}</span>
              </div>

              <div className="flex justify-between">
                <span className="text-slate-400 font-semibold">Current Status:</span>
                <span className="font-bold text-teal-700">{sample.collection_status}</span>
              </div>

              <div className="flex justify-between">
                <span className="text-slate-400 font-semibold">Priority:</span>
                <span className="font-bold text-slate-800">{sample.priority}</span>
              </div>

              <div className="flex justify-between">
                <span className="text-slate-400 font-semibold">Barcode Value:</span>
                <span className="font-mono font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                  {sample.sample_identifier}
                </span>
              </div>
            </div>

            {/* Workflow Quick Action CTAs */}
            {(user?.role === "admin" || user?.role === "technician") && (
              <div className="mt-2 pt-3 border-t border-slate-100 flex flex-col gap-2">
                {sample.collection_status === "Registered" && (
                  <Button
                    variant="primary"
                    isLoading={isUpdating}
                    onClick={() => handleStatusChange("Collected")}
                    className="w-full bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs"
                  >
                    Mark Sample Collected
                  </Button>
                )}

                {sample.collection_status === "Collected" && (
                  <Button
                    variant="primary"
                    isLoading={isUpdating}
                    onClick={() => handleStatusChange("Processing")}
                    className="w-full bg-violet-600 hover:bg-violet-700 text-white font-bold text-xs"
                  >
                    Start Processing Specimen
                  </Button>
                )}

                {["Collected", "Processing"].includes(sample.collection_status) && (
                  <Button
                    variant="primary"
                    onClick={() => router.push(`/results/${sample.id}`)}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs"
                  >
                    Open Result Entry Form
                  </Button>
                )}
              </div>
            )}
          </Card>

          {/* Patient Card */}
          {patient && (
            <Card className="p-5 border border-slate-200/80 shadow-sm flex flex-col gap-3 text-xs">
              <h2 className="text-xs font-black text-slate-800 border-b border-slate-100 pb-2">
                Associated Patient
              </h2>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center font-bold text-slate-700">
                  {patient.first_name.charAt(0)}
                </div>
                <div>
                  <div className="font-bold text-slate-900 text-sm">{patient.first_name} {patient.last_name}</div>
                  <div className="text-[10px] text-teal-600 font-bold">{patient.patient_id}</div>
                </div>
              </div>
              <div className="mt-2 pt-2 border-t border-slate-100 flex flex-col gap-1.5 text-slate-600">
                <div><strong>Phone:</strong> {patient.phone}</div>
                <div><strong>Gender:</strong> {patient.gender}</div>
              </div>
            </Card>
          )}
        </div>

        {/* Right Side — Timeline & Rejection Warning */}
        <div className="flex flex-col gap-6 lg:col-span-2">
          {sample.recollection_required && (
            <Card className="p-5 bg-rose-50 border-rose-200 shadow-sm flex items-start gap-4">
              <AlertTriangle className="w-6 h-6 text-rose-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-black text-rose-900">Specimen Rejected — Recollection Required</h3>
                <p className="text-xs text-rose-700 mt-1 font-medium">
                  Rejection Reason: <strong className="text-rose-950">{sample.rejection_reason || "Unspecified"}</strong>
                </p>
                <p className="text-[11px] text-rose-600 mt-2 font-medium">
                  Original sample record is preserved for audit traceability. A new sample must be registered for the order.
                </p>
              </div>
            </Card>
          )}

          {/* Timeline Audit Card */}
          <Card className="p-6 border border-slate-200/80 shadow-sm flex flex-col gap-5">
            <h2 className="text-xs font-black text-slate-800 border-b border-slate-100 pb-2">
              Laboratory Specimen Timeline
            </h2>

            <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
              {/* Registered */}
              <div className="relative">
                <div className="absolute -left-6 top-1 w-3 h-3 rounded-full bg-teal-500 ring-4 ring-white" />
                <div className="text-xs font-bold text-slate-900">Specimen Registered</div>
                <div className="text-[11px] text-slate-500 font-medium mt-0.5">
                  {new Date(sample.created_at).toLocaleString("en-IN")}
                </div>
              </div>

              {/* Collected */}
              <div className="relative">
                <div className={`absolute -left-6 top-1 w-3 h-3 rounded-full ring-4 ring-white ${sample.collected_at ? "bg-teal-500" : "bg-slate-300"}`} />
                <div className="text-xs font-bold text-slate-900">Sample Collection</div>
                <div className="text-[11px] text-slate-500 font-medium mt-0.5">
                  {sample.collected_at ? new Date(sample.collected_at).toLocaleString("en-IN") : "Pending collection"}
                </div>
              </div>

              {/* Processing */}
              <div className="relative">
                <div className={`absolute -left-6 top-1 w-3 h-3 rounded-full ring-4 ring-white ${sample.processing_started_at ? "bg-teal-500" : "bg-slate-300"}`} />
                <div className="text-xs font-bold text-slate-900">Laboratory Processing Started</div>
                <div className="text-[11px] text-slate-500 font-medium mt-0.5">
                  {sample.processing_started_at ? new Date(sample.processing_started_at).toLocaleString("en-IN") : "Not started"}
                </div>
              </div>

              {/* Completed */}
              <div className="relative">
                <div className={`absolute -left-6 top-1 w-3 h-3 rounded-full ring-4 ring-white ${sample.processing_completed_at ? "bg-emerald-500" : "bg-slate-300"}`} />
                <div className="text-xs font-bold text-slate-900">Processing Completed</div>
                <div className="text-[11px] text-slate-500 font-medium mt-0.5">
                  {sample.processing_completed_at ? new Date(sample.processing_completed_at).toLocaleString("en-IN") : "Awaiting result completion"}
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
