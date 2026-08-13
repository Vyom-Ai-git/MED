"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { Button, Card, Toast, Badge } from "@/components/ui/primitives";
import {
  ArrowLeft, FlaskConical, AlertCircle, AlertTriangle, CheckCircle2, Save, Send, User, FileText
} from "lucide-react";

interface TestParameter {
  id: number;
  test_id: number;
  name: string;
  code: string;
  unit?: string;
  data_type: string;
  reference_range?: string;
  lower_limit?: number;
  upper_limit?: number;
  critical_low?: number;
  critical_high?: number;
}

interface TestDetail {
  id: number;
  code: string;
  name: string;
  category: string;
  parameters: TestParameter[];
}

interface OrderItem {
  id: number;
  test_id: number;
  test_name_snapshot: string;
  test_code_snapshot: string;
}

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
  patient?: PatientSummary;
  items: OrderItem[];
}

interface Sample {
  id: number;
  order_id: number;
  sample_identifier: string;
  sample_type: string;
  collection_status: string;
  priority: string;
  order?: OrderSummary;
}

interface ExistingResult {
  id: number;
  parameter_id: number;
  order_item_id: number;
  test_id: number;
  raw_value?: string;
  numeric_value?: number;
  abnormal_flag: string;
  critical_flag: boolean;
  status: string;
}

