"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { Button, Card, Badge, Toast } from "@/components/ui/primitives";
import {
  Inbox, Search, Filter, RefreshCw, Eye, FlaskConical, Clock, AlertTriangle, Layers
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
  recollection_required: boolean;
  order?: OrderSummary;
}

interface SampleListResponse {
  items: Sample[];
  total: number;
}

export default function TechnicianWorklistPage() {
  const router = useRouter();
  const { user } = useAuth();

  const [samples, setSamples] = useState<Sample[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"all" | "urgent" | "pending_collection" | "processing">("all");

  const fetchWorklist = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get<SampleListResponse>("/samples?page_size=50");
      setSamples(data.items || []);
    } catch (err: any) {
      setError(err.detail || "Failed to load technician worklist.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWorklist();
  }, [fetchWorklist]);

  // Counts
  const urgentCount = samples.filter(s => s.priority === "Urgent").length;
  const pendingCollCount = samples.filter(s => s.collection_status === "Registered").length;
  const processingCount = samples.filter(s => s.collection_status === "Processing").length;
  const collectedCount = samples.filter(s => s.collection_status === "Collected").length;

  const filteredSamples = samples.filter(s => {
    if (activeTab === "urgent") return s.priority === "Urgent";
    if (activeTab === "pending_collection") return s.collection_status === "Registered";
    if (activeTab === "processing") return ["Collected", "Processing"].includes(s.collection_status);
    return true;
  });

  return (
    <div className="flex flex-col gap-6 w-full animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-teal-600 font-black uppercase tracking-wider">
              Laboratory Processing Console
            </span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight mt-0.5">
            Technician Worklist
          </h1>
          <p className="text-xs font-semibold text-slate-500 mt-1">
            Primary workspace for specimen collection, laboratory processing, and parameter result entry.
          </p>
        </div>

        <Button
          variant="secondary"
          onClick={fetchWorklist}
          className="border-slate-200/80 bg-white hover:bg-slate-50 font-bold text-xs shadow-sm h-9"
        >
          <RefreshCw className="w-3.5 h-3.5 mr-1.5" /> Refresh Worklist
        </Button>
      </div>

      {error && <Toast message={error} type="error" onClose={() => setError(null)} />}

      {/* Metric Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div onClick={() => setActiveTab("all")} className="cursor-pointer">
          <Card className={`p-4 border transition-all ${activeTab === "all" ? "border-teal-500 bg-teal-50/20 shadow-md" : "border-slate-200/80 hover:border-slate-300"}`}>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-500 uppercase">Total Samples</span>
              <Layers className="w-4 h-4 text-teal-600" />
            </div>
            <div className="text-2xl font-black text-slate-900 mt-2">{samples.length}</div>
          </Card>
        </div>

        <div onClick={() => setActiveTab("urgent")} className="cursor-pointer">
          <Card className={`p-4 border transition-all ${activeTab === "urgent" ? "border-rose-500 bg-rose-50/20 shadow-md" : "border-slate-200/80 hover:border-slate-300"}`}>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-rose-600 uppercase">Urgent Priority</span>
              <AlertTriangle className="w-4 h-4 text-rose-600" />
            </div>
            <div className="text-2xl font-black text-rose-900 mt-2">{urgentCount}</div>
          </Card>
        </div>

        <div onClick={() => setActiveTab("pending_collection")} className="cursor-pointer">
          <Card className={`p-4 border transition-all ${activeTab === "pending_collection" ? "border-amber-500 bg-amber-50/20 shadow-md" : "border-slate-200/80 hover:border-slate-300"}`}>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-amber-600 uppercase">Pending Collection</span>
              <Clock className="w-4 h-4 text-amber-600" />
            </div>
            <div className="text-2xl font-black text-amber-900 mt-2">{pendingCollCount}</div>
          </Card>
        </div>

        <div onClick={() => setActiveTab("processing")} className="cursor-pointer">
          <Card className={`p-4 border transition-all ${activeTab === "processing" ? "border-violet-500 bg-violet-50/20 shadow-md" : "border-slate-200/80 hover:border-slate-300"}`}>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-violet-600 uppercase">In Processing / Entry</span>
              <FlaskConical className="w-4 h-4 text-violet-600" />
            </div>
            <div className="text-2xl font-black text-violet-900 mt-2">{collectedCount + processingCount}</div>
          </Card>
        </div>
      </div>

      {/* Worklist Table */}
      <Card className="p-0 border border-slate-200/80 shadow-sm overflow-hidden flex flex-col">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/80 text-[10px] font-black text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">Priority</th>
                <th className="py-3 px-4">Sample ID</th>
                <th className="py-3 px-4">Order #</th>
                <th className="py-3 px-4">Patient</th>
                <th className="py-3 px-4">Tests</th>
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <div className="w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                    Loading technician worklist...
                  </td>
                </tr>
              ) : filteredSamples.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500">
                    <Inbox className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                    No samples found matching current tab view.
                  </td>
                </tr>
              ) : (
                filteredSamples.map((sample) => (
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
                    <td className="py-3 px-4 font-extrabold text-slate-900">
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
                      {sample.order?.tests.join(", ") || "—"}
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-600">
                      {sample.sample_type}
                    </td>
                    <td className="py-3 px-4 font-bold text-slate-800">
                      {sample.collection_status}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          variant="primary"
                          size="sm"
                          className="h-7 px-3 text-[11px] font-bold bg-teal-600 hover:bg-teal-700 text-white"
                          onClick={() => router.push(`/results/${sample.id}`)}
                        >
                          Enter Results
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
