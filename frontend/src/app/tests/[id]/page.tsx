"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useParams, useRouter } from "next/navigation";
import { Card, Button, Badge } from "@/components/ui/primitives";
import {
  ArrowLeft,
  FlaskConical,
  Activity,
  AlertCircle,
  Hash,
  Coins,
  Settings,
  ShieldCheck,
  Percent
} from "lucide-react";

interface TestParameter {
  id: number;
  name: string;
  code: string;
  unit: string | null;
  data_type: string;
  reference_range: string | null;
  lower_limit: number | null;
  upper_limit: number | null;
  critical_low: number | null;
  critical_high: number | null;
  ref_gender: string | null;
  ref_age_min: number | null;
  ref_age_max: number | null;
  ref_context: string | null;
  display_order: number;
}

interface Test {
  id: number;
  code: string;
  name: string;
  category: string;
  description: string | null;
  price: string;
  status: string;
  parameters: TestParameter[];
}

export default function TestDetailPage() {
  const params = useParams();
  const router = useRouter();
  const testId = params.id;

  const [test, setTest] = useState<Test | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTestDetails = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.get<Test>(`/tests/${testId}`);
        setTest(data);
      } catch (err: any) {
        setError(err.detail || "Failed to load test details.");
      } finally {
        setIsLoading(false);
      }
    };

    if (testId) {
      fetchTestDetails();
    }
  }, [testId]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 w-full">
        <div className="w-8 h-8 border-4 border-teal-500 border-t-transparent rounded-full animate-spin"></div>
        <span className="text-xs text-slate-500 font-semibold mt-4">Loading test parameters...</span>
      </div>
    );
  }

  if (error || !test) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center select-none max-w-md mx-auto w-full px-4">
        <div className="w-16 h-16 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center mb-6 border border-rose-100/50">
          <AlertCircle className="w-8 h-8" />
        </div>
        <h2 className="text-lg font-black text-slate-900 tracking-tight">Test Not Found</h2>
        <p className="text-sm text-slate-500 font-medium mt-2 leading-relaxed">
          {error || "We could not find the test catalog configuration. It may belong to another organization."}
        </p>
        <Button
          variant="secondary"
          onClick={() => router.push("/tests")}
          className="mt-6 font-bold shadow-sm"
        >
          Return to Test Catalog
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 w-full animate-in fade-in duration-200">
      {/* Return header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.push("/tests")}
          className="p-2 hover:bg-slate-100 rounded-lg text-slate-500 hover:text-slate-900 border border-slate-200/80 bg-white transition-all shadow-sm"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <span className="block text-[10px] text-teal-600 font-black uppercase tracking-wider">
            Catalog Reference Configuration
          </span>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight mt-0.5">
            {test.name} ({test.code})
          </h1>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left Side: Test summary details card */}
        <Card className="lg:col-span-1 p-6 border border-slate-200/80 shadow-sm flex flex-col gap-5">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-teal-50 border border-teal-100 text-teal-600 flex items-center justify-center font-bold text-lg">
              <FlaskConical className="w-6 h-6" />
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-slate-400 font-black uppercase">Category</span>
              <span className="text-sm font-black text-slate-800 tracking-tight mt-0.5">
                {test.category}
              </span>
            </div>
          </div>

          <hr className="border-slate-100" />

          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
              <span className="flex items-center gap-1.5 text-slate-500">
                <Coins className="w-4 h-4 text-slate-400" />
                Base Pricing
              </span>
              <span className="font-extrabold text-slate-900 text-sm">
                ₹{parseFloat(test.price).toFixed(2)}
              </span>
            </div>

            <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
              <span className="flex items-center gap-1.5 text-slate-500">
                <Settings className="w-4 h-4 text-slate-400" />
                Status
              </span>
              <Badge status={test.status} />
            </div>

            <div className="flex flex-col gap-1.5 pt-2 border-t border-slate-100/50">
              <span className="text-[10px] text-slate-400 font-bold uppercase">Clinical Description</span>
              <p className="text-xs text-slate-600 leading-relaxed font-semibold">
                {test.description || "No catalog description configured for this test code."}
              </p>
            </div>
          </div>
        </Card>

        {/* Right Side: Parameters details list */}
        <Card className="lg:col-span-2 p-0 border border-slate-200/80 shadow-sm overflow-hidden flex flex-col">
          <div className="p-5 border-b border-slate-100 bg-slate-50/20 flex items-center gap-2">
            <Activity className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-black text-slate-800">Parameters Reference Guidelines</span>
          </div>

          {test.parameters.length === 0 ? (
            <div className="p-12 text-center text-slate-400 font-semibold text-xs py-16">
              No parameters configured for this catalog test.
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {test.parameters
                .sort((a, b) => a.display_order - b.display_order)
                .map((param) => (
                  <div key={param.id} className="p-5 flex flex-col gap-3">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <span className="text-xs font-black text-slate-800">{param.name}</span>
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold border border-slate-200 bg-slate-50 text-slate-500 uppercase ml-2.5">
                          {param.code}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-xs font-semibold text-slate-600 text-right">
                        <div>
                          <span className="block text-[10px] text-slate-400 font-bold uppercase">Data Type</span>
                          <span className="block font-bold text-slate-700 capitalize mt-0.5">{param.data_type}</span>
                        </div>
                        <div>
                          <span className="block text-[10px] text-slate-400 font-bold uppercase">Reporting Unit</span>
                          <span className="block font-bold text-slate-700 mt-0.5">{param.unit || "N/A"}</span>
                        </div>
                      </div>
                    </div>

                    {param.data_type === "numeric" && (
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-slate-50/50 p-3 rounded-lg border border-slate-200/40 text-xs font-semibold text-slate-600">
                        {/* Reference Range */}
                        <div className="flex flex-col gap-0.5">
                          <span className="text-[10px] text-slate-400 font-bold uppercase">Reference range</span>
                          <span className="text-slate-800 font-bold mt-0.5">
                            {param.reference_range || (param.lower_limit !== null && param.upper_limit !== null 
                              ? `${param.lower_limit} - ${param.upper_limit}` 
                              : "Not configured")}
                          </span>
                        </div>

                        {/* Numeric Limits */}
                        <div className="flex flex-col gap-0.5">
                          <span className="text-[10px] text-slate-400 font-bold uppercase">Limit values</span>
                          <span className="text-slate-700 mt-0.5">
                            {param.lower_limit !== null ? `Min: ${param.lower_limit}` : ""}
                            {param.lower_limit !== null && param.upper_limit !== null ? " • " : ""}
                            {param.upper_limit !== null ? `Max: ${param.upper_limit}` : ""}
                            {param.lower_limit === null && param.upper_limit === null ? "None" : ""}
                          </span>
                        </div>

                        {/* Critical values */}
                        <div className="flex flex-col gap-0.5">
                          <span className="text-[10px] text-rose-500 font-bold uppercase">Critical boundaries</span>
                          <span className="text-rose-600 font-bold mt-0.5">
                            {param.critical_low !== null ? `Low: <${param.critical_low}` : ""}
                            {param.critical_low !== null && param.critical_high !== null ? " • " : ""}
                            {param.critical_high !== null ? `High: >${param.critical_high}` : ""}
                            {param.critical_low === null && param.critical_high === null ? "None Configured" : ""}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
