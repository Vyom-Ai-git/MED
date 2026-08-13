"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { Button, Card, Toast } from "@/components/ui/primitives";
import {
  ArrowLeft, Search, X, Plus, Minus, User2, FlaskConical,
  IndianRupee, FileText, CheckCircle2, ChevronRight, AlertCircle
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface PatientResult {
  id: number;
  patient_id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  phone: string;
}

interface TestResult {
  id: number;
  code: string;
  name: string;
  category: string;
  price: string;
  status: string;
}

interface SelectedTest {
  test: TestResult;
}

const PAYMENT_OPTIONS = [
  { value: "Pending", label: "Pending", desc: "Payment to be collected" },
  { value: "Paid", label: "Paid", desc: "Payment collected in full" },
  { value: "Partial", label: "Partial", desc: "Partial payment received" },
];

function calcAge(dob: string): number {
  const birth = new Date(dob);
  const now = new Date();
  let age = now.getFullYear() - birth.getFullYear();
  if (now < new Date(now.getFullYear(), birth.getMonth(), birth.getDate())) age--;
  return age;
}

// ── Section Wrapper ────────────────────────────────────────────────────────────

function Section({ step, title, icon: Icon, children, done }: {
  step: number; title: string; icon: any; children: React.ReactNode; done?: boolean;
}) {
  return (
    <Card className="p-0 border border-slate-200/80 shadow-sm overflow-hidden">
      <div className="flex items-center gap-3 px-5 py-4 bg-slate-50/80 border-b border-slate-100">
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-extrabold transition-all ${done ? "bg-teal-500 text-white" : "bg-white border border-slate-200 text-slate-600"}`}>
          {done ? <CheckCircle2 className="w-4 h-4" /> : step}
        </div>
        <Icon className="w-4 h-4 text-slate-500" />
        <h2 className="text-sm font-extrabold text-slate-900">{title}</h2>
      </div>
      <div className="p-5">{children}</div>
    </Card>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function NewOrderPage() {
  const router = useRouter();
  const { user } = useAuth();

  // Step 1: Patient
  const [patientQuery, setPatientQuery] = useState("");
  const [patientResults, setPatientResults] = useState<PatientResult[]>([]);
  const [isSearchingPatient, setIsSearchingPatient] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState<PatientResult | null>(null);

  // Step 2: Tests
  const [testQuery, setTestQuery] = useState("");
  const [testCategoryFilter, setTestCategoryFilter] = useState("");
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [isSearchingTest, setIsSearchingTest] = useState(false);
  const [selectedTests, setSelectedTests] = useState<SelectedTest[]>([]);
  const [categories, setCategories] = useState<string[]>([]);

  // Step 3: Review
  const [discount, setDiscount] = useState("0");
  const [paymentStatus, setPaymentStatus] = useState("Pending");
  const [notes, setNotes] = useState("");

  // Submit
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const patientTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const testTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Patient Search ───────────────────────────────────────────────────────────

  const searchPatients = useCallback(async (q: string) => {
    if (!q.trim()) { setPatientResults([]); return; }
    setIsSearchingPatient(true);
    try {
      const data = await api.get<{ items: PatientResult[] }>(`/patients?q=${encodeURIComponent(q)}&page_size=8`);
      setPatientResults(data.items || []);
    } catch { setPatientResults([]); }
    finally { setIsSearchingPatient(false); }
  }, []);

  useEffect(() => {
    // Check if patient_id query parameter is passed
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      const pidParam = urlParams.get("patient_id");
      if (pidParam) {
        api.get<PatientResult>(`/patients/${pidParam}`)
          .then(pat => setSelectedPatient(pat))
          .catch(() => {});
      }
    }
  }, []);

  useEffect(() => {
    if (patientTimerRef.current) clearTimeout(patientTimerRef.current);
    patientTimerRef.current = setTimeout(() => searchPatients(patientQuery), 350);
  }, [patientQuery, searchPatients]);

  // ── Test Search ──────────────────────────────────────────────────────────────

  const searchTests = useCallback(async (q: string, category: string) => {
    setIsSearchingTest(true);
    try {
      const params = new URLSearchParams({ page_size: "20", status: "active" });
      if (q.trim()) params.set("q", q);
      if (category) params.set("category", category);
      const data = await api.get<{ items: TestResult[]; categories?: string[] }>(`/tests?${params}`);
      setTestResults((data.items || []).filter(t => t.status === "active"));
      // Extract unique categories from results if present
    } catch { setTestResults([]); }
    finally { setIsSearchingTest(false); }
  }, []);

  useEffect(() => {
    searchTests("", "");
  }, []);

  useEffect(() => {
    if (testTimerRef.current) clearTimeout(testTimerRef.current);
    testTimerRef.current = setTimeout(() => searchTests(testQuery, testCategoryFilter), 300);
  }, [testQuery, testCategoryFilter, searchTests]);

  // Extract categories from test results
  useEffect(() => {
    const cats = Array.from(new Set(testResults.map(t => t.category))).sort();
    setCategories(cats);
  }, [testResults]);

  // ── Test Selection ───────────────────────────────────────────────────────────

  const isTestSelected = (testId: number) => selectedTests.some(s => s.test.id === testId);

  const toggleTest = (test: TestResult) => {
    if (isTestSelected(test.id)) {
      setSelectedTests(prev => prev.filter(s => s.test.id !== test.id));
    } else {
      setSelectedTests(prev => [...prev, { test }]);
    }
  };

  const removeTest = (testId: number) => {
    setSelectedTests(prev => prev.filter(s => s.test.id !== testId));
  };

  // ── Calculations ─────────────────────────────────────────────────────────────

  const subtotal = selectedTests.reduce((acc, s) => acc + parseFloat(s.test.price), 0);
  const parsedDiscount = Math.min(parseFloat(discount) || 0, subtotal);
  const total = Math.max(0, subtotal - parsedDiscount);

  // ── Submit ───────────────────────────────────────────────────────────────────

  const handleSubmit = async () => {
    setError(null);
    if (!selectedPatient) { setError("Please select a patient."); return; }
    if (selectedTests.length === 0) { setError("Please select at least one test."); return; }
    if (parsedDiscount > subtotal) { setError("Discount cannot exceed subtotal."); return; }

    setIsSubmitting(true);
    try {
      const payload = {
        patient_id: selectedPatient.id,
        branch_id: user?.branch_id || null,
        selected_test_ids: selectedTests.map(s => s.test.id),
        discount: parsedDiscount,
        tax: 0,
        payment_status: paymentStatus,
        notes: notes.trim() || null,
      };
      const result = await api.post<{ id: number; order_number: string }>("/orders", payload);
      router.push(`/orders/${result.id}`);
    } catch (err: any) {
      setError(err.detail || "Failed to create order. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const patientComplete = !!selectedPatient;
  const testsComplete = selectedTests.length > 0;

  return (
    <div className="flex flex-col gap-5 w-full max-w-4xl mx-auto">
      {/* Page Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.push("/orders")}
          className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-500 hover:text-slate-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">Create New Order</h1>
          <p className="text-xs text-slate-500 font-medium mt-0.5">Select patient, add tests, review and confirm</p>
        </div>
      </div>

      {error && <Toast type="error" text={error} onClose={() => setError(null)} />}

      {/* Section 1: Patient */}
      <Section step={1} title="Patient" icon={User2} done={patientComplete}>
        {!selectedPatient ? (
          <div className="flex flex-col gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search by name, patient ID, or phone..."
                value={patientQuery}
                onChange={(e) => setPatientQuery(e.target.value)}
                autoFocus
                className="w-full pl-9 pr-3.5 py-2.5 text-sm rounded-lg border border-slate-200 bg-white text-slate-900 outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-colors"
              />
              {isSearchingPatient && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 rounded-full border-2 border-teal-500 border-t-transparent animate-spin" />
              )}
            </div>

            {patientResults.length > 0 && (
              <div className="border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100">
                {patientResults.map(p => (
                  <button
                    key={p.id}
                    onClick={() => { setSelectedPatient(p); setPatientQuery(""); setPatientResults([]); }}
                    className="w-full flex items-center justify-between px-4 py-3 hover:bg-teal-50 transition-colors text-left group"
                  >
                    <div>
                      <p className="text-sm font-bold text-slate-900 group-hover:text-teal-700">
                        {p.first_name} {p.last_name}
                      </p>
                      <p className="text-[11px] text-slate-500 mt-0.5 font-medium">
                        {p.patient_id} · {p.gender.charAt(0).toUpperCase() + p.gender.slice(1)}, {calcAge(p.date_of_birth)} yrs · {p.phone}
                      </p>
                    </div>
                    <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-teal-500" />
                  </button>
                ))}
              </div>
            )}

            {patientQuery && !isSearchingPatient && patientResults.length === 0 && (
              <div className="flex items-center gap-2 text-xs text-slate-500 font-medium px-1">
                <AlertCircle className="w-3.5 h-3.5" />
                No patients found for "{patientQuery}". Try a different search.
              </div>
            )}

            {!patientQuery && (
              <p className="text-xs text-slate-400 font-medium px-1">
                Search by patient name, ID (PAT-...), or phone number
              </p>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-between p-4 rounded-xl bg-teal-50 border border-teal-100">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-teal-500 text-white flex items-center justify-center text-xs font-extrabold">
                {selectedPatient.first_name.charAt(0)}{selectedPatient.last_name.charAt(0)}
              </div>
              <div>
                <p className="text-sm font-extrabold text-teal-900">
                  {selectedPatient.first_name} {selectedPatient.last_name}
                </p>
                <p className="text-[11px] text-teal-700 font-semibold mt-0.5">
                  {selectedPatient.patient_id} · {selectedPatient.gender.charAt(0).toUpperCase() + selectedPatient.gender.slice(1)}, {calcAge(selectedPatient.date_of_birth)} yrs · {selectedPatient.phone}
                </p>
              </div>
            </div>
            <button
              onClick={() => setSelectedPatient(null)}
              className="p-1.5 rounded-lg hover:bg-teal-100 text-teal-600 hover:text-teal-800 transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </Section>

      {/* Section 2: Tests */}
      <Section step={2} title="Tests" icon={FlaskConical} done={testsComplete}>
        <div className="flex flex-col gap-4">
          {/* Search + Filter */}
          <div className="flex gap-2.5">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search by test name or code..."
                value={testQuery}
                onChange={(e) => setTestQuery(e.target.value)}
                className="w-full pl-9 pr-3.5 py-2 text-xs rounded-lg border border-slate-200 bg-white text-slate-900 outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-colors"
              />
              {isSearchingTest && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 rounded-full border-2 border-teal-500 border-t-transparent animate-spin" />
              )}
            </div>
            <select
              value={testCategoryFilter}
              onChange={(e) => setTestCategoryFilter(e.target.value)}
              className="text-xs font-semibold rounded-lg border border-slate-200 bg-white text-slate-700 outline-none px-3 py-2 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-colors"
            >
              <option value="">All Categories</option>
              {categories.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          {/* Test Catalog */}
          {testResults.length > 0 ? (
            <div className="flex flex-col gap-1.5 max-h-56 overflow-y-auto pr-1">
              {testResults.map(test => {
                const selected = isTestSelected(test.id);
                return (
                  <button
                    key={test.id}
                    onClick={() => toggleTest(test)}
                    className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl border text-xs font-semibold transition-all ${
                      selected
                        ? "bg-teal-50 border-teal-300 text-teal-800"
                        : "bg-white border-slate-200 text-slate-700 hover:border-teal-200 hover:bg-teal-50/30"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <div className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-colors ${selected ? "bg-teal-500 border-teal-500" : "border-slate-300"}`}>
                        {selected && <CheckCircle2 className="w-3 h-3 text-white" />}
                      </div>
                      <div className="text-left">
                        <p className="font-bold">{test.name}</p>
                        <p className="text-[10px] text-slate-400 uppercase tracking-wide">{test.code} · {test.category}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-0.5 font-extrabold text-slate-900">
                      <IndianRupee className="w-3 h-3" />
                      {parseFloat(test.price).toLocaleString("en-IN")}
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            !isSearchingTest && (
              <p className="text-xs text-slate-400 font-medium text-center py-4">
                {testQuery ? `No active tests found for "${testQuery}"` : "No active tests available."}
              </p>
            )
          )}

          {/* Selected Tests */}
          {selectedTests.length > 0 && (
            <div className="border-t border-slate-100 pt-4">
              <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">
                Selected Tests ({selectedTests.length})
              </p>
              <div className="flex flex-col gap-1.5">
                {selectedTests.map(({ test }) => (
                  <div key={test.id} className="flex items-center justify-between px-3 py-2 bg-slate-50 rounded-lg border border-slate-100">
                    <div>
                      <p className="text-xs font-bold text-slate-900">{test.name}</p>
                      <p className="text-[10px] text-slate-400 uppercase font-bold tracking-wide">{test.code}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-extrabold text-slate-800 flex items-center gap-0.5">
                        <IndianRupee className="w-3 h-3" />
                        {parseFloat(test.price).toLocaleString("en-IN")}
                      </span>
                      <button
                        onClick={() => removeTest(test.id)}
                        className="p-1 rounded-lg hover:bg-rose-100 text-slate-400 hover:text-rose-600 transition-colors"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </Section>

      {/* Section 3: Review & Payment */}
      <Section step={3} title="Review & Payment" icon={IndianRupee} done={false}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Left: Financial Summary */}
          <div className="flex flex-col gap-4">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100 space-y-2.5">
              <div className="flex justify-between text-xs">
                <span className="font-semibold text-slate-500">Subtotal</span>
                <span className="font-bold text-slate-700">₹{subtotal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
              </div>

              {/* Discount Input */}
              <div className="flex items-center justify-between gap-4">
                <span className="text-xs font-semibold text-slate-500 flex-shrink-0">Discount (₹)</span>
                <input
                  type="number"
                  min="0"
                  max={subtotal}
                  step="0.01"
                  value={discount}
                  onChange={(e) => setDiscount(e.target.value)}
                  className="w-28 text-right text-xs font-bold rounded-lg border border-slate-200 bg-white text-slate-900 outline-none px-3 py-1.5 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-colors"
                />
              </div>

              <div className="flex justify-between text-xs">
                <span className="font-semibold text-slate-500">Tax</span>
                <span className="font-medium text-slate-500">₹0.00</span>
              </div>

              <div className="border-t border-slate-200 pt-2.5">
                <div className="flex justify-between">
                  <span className="text-sm font-extrabold text-slate-900">Total</span>
                  <span className="text-sm font-extrabold text-teal-700">
                    ₹{total.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Payment + Notes */}
          <div className="flex flex-col gap-4">
            {/* Payment Status */}
            <div>
              <p className="text-xs font-bold text-slate-700 mb-2">Payment Status</p>
              <div className="flex flex-col gap-1.5">
                {PAYMENT_OPTIONS.map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => setPaymentStatus(opt.value)}
                    className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl border text-xs transition-all ${
                      paymentStatus === opt.value
                        ? "bg-teal-50 border-teal-300 text-teal-800"
                        : "bg-white border-slate-200 text-slate-600 hover:border-slate-300"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <div className={`w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center ${paymentStatus === opt.value ? "border-teal-500" : "border-slate-300"}`}>
                        {paymentStatus === opt.value && <div className="w-2 h-2 rounded-full bg-teal-500" />}
                      </div>
                      <div className="text-left">
                        <p className="font-bold">{opt.label}</p>
                        <p className="text-[10px] text-slate-400">{opt.desc}</p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Notes */}
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1.5">Notes (Optional)</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Any special instructions or notes..."
                rows={3}
                className="w-full text-xs rounded-lg border border-slate-200 bg-white text-slate-900 outline-none px-3.5 py-2.5 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-colors resize-none"
              />
            </div>
          </div>
        </div>
      </Section>

      {/* Action Footer */}
      <div className="flex items-center justify-between gap-4 pb-6">
        <div className="text-xs text-slate-500 font-medium">
          {!patientComplete && "⬆ Select a patient to continue"}
          {patientComplete && !testsComplete && "⬆ Add at least one test"}
          {patientComplete && testsComplete && (
            <span className="text-teal-700 font-bold">
              Ready: {selectedTests.length} test{selectedTests.length > 1 ? "s" : ""} · Total ₹{total.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </span>
          )}
        </div>
        <div className="flex gap-2.5">
          <Button variant="outline" onClick={() => router.push("/orders")} disabled={isSubmitting}
            className="text-xs font-bold px-4 py-2.5">
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            isLoading={isSubmitting}
            disabled={!patientComplete || !testsComplete || isSubmitting}
            className="text-xs font-bold px-5 py-2.5 flex items-center gap-2 shadow-sm"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            Create Order
          </Button>
        </div>
      </div>
    </div>
  );
}
