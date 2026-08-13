"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { Button, Card, Toast } from "@/components/ui/primitives";
import {
  ArrowLeft, ClipboardList, User2, FlaskConical, IndianRupee,
  Calendar, Shield, XCircle, CreditCard, ChevronRight, Clock,
  CheckCircle2, AlertCircle, FileText
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface OrderItem {
  id: number;
  test_id?: number;
  test_name_snapshot: string;
  test_code_snapshot: string;
  unit_price: string;
  quantity: number;
  discount: string;
  total: string;
  status: string;
}

interface OrderPatient {
  id: number;
  patient_id: string;
  first_name: string;
  last_name: string;
  phone: string;
  date_of_birth: string;
}

interface OrderUser {
  id: number;
  name: string;
  email: string;
  role: string;
}

interface Order {
  id: number;
  order_number: string;
  status: string;
  payment_status: string;
  subtotal: string;
  discount: string;
  tax: string;
  total_amount: string;
  notes?: string;
  created_at: string;
  updated_at: string;
  patient?: OrderPatient;
  ordering_user?: OrderUser;
  items: OrderItem[];
}

// ── Status helpers ─────────────────────────────────────────────────────────────

function StatusChip({ status }: { status: string }) {
  const map: Record<string, string> = {
    "Pending": "bg-amber-100 text-amber-800 border border-amber-200",
    "Sample Collected": "bg-blue-100 text-blue-800 border border-blue-200",
    "Processing": "bg-violet-100 text-violet-800 border border-violet-200",
    "Result Entered": "bg-cyan-100 text-cyan-800 border border-cyan-200",
    "Verified": "bg-teal-100 text-teal-800 border border-teal-200",
    "Published": "bg-emerald-100 text-emerald-800 border border-emerald-200",
    "Cancelled": "bg-rose-100 text-rose-800 border border-rose-200",
    "Paid": "bg-emerald-100 text-emerald-800 border border-emerald-200",
    "Partial": "bg-orange-100 text-orange-800 border border-orange-200",
    "Refunded": "bg-slate-100 text-slate-600 border border-slate-200",
  };
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold tracking-wide ${map[status] || "bg-slate-100 text-slate-700 border border-slate-200"}`}>
      {status}
    </span>
  );
}

function calcAge(dob: string): number {
  const birth = new Date(dob);
  const now = new Date();
  let age = now.getFullYear() - birth.getFullYear();
  if (now < new Date(now.getFullYear(), birth.getMonth(), birth.getDate())) age--;
  return age;
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuth();

  const [order, setOrder] = useState<Order | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Payment update
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [newPaymentStatus, setNewPaymentStatus] = useState("");
  const [isUpdatingPayment, setIsUpdatingPayment] = useState(false);

  // Cancel
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);

  const canModify = user?.role === "admin" || user?.role === "reception";

  const fetchOrder = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get<Order>(`/orders/${id}`);
      setOrder(data);
    } catch (err: any) {
      setError(err.detail || "Failed to load order details.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchOrder(); }, [id]);

  const handleCancel = async () => {
    if (!order) return;
    setIsCancelling(true);
    try {
      const updated = await api.patch<Order>(`/orders/${order.id}/cancel`, {});
      setOrder(updated);
      setShowCancelModal(false);
      setSuccessMessage("Order cancelled successfully.");
    } catch (err: any) {
      setError(err.detail || "Failed to cancel order.");
      setShowCancelModal(false);
    } finally {
      setIsCancelling(false);
    }
  };

  const handlePaymentUpdate = async () => {
    if (!order || !newPaymentStatus) return;
    setIsUpdatingPayment(true);
    try {
      const updated = await api.patch<Order>(`/orders/${order.id}/payment`, { payment_status: newPaymentStatus });
      setOrder(updated);
      setShowPaymentModal(false);
      setSuccessMessage(`Payment status updated to ${newPaymentStatus}.`);
    } catch (err: any) {
      setError(err.detail || "Failed to update payment status.");
      setShowPaymentModal(false);
    } finally {
      setIsUpdatingPayment(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-full border-2 border-teal-500 border-t-transparent animate-spin" />
          <p className="text-xs text-slate-400 font-semibold">Loading order...</p>
        </div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <div className="w-12 h-12 rounded-xl bg-rose-50 text-rose-500 flex items-center justify-center">
          <AlertCircle className="w-6 h-6" />
        </div>
        <p className="text-sm font-bold text-slate-900">Order not found</p>
        <Button variant="outline" size="sm" onClick={() => router.push("/orders")}>
          Back to Orders
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5 w-full max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/orders")}
            className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-500 hover:text-slate-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">{order.order_number}</h1>
              <StatusChip status={order.status} />
              <StatusChip status={order.payment_status} />
            </div>
            <p className="text-xs text-slate-400 font-medium mt-0.5 flex items-center gap-1.5">
              <Calendar className="w-3 h-3" />
              {new Date(order.created_at).toLocaleDateString("en-IN", {
                day: "numeric", month: "long", year: "numeric",
                hour: "2-digit", minute: "2-digit"
              })}
            </p>
          </div>
        </div>

        {canModify && (
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm"
              onClick={() => { setNewPaymentStatus(order.payment_status); setShowPaymentModal(true); }}
              className="text-xs font-bold flex items-center gap-1.5">
              <CreditCard className="w-3.5 h-3.5" /> Update Payment
            </Button>
            {order.status === "Verified" && (
              <Button
                variant="primary"
                size="sm"
                onClick={async () => {
                  try {
                    const rpt = await api.post<any>(`/reports/generate/${order.id}`, {});
                    setSuccessMessage(`Report ${rpt.report_number} generated successfully!`);
                    fetchOrder();
                  } catch (err: any) {
                    setError(err.detail || "Failed to generate report.");
                  }
                }}
                className="bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs shadow-sm flex items-center gap-1.5"
              >
                <FileText className="w-3.5 h-3.5" /> Generate Report PDF
              </Button>
            )}
            {order.status === "Pending" && (
              <Button variant="danger" size="sm"
                onClick={() => setShowCancelModal(true)}
                className="text-xs font-bold flex items-center gap-1.5">
                <XCircle className="w-3.5 h-3.5" /> Cancel Order
              </Button>
            )}
          </div>
        )}
      </div>

      {successMessage && <Toast type="success" text={successMessage} onClose={() => setSuccessMessage(null)} />}
      {error && <Toast type="error" text={error} onClose={() => setError(null)} />}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Left Column: Patient + Items + Financial */}
        <div className="md:col-span-2 flex flex-col gap-5">
          {/* Patient Card */}
          {order.patient && (
            <Card className="p-0 border border-slate-200/80 shadow-sm overflow-hidden">
              <div className="flex items-center gap-2 px-5 py-3 bg-slate-50 border-b border-slate-100">
                <User2 className="w-3.5 h-3.5 text-slate-400" />
                <p className="text-xs font-bold text-slate-700 uppercase tracking-wider">Patient</p>
              </div>
              <div className="px-5 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500 to-teal-700 text-white flex items-center justify-center text-sm font-extrabold shadow-sm">
                      {order.patient.first_name.charAt(0)}{order.patient.last_name.charAt(0)}
                    </div>
                    <div>
                      <p className="text-sm font-extrabold text-slate-900">
                        {order.patient.first_name} {order.patient.last_name}
                      </p>
                      <p className="text-xs text-slate-500 font-medium mt-0.5">
                        {order.patient.patient_id} · {calcAge(order.patient.date_of_birth)} yrs · {order.patient.phone}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => router.push(`/patients/${order.patient!.id}`)}
                    className="flex items-center gap-1 text-[11px] font-bold text-teal-600 hover:text-teal-800 hover:underline"
                  >
                    View Profile <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </Card>
          )}

          {/* Tests / Line Items */}
          <Card className="p-0 border border-slate-200/80 shadow-sm overflow-hidden">
            <div className="flex items-center gap-2 px-5 py-3 bg-slate-50 border-b border-slate-100">
              <FlaskConical className="w-3.5 h-3.5 text-slate-400" />
              <p className="text-xs font-bold text-slate-700 uppercase tracking-wider">Tests Ordered ({order.items.length})</p>
            </div>
            <div className="divide-y divide-slate-50">
              {order.items.map((item) => (
                <div key={item.id} className="flex items-center justify-between px-5 py-3.5">
                  <div>
                    <p className="text-sm font-bold text-slate-900">{item.test_name_snapshot}</p>
                    <p className="text-[11px] text-slate-400 font-bold uppercase tracking-wide mt-0.5">
                      {item.test_code_snapshot} · Qty: {item.quantity}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <StatusChip status={item.status} />
                    <div className="text-right">
                      <p className="text-sm font-extrabold text-slate-900 flex items-center gap-0.5">
                        <IndianRupee className="w-3 h-3 text-slate-500" />
                        {parseFloat(item.total).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </p>
                      {parseFloat(item.unit_price) !== parseFloat(item.total) && (
                        <p className="text-[10px] text-slate-400 font-medium">
                          ₹{parseFloat(item.unit_price).toFixed(2)} × {item.quantity}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Financial Summary */}
          <Card className="p-0 border border-slate-200/80 shadow-sm overflow-hidden">
            <div className="flex items-center gap-2 px-5 py-3 bg-slate-50 border-b border-slate-100">
              <IndianRupee className="w-3.5 h-3.5 text-slate-400" />
              <p className="text-xs font-bold text-slate-700 uppercase tracking-wider">Financial Summary</p>
            </div>
            <div className="px-5 py-4 space-y-3">
              <div className="flex justify-between text-xs">
                <span className="text-slate-500 font-semibold">Subtotal</span>
                <span className="font-bold text-slate-700">₹{parseFloat(order.subtotal).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500 font-semibold">Discount</span>
                <span className="font-bold text-rose-600">
                  {parseFloat(order.discount) > 0 ? `- ₹${parseFloat(order.discount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : "₹0.00"}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500 font-semibold">Tax</span>
                <span className="font-medium text-slate-400">₹{parseFloat(order.tax).toFixed(2)}</span>
              </div>
              <div className="border-t border-slate-100 pt-3">
                <div className="flex justify-between">
                  <span className="text-sm font-extrabold text-slate-900">Total Amount</span>
                  <span className="text-base font-extrabold text-teal-700">
                    ₹{parseFloat(order.total_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </span>
                </div>
              </div>
            </div>
          </Card>

          {/* Notes */}
          {order.notes && (
            <Card className="p-4 border border-amber-100 bg-amber-50/40 shadow-sm">
              <div className="flex items-start gap-2.5">
                <ClipboardList className="w-3.5 h-3.5 text-amber-600 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-[11px] font-bold text-amber-700 uppercase tracking-wider mb-1">Notes</p>
                  <p className="text-xs text-amber-800 font-medium leading-relaxed">{order.notes}</p>
                </div>
              </div>
            </Card>
          )}
        </div>

        {/* Right Column: Audit + Future Placeholders */}
        <div className="flex flex-col gap-5">
          {/* Audit Info */}
          <Card className="p-0 border border-slate-200/80 shadow-sm overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 bg-slate-50 border-b border-slate-100">
              <Shield className="w-3.5 h-3.5 text-slate-400" />
              <p className="text-xs font-bold text-slate-700 uppercase tracking-wider">Audit</p>
            </div>
            <div className="px-4 py-4 space-y-3">
              {order.ordering_user && (
                <div>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Created By</p>
                  <p className="text-xs font-bold text-slate-800">{order.ordering_user.name}</p>
                  <p className="text-[10px] text-slate-400">{order.ordering_user.role} · {order.ordering_user.email}</p>
                </div>
              )}
              <div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Created At</p>
                <p className="text-xs font-medium text-slate-700">
                  {new Date(order.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}
                </p>
              </div>
              <div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Last Updated</p>
                <p className="text-xs font-medium text-slate-700">
                  {new Date(order.updated_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}
                </p>
              </div>
            </div>
          </Card>

          {/* Future: Sample Collection (placeholder) */}
          <Card className="p-4 border border-dashed border-slate-200 bg-slate-50/40 opacity-60">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Sample Collection</p>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">Available in Phase 4 — Sample workflow</p>
          </Card>

          {/* Future: Results (placeholder) */}
          <Card className="p-4 border border-dashed border-slate-200 bg-slate-50/40 opacity-60">
            <div className="flex items-center gap-2 mb-2">
              <FlaskConical className="w-3.5 h-3.5 text-slate-400" />
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Results</p>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">Available in Phase 5 — Result entry</p>
          </Card>

          {/* Future: Report (placeholder) */}
          <Card className="p-4 border border-dashed border-slate-200 bg-slate-50/40 opacity-60">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-slate-400" />
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Report</p>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">Available in Phase 6 — Report generation</p>
          </Card>
        </div>
      </div>

      {/* Cancel Modal */}
      {showCancelModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 p-6 w-full max-w-sm mx-4">
            <div className="w-11 h-11 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center mb-4">
              <XCircle className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-extrabold text-slate-900 mb-1">Cancel Order?</h3>
            <p className="text-xs text-slate-500 mb-5">
              Cancel order <span className="font-bold text-slate-800">{order.order_number}</span>?
              This cannot be undone.
            </p>
            <div className="flex gap-2.5">
              <Button variant="outline" size="sm" className="flex-1 text-xs font-bold"
                onClick={() => setShowCancelModal(false)} disabled={isCancelling}>
                Keep Order
              </Button>
              <Button variant="danger" size="sm" className="flex-1 text-xs font-bold"
                onClick={handleCancel} isLoading={isCancelling}>
                Cancel Order
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Payment Update Modal */}
      {showPaymentModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 p-6 w-full max-w-sm mx-4">
            <div className="w-11 h-11 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center mb-4">
              <CreditCard className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-extrabold text-slate-900 mb-4">Update Payment Status</h3>
            <div className="flex flex-col gap-2 mb-5">
              {["Pending", "Paid", "Partial", "Refunded"].map(opt => (
                <button
                  key={opt}
                  onClick={() => setNewPaymentStatus(opt)}
                  className={`px-4 py-2.5 rounded-xl border text-xs font-bold transition-all text-left ${
                    newPaymentStatus === opt
                      ? "bg-teal-50 border-teal-300 text-teal-800"
                      : "border-slate-200 text-slate-600 hover:border-slate-300"
                  }`}
                >
                  {opt}
                </button>
              ))}
            </div>
            <div className="flex gap-2.5">
              <Button variant="outline" size="sm" className="flex-1 text-xs font-bold"
                onClick={() => setShowPaymentModal(false)} disabled={isUpdatingPayment}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" className="flex-1 text-xs font-bold"
                onClick={handlePaymentUpdate} isLoading={isUpdatingPayment}>
                Update
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