export default function ResultEntryPage() {
  const params = useParams();
  const router = useRouter();
  const sampleId = params.id;
  const { user } = useAuth();

  const [sample, setSample] = useState<Sample | null>(null);
  const [testDetails, setTestDetails] = useState<Record<number, TestDetail>>({});
  const [formValues, setFormValues] = useState<Record<string, string>>({}); // key: `${order_item_id}_${param_id}` -> raw_value
  const [existingResults, setExistingResults] = useState<Record<string, ExistingResult>>({});

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // 1. Fetch sample details & order details
      const sampleData = await api.get<Sample>(`/samples/${sampleId}`);
      setSample(sampleData);

      // 2. Fetch existing results for sample
      const existingRes = await api.get<ExistingResult[]>(`/samples/${sampleId}/results`).catch(() => []);
      const resMap: Record<string, ExistingResult> = {};
      const initialValues: Record<string, string> = {};

      for (const r of existingRes) {
        const key = `${r.order_item_id}_${r.parameter_id}`;
        resMap[key] = r;
        if (r.raw_value !== undefined && r.raw_value !== null) {
          initialValues[key] = r.raw_value;
        }
      }
      setExistingResults(resMap);

      // 3. Fetch test catalog parameter definitions dynamically for each test in order
      if (sampleData.order?.items) {
        const details: Record<number, TestDetail> = {};
        for (const item of sampleData.order.items) {
          if (item.test_id) {
            const tData = await api.get<TestDetail>(`/tests/${item.test_id}`).catch(() => null);
            if (tData) details[item.test_id] = tData;
          }
        }
        setTestDetails(details);
      }

      setFormValues(prev => ({ ...initialValues, ...prev }));
    } catch (err: any) {
      setError(err.detail || "Failed to load result entry form.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (sampleId) fetchData();
  }, [sampleId]);

  const handleInputChange = (orderItemId: number, paramId: number, value: string) => {
    const key = `${orderItemId}_${paramId}`;
    setFormValues(prev => ({ ...prev, [key]: value }));
  };

  // Compute live preview flag for numeric parameters
  const computeFlagPreview = (param: TestParameter, valStr: string) => {
    if (!valStr || param.data_type !== "numeric") return null;
    const num = parseFloat(valStr);
    if (isNaN(num)) return { text: "INVALID", type: "error" };

    let isCritical = false;
    if (param.critical_low !== undefined && num <= param.critical_low) isCritical = true;
    if (param.critical_high !== undefined && num >= param.critical_high) isCritical = true;

    if (isCritical) return { text: "CRITICAL", type: "critical" };

    if (param.lower_limit !== undefined && num < param.lower_limit) return { text: "LOW", type: "abnormal" };
    if (param.upper_limit !== undefined && num > param.upper_limit) return { text: "HIGH", type: "abnormal" };

    return { text: "NORMAL", type: "normal" };
  };

  const preparePayload = () => {
    if (!sample?.order?.items) return [];
    const resultsPayload = [];

    for (const item of sample.order.items) {
      const test = testDetails[item.test_id];
      if (test) {
        for (const param of test.parameters) {
          const key = `${item.id}_${param.id}`;
          const val = formValues[key] || "";
          resultsPayload.push({
            parameter_id: param.id,
            order_item_id: item.id,
            test_id: item.test_id,
            raw_value: val,
          });
        }
      }
    }
    return resultsPayload;
  };

  const handleSaveDraft = async () => {
    setIsSaving(true);
    setError(null);
    try {
      const payload = { results: preparePayload() };
      await api.post(`/samples/${sampleId}/results/draft`, payload);
      setSuccessMessage("Draft results saved successfully.");
      fetchData();
    } catch (err: any) {
      setError(err.detail || "Failed to save draft results.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSubmitResults = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      const payload = { results: preparePayload() };
      await api.post(`/samples/${sampleId}/results/submit`, payload);
      setSuccessMessage("Results submitted successfully! Status updated to Entered.");
      setTimeout(() => {
        router.push("/worklist");
      }, 1200);
    } catch (err: any) {
      setError(err.detail || "Failed to submit results. Check mandatory fields.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 w-full">
        <div className="w-8 h-8 border-4 border-teal-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-xs text-slate-500 font-semibold mt-4">Generating parameter-bound result form...</span>
      </div>
    );
  }

  if (error && !sample) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center max-w-md mx-auto">
        <AlertTriangle className="w-10 h-10 text-rose-600 mb-3" />
        <h2 className="text-lg font-black text-slate-900">Result Form Error</h2>
        <p className="text-xs text-slate-500 mt-2">{error}</p>
        <Button variant="secondary" onClick={() => router.push("/worklist")} className="mt-6 font-bold">
          Return to Worklist
        </Button>
      </div>
    );
  }

  const patient = sample?.order?.patient;

  return (
    <div className="flex flex-col gap-6 w-full animate-in fade-in duration-200">
      {/* Return & Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/worklist")}
            className="p-2 hover:bg-slate-100 rounded-lg text-slate-500 hover:text-slate-900 border border-slate-200/80 bg-white transition-all shadow-sm"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-teal-600 font-black uppercase tracking-wider">
                Laboratory Result Entry
              </span>
            </div>
            <h1 className="text-xl font-extrabold text-slate-900 tracking-tight mt-0.5">
              Sample {sample?.sample_identifier}
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            isLoading={isSaving}
            onClick={handleSaveDraft}
            className="border-slate-200/80 bg-white hover:bg-slate-50 font-bold text-xs shadow-sm h-9"
          >
            <Save className="w-3.5 h-3.5 mr-1.5" /> Save Draft
          </Button>

          <Button
            variant="primary"
            isLoading={isSubmitting}
            onClick={handleSubmitResults}
            className="bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs shadow-sm h-9"
          >
            <Send className="w-3.5 h-3.5 mr-1.5" /> Submit Completed Results
          </Button>
        </div>
      </div>

      {successMessage && <Toast message={successMessage} type="success" onClose={() => setSuccessMessage(null)} />}
      {error && <Toast message={error} type="error" onClose={() => setError(null)} />}

      {/* Patient & Order Overview Banner */}
      <Card className="p-5 border border-slate-200/80 shadow-sm bg-slate-50/50 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
        <div>
          <span className="text-[10px] text-slate-400 font-bold uppercase block">Patient</span>
          <span className="font-extrabold text-slate-900 text-sm">
            {patient ? `${patient.first_name} ${patient.last_name}` : "—"}
          </span>
          <span className="block text-[11px] text-slate-500 font-semibold mt-0.5">
            ID: {patient?.patient_id} | {patient?.gender}
          </span>
        </div>

        <div>
          <span className="text-[10px] text-slate-400 font-bold uppercase block">Order & Specimen</span>
          <span className="font-bold text-teal-700 text-sm">{sample?.order?.order_number}</span>
          <span className="block text-[11px] text-slate-500 font-semibold mt-0.5">
            Type: {sample?.sample_type} | Status: {sample?.collection_status}
          </span>
        </div>

        <div>
          <span className="text-[10px] text-slate-400 font-bold uppercase block">Ordered Tests</span>
          <span className="font-bold text-slate-800 text-xs">
            {sample?.order?.items.map(i => i.test_name_snapshot).join(", ")}
          </span>
        </div>
      </Card>

      {/* Parameter-Bound Entry Forms */}
      <div className="flex flex-col gap-6">
        {sample?.order?.items.map((item) => {
          const test = testDetails[item.test_id];
          if (!test) return null;

          return (
            <Card key={item.id} className="p-0 border border-slate-200/80 shadow-sm overflow-hidden flex flex-col">
              <div className="px-5 py-3.5 bg-slate-100/70 border-b border-slate-200/80 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FlaskConical className="w-4 h-4 text-teal-600" />
                  <h2 className="text-xs font-black text-slate-900 uppercase tracking-wider">
                    {item.test_name_snapshot} ({item.test_code_snapshot})
                  </h2>
                </div>
                <span className="text-[10px] font-bold text-slate-500 uppercase">
                  {test.category}
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50/50 text-[10px] font-black text-slate-400 uppercase tracking-wider">
                      <th className="py-3 px-5">Parameter Name</th>
                      <th className="py-3 px-5">Result Value</th>
                      <th className="py-3 px-5">Unit</th>
                      <th className="py-3 px-5">Reference Range</th>
                      <th className="py-3 px-5">Live Flag</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-xs">
                    {test.parameters.map((param) => {
                      const key = `${item.id}_${param.id}`;
                      const currentVal = formValues[key] || "";
                      const previewFlag = computeFlagPreview(param, currentVal);

                      return (
                        <tr key={param.id} className="hover:bg-slate-50/80 transition-colors">
                          <td className="py-3 px-5">
                            <div className="font-bold text-slate-900">{param.name}</div>
                            <div className="text-[10px] text-slate-400 font-semibold">{param.code}</div>
                          </td>

                          <td className="py-3 px-5">
                            {param.data_type === "boolean" ? (
                              <select
                                value={currentVal}
                                onChange={(e) => handleInputChange(item.id, param.id, e.target.value)}
                                className="px-3 py-1.5 border border-slate-200 rounded-lg text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-teal-500/20"
                              >
                                <option value="">Select...</option>
                                <option value="Positive">Positive</option>
                                <option value="Negative">Negative</option>
                              </select>
                            ) : (
                              <input
                                type="text"
                                placeholder={`Enter ${param.data_type} result...`}
                                value={currentVal}
                                onChange={(e) => handleInputChange(item.id, param.id, e.target.value)}
                                className="w-48 px-3 py-1.5 border border-slate-200 rounded-lg text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                              />
                            )}
                          </td>

                          <td className="py-3 px-5 font-semibold text-slate-600">
                            {param.unit || "—"}
                          </td>

                          <td className="py-3 px-5 font-medium text-slate-600">
                            {param.reference_range || (param.lower_limit !== undefined ? `${param.lower_limit} – ${param.upper_limit}` : "—")}
                          </td>

                          <td className="py-3 px-5">
                            {previewFlag ? (
                              <span
                                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-black border ${
                                  previewFlag.type === "critical"
                                    ? "bg-rose-600 text-white border-rose-700 animate-pulse"
                                    : previewFlag.type === "abnormal"
                                    ? "bg-amber-100 text-amber-800 border-amber-300"
                                    : previewFlag.type === "error"
                                    ? "bg-slate-100 text-slate-600 border-slate-300"
                                    : "bg-emerald-100 text-emerald-800 border-emerald-300"
                                }`}
                              >
                                {previewFlag.text}
                              </span>
                            ) : (
                              <span className="text-slate-300 text-[11px]">—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
