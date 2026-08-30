"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ShieldCheck, ShieldX, Clock } from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface VerifyResult {
  valid: boolean;
  reason?: string;
  report_number?: string;
  status?: string;
  organization_name?: string;
  patient_display_name?: string;
  generated_at?: string;
  verification_code?: string;
}

export default function VerifyReportPage() {
  const params = useParams();
  const token = params.token as string;

  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState<VerifyResult | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/public/reports/verify/${token}`);
        const data = await res.json();
        setResult(data);
      } catch {
        setResult({ valid: false, reason: "error" });
      } finally {
        setLoading(false);
      }
    })();
  }, [token]);

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-center gap-2.5 mb-6">
          <div className="w-8 h-8 rounded-lg bg-teal-600 flex items-center justify-center text-white font-black text-sm shadow-md">
            L
          </div>
          <span className="font-extrabold text-sm text-slate-900 tracking-tight">Vyoma LabOS</span>
        </div>

        <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
          {loading ? (
            <div className="flex flex-col items-center justify-center gap-3 py-16">
              <div className="w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs font-semibold text-slate-500">Checking report authenticity…</span>
            </div>
          ) : result?.valid ? (
            <div className="flex flex-col items-center text-center gap-4 px-8 py-10">
              <div className="w-16 h-16 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-100">
                <ShieldCheck className="w-8 h-8" />
              </div>
              <div>
                <h1 className="text-lg font-black text-slate-900 tracking-tight">
                  Verified Authentic Report
                </h1>
                <p className="text-xs text-slate-500 font-medium mt-1">
                  This report was genuinely issued by {result.organization_name}.
                </p>
              </div>

              <div className="w-full flex flex-col gap-2.5 mt-2 text-left">
                <div className="flex items-center justify-between text-xs font-semibold border-b border-slate-100 pb-2">
                  <span className="text-slate-500">Report Number</span>
                  <span className="font-mono font-bold text-slate-900">{result.report_number}</span>
                </div>
                <div className="flex items-center justify-between text-xs font-semibold border-b border-slate-100 pb-2">
                  <span className="text-slate-500">Patient</span>
                  <span className="font-bold text-slate-900">{result.patient_display_name}</span>
                </div>
                <div className="flex items-center justify-between text-xs font-semibold border-b border-slate-100 pb-2">
                  <span className="text-slate-500">Status</span>
                  <span className="font-bold text-emerald-700">{result.status}</span>
                </div>
                {result.generated_at && (
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span className="text-slate-500">Issued</span>
                    <span className="font-bold text-slate-900">
                      {new Date(result.generated_at).toLocaleDateString()}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center text-center gap-4 px-8 py-10">
              <div className="w-16 h-16 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center border border-rose-100">
                {result?.reason === "expired" ? (
                  <Clock className="w-8 h-8" />
                ) : (
                  <ShieldX className="w-8 h-8" />
                )}
              </div>
              <div>
                <h1 className="text-lg font-black text-slate-900 tracking-tight">
                  {result?.reason === "expired" ? "Verification Link Expired" : "Not a Recognized Report"}
                </h1>
                <p className="text-xs text-slate-500 font-medium mt-1 max-w-xs">
                  {result?.reason === "expired"
                    ? "This report's verification link has expired. Contact the laboratory for a fresh copy."
                    : "We couldn't confirm this report's authenticity. If you scanned a QR code, please contact the issuing laboratory directly."}
                </p>
              </div>
            </div>
          )}
        </div>

        <p className="text-center text-[11px] text-slate-400 font-medium mt-5">
          Powered by Vyoma LabOS — Laboratory Management Platform
        </p>
      </div>
    </div>
  );
}
