"use client";

/**
 * AI Report Assistant
 * --------------------
 * Self-contained module: explains an already-verified report's results in
 * plain language. Drop into any page with:
 *
 *   <AIReportAssistant reportId={report.id} />
 *
 * Talks to POST /reports/{id}/ai-analysis on the existing backend, which in
 * turn calls Gemini using GEMINI_API_KEY / GEMINI_MODEL from the server .env.
 * Never diagnoses or prescribes — explains only, with a fixed safety notice.
 */

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Card, Button, Badge } from "@/components/ui/primitives";
import { Sparkles, RefreshCw, AlertTriangle, Languages } from "lucide-react";

interface AITestFinding {
  test_name: string;
  parameter_name: string;
  value: string;
  unit: string;
  reference_range: string;
  status: string;
  explanation: string;
}

interface AIAnalysisResult {
  report_id: number;
  report_number: string;
  summary: string;
  tests: AITestFinding[];
  key_findings: string[];
  doctor_discussion: string[];
  safety_notice: string;
}

const statusBadge: Record<string, string> = {
  normal: "verified",
  attention: "pending",
  critical: "failed",
  unknown: "draft",
};

export function AIReportAssistant({ reportId }: { reportId: number | string }) {
  const [language, setLanguage] = useState<"en" | "ml">("en");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AIAnalysisResult | null>(null);

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.post<AIAnalysisResult>(
        `/reports/${reportId}/ai-analysis?language=${language}`,
        {}
      );
      setResult(data);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 503) {
        setError(
          "AI Report Assistant isn't configured yet — add GEMINI_API_KEY and GEMINI_MODEL to the backend .env to enable it."
        );
      } else {
        setError(err?.detail || err?.message || "Couldn't generate an AI explanation right now.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card
      className="border-indigo-200/70"
      headerAction={
        !result ? undefined : (
          <Button variant="outline" size="sm" onClick={runAnalysis} isLoading={loading}>
            <RefreshCw className="w-3.5 h-3.5 mr-1.5" /> Regenerate
          </Button>
        )
      }
      title="AI Report Assistant"
      subtitle="Plain-language explanation of this report's verified results"
    >
      {!result && !loading && (
        <div className="flex flex-col items-center text-center gap-3 py-6">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center border border-indigo-100">
            <Sparkles className="w-6 h-6" />
          </div>
          <p className="text-sm text-slate-600 font-medium max-w-md">
            Generate a plain-language summary of these verified results — useful for
            explaining a report to a patient at the counter or over a call.
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setLanguage("en")}
              className={`text-[11px] font-bold px-2.5 py-1 rounded-full border transition-all ${
                language === "en"
                  ? "bg-indigo-600 text-white border-indigo-600"
                  : "bg-white text-slate-500 border-slate-200 hover:bg-slate-50"
              }`}
            >
              English
            </button>
            <button
              onClick={() => setLanguage("ml")}
              className={`text-[11px] font-bold px-2.5 py-1 rounded-full border transition-all ${
                language === "ml"
                  ? "bg-indigo-600 text-white border-indigo-600"
                  : "bg-white text-slate-500 border-slate-200 hover:bg-slate-50"
              }`}
            >
              <Languages className="w-3 h-3 inline mr-1" /> Malayalam
            </button>
          </div>
          <Button variant="primary" onClick={runAnalysis} className="bg-indigo-600 hover:bg-indigo-700 mt-1">
            <Sparkles className="w-4 h-4 mr-2" /> Analyze with AI
          </Button>
        </div>
      )}

      {loading && (
        <div className="flex flex-col items-center justify-center gap-2.5 py-10">
          <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm font-medium text-slate-500">Reading verified results…</span>
        </div>
      )}

      {error && !loading && (
        <div className="flex items-start gap-2.5 bg-amber-50 border border-amber-200 text-amber-800 rounded-lg px-4 py-3 text-xs font-semibold">
          <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {result && !loading && (
        <div className="flex flex-col gap-5">
          <div className="bg-indigo-50/60 border border-indigo-100 rounded-lg px-4 py-3">
            <p className="text-sm text-slate-800 font-medium leading-relaxed">{result.summary}</p>
          </div>

          {result.tests.length > 0 && (
            <div className="flex flex-col gap-2">
              <span className="text-[10px] uppercase tracking-wider font-extrabold text-slate-400">
                Result-by-Result
              </span>
              <div className="flex flex-col gap-2">
                {result.tests.map((t, idx) => (
                  <div
                    key={idx}
                    className="flex flex-col gap-1 rounded-lg border border-slate-200 px-3.5 py-2.5"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-slate-900">
                        {t.parameter_name || t.test_name}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-slate-700">
                          {t.value} {t.unit}
                        </span>
                        <Badge status={statusBadge[t.status] || "draft"} />
                      </div>
                    </div>
                    {t.explanation && (
                      <p className="text-xs text-slate-600 leading-relaxed">{t.explanation}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.key_findings.length > 0 && (
            <div>
              <span className="text-[10px] uppercase tracking-wider font-extrabold text-slate-400">
                Key Findings
              </span>
              <ul className="mt-1.5 flex flex-col gap-1">
                {result.key_findings.map((f, idx) => (
                  <li key={idx} className="text-xs text-slate-700 font-medium flex items-start gap-2">
                    <span className="text-indigo-500 mt-0.5">•</span> {f}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.doctor_discussion.length > 0 && (
            <div>
              <span className="text-[10px] uppercase tracking-wider font-extrabold text-slate-400">
                Worth Discussing With a Doctor
              </span>
              <ul className="mt-1.5 flex flex-col gap-1">
                {result.doctor_discussion.map((f, idx) => (
                  <li key={idx} className="text-xs text-slate-700 font-medium flex items-start gap-2">
                    <span className="text-teal-500 mt-0.5">•</span> {f}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex items-start gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3.5 py-2.5">
            <AlertTriangle className="w-3.5 h-3.5 text-slate-400 mt-0.5 flex-shrink-0" />
            <p className="text-[11px] text-slate-500 font-medium leading-relaxed">
              {result.safety_notice}
            </p>
          </div>
        </div>
      )}
    </Card>
  );
}

export default AIReportAssistant;
