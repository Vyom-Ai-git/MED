"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { Button, Card, Badge, Toast } from "@/components/ui/primitives";
import {
  Plus, Search, Filter, FlaskConical, Calendar, ChevronLeft, ChevronRight,
  Eye, XCircle, RefreshCw, IndianRupee, User2, ClipboardList
} from "lucide-react";

interface PatientSummary {
  id: number;
  patient_id: string;
  first_name: string;
  last_name: string;
  phone: string;
}

interface OrderItem {
  id: number;
  test_name_snapshot: string;
  test_code_snapshot: string;
  unit_price: string;
  quantity: number;
  total: string;
  status: string;
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
  patient?: PatientSummary;
  ordering_user?: { id: number; name: string; email: string; role: string };
  items: OrderItem[];
}

interface OrderListResponse {
  items: Order[];
  total: number;
  page: number;
  page_size: number;
}

const STATUS_OPTIONS = ["", "Pending", "Sample Collected", "Processing", "Result Entered", "Verified", "Published", "Cancelled"];
const PAYMENT_OPTIONS = ["", "Pending", "Paid", "Partial", "Refunded"];

function StatusBadge({ status }: { status: string }) {
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
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold tracking-wide ${map[status] || "bg-slate-100 text-slate-700 border border-slate-200"}`}>
      {status}
    </span>
  );
}

export default function OrdersPage() {
  const router = useRouter();
  const { user } = useAuth();

  const [orderList, setOrderList] = useState<OrderListResponse>({ items: [], total: 0, page: 1, page_size: 10 });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [paymentFilter, setPaymentFilter] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Cancel confirm state
  const [cancelTarget, setCancelTarget] = useState<Order | null>(null);
  const [isCancelling, setIsCancelling] = useState(false);

  const canCreateOrder = user?.role === "admin" || user?.role === "reception";
  const canCancelOrder = user?.role === "admin" || user?.role === "reception";

  const fetchOrders = useCallback(async (page = currentPage, q = searchQuery, status = statusFilter, payment = paymentFilter) => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
      });
      if (q) params.set("q", q);
      if (status) params.set("status", status);
      if (payment) params.set("payment_status", payment);

      const data = await api.get<OrderListResponse>(`/orders?${params}`);
      setOrderList(data);
    } catch (err: any) {
      setError(err.detail || "Failed to load orders.");
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, searchQuery, statusFilter, paymentFilter]);

  useEffect(() => {
    fetchOrders(currentPage, searchQuery, statusFilter, paymentFilter);
  }, [currentPage]);

  // Debounced search
  useEffect(() => {
    const t = setTimeout(() => {
      setCurrentPage(1);
      fetchOrders(1, searchQuery, statusFilter, paymentFilter);
    }, 400);
    return () => clearTimeout(t);
  }, [searchQuery, statusFilter, paymentFilter]);

  const handleCancel = async () => {
    if (!cancelTarget) return;
    setIsCancelling(true);
    try {
      await api.patch(`/orders/${cancelTarget.id}/cancel`, {});
      setSuccessMessage(`Order ${cancelTarget.order_number} cancelled.`);
      setCancelTarget(null);
      fetchOrders(currentPage, searchQuery, statusFilter, paymentFilter);
    } catch (err: any) {
      setError(err.detail || "Failed to cancel order.");
      setCancelTarget(null);
    } finally {
      setIsCancelling(false);
    }
  };

  const totalPages = Math.ceil(orderList.total / pageSize);

  return (
    <div className="flex flex-col gap-6 w-full">
      {/* Page Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">Orders</h1>
          <p className="text-xs text-slate-500 font-medium mt-1">
            Manage laboratory test orders — {orderList.total} total order{orderList.total !== 1 ? "s" : ""}
          </p>
        </div>
        {canCreateOrder && (
          <Button
            variant="primary"
            onClick={() => router.push("/orders/new")}
            className="flex items-center gap-2 text-xs font-bold py-2.5 px-4 shadow-sm"
          >
            <Plus className="w-4 h-4" />
            <span>New Order</span>
          </Button>
        )}
      </div>

      {/* Notifications */}
      {successMessage && <Toast type="success" text={successMessage} onClose={() => setSuccessMessage(null)} />}
      {error && <Toast type="error" text={error} onClose={() => setError(null)} />}

      {/* Filter Bar */}
      <Card className="p-4 border border-slate-200/80 shadow-sm">
        <div className="flex flex-wrap gap-3 items-center">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search order, patient, phone..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3.5 py-2 text-xs font-medium rounded-lg border border-slate-200 bg-white text-slate-900 outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-colors"
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs font-semibold rounded-lg border border-slate-200 bg-white text-slate-700 outline-none px-3 py-2 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-colors"
            >
              {STATUS_OPTIONS.map(s => (
                <option key={s} value={s}>{s || "All Statuses"}</option>
              ))}
            </select>
          </div>

          {/* Payment Filter */}
          <select
            value={paymentFilter}
            onChange={(e) => setPaymentFilter(e.target.value)}
            className="text-xs font-semibold rounded-lg border border-slate-200 bg-white text-slate-700 outline-none px-3 py-2 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-colors"
          >
            {PAYMENT_OPTIONS.map(p => (
              <option key={p} value={p}>{p || "All Payments"}</option>
            ))}
          </select>

          <button
            onClick={() => fetchOrders(currentPage, searchQuery, statusFilter, paymentFilter)}
            className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-500 hover:text-slate-700 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </Card>

      {/* Orders Table */}
      <Card className="p-0 border border-slate-200/80 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-40">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 rounded-full border-2 border-teal-500 border-t-transparent animate-spin" />
              <p className="text-xs text-slate-400 font-semibold">Loading orders...</p>
            </div>
          </div>
        ) : orderList.items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 gap-3">
            <div className="w-12 h-12 rounded-xl bg-teal-50 text-teal-500 flex items-center justify-center">
              <ClipboardList className="w-6 h-6" />
            </div>
            <div className="text-center">
              <p className="text-sm font-bold text-slate-900">No orders found</p>
              <p className="text-xs text-slate-500 mt-1">
                {searchQuery || statusFilter || paymentFilter
                  ? "Try adjusting your search or filters."
                  : "Create the first laboratory order to get started."}
              </p>
            </div>
            {canCreateOrder && !searchQuery && !statusFilter && !paymentFilter && (
              <Button variant="primary" size="sm" onClick={() => router.push("/orders/new")}
                className="flex items-center gap-1.5 text-xs font-bold">
                <Plus className="w-3.5 h-3.5" /> New Order
              </Button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/80">
                  {["Order Number", "Patient", "Tests", "Date", "Amount", "Payment", "Status", "Created By", "Actions"].map(h => (
                    <th key={h} className="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider text-[10px]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {orderList.items.map((order) => (
                  <tr key={order.id} className="hover:bg-slate-50/60 transition-colors group">
                    {/* Order Number */}
                    <td className="px-4 py-3.5">
                      <button
                        onClick={() => router.push(`/orders/${order.id}`)}
                        className="font-extrabold text-teal-700 hover:text-teal-900 hover:underline tracking-wide"
                      >
                        {order.order_number}
                      </button>
                    </td>

                    {/* Patient */}
                    <td className="px-4 py-3.5">
                      {order.patient ? (
                        <div>
                          <p className="font-bold text-slate-900">
                            {order.patient.first_name} {order.patient.last_name}
                          </p>
                          <p className="text-[10px] text-slate-400 font-medium">{order.patient.patient_id}</p>
                        </div>
                      ) : <span className="text-slate-400">—</span>}
                    </td>

                    {/* Tests */}
                    <td className="px-4 py-3.5">
                      <div className="flex flex-wrap gap-1">
                        {order.items.slice(0, 3).map(item => (
                          <span key={item.id}
                            className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600">
                            {item.test_code_snapshot}
                          </span>
                        ))}
                        {order.items.length > 3 && (
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-500">
                            +{order.items.length - 3}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Date */}
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-1 text-slate-500">
                        <Calendar className="w-3 h-3 text-slate-400" />
                        <span className="font-medium">
                          {new Date(order.created_at).toLocaleDateString("en-IN", {
                            day: "2-digit", month: "short", year: "numeric"
                          })}
                        </span>
                      </div>
                    </td>

                    {/* Amount */}
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-0.5 font-bold text-slate-900">
                        <IndianRupee className="w-3 h-3 text-slate-500" />
                        {parseFloat(order.total_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </div>
                    </td>

                    {/* Payment */}
                    <td className="px-4 py-3.5"><StatusBadge status={order.payment_status} /></td>

                    {/* Status */}
                    <td className="px-4 py-3.5"><StatusBadge status={order.status} /></td>

                    {/* Created By */}
                    <td className="px-4 py-3.5">
                      {order.ordering_user ? (
                        <div className="flex items-center gap-1.5">
                          <User2 className="w-3 h-3 text-slate-400" />
                          <span className="text-slate-600 font-medium">{order.ordering_user.name}</span>
                        </div>
                      ) : <span className="text-slate-400">—</span>}
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => router.push(`/orders/${order.id}`)}
                          className="flex items-center gap-1 text-[10px] font-bold text-teal-600 hover:text-teal-700 hover:underline"
                        >
                          <Eye className="w-3.5 h-3.5" /> View
                        </button>
                        {canCancelOrder && order.status === "Pending" && (
                          <button
                            onClick={() => setCancelTarget(order)}
                            className="flex items-center gap-1 text-[10px] font-bold text-rose-500 hover:text-rose-700 hover:underline"
                          >
                            <XCircle className="w-3.5 h-3.5" /> Cancel
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 bg-slate-50/50">
            <span className="text-[11px] text-slate-500 font-medium">
              Showing {((currentPage - 1) * pageSize) + 1}–{Math.min(currentPage * pageSize, orderList.total)} of {orderList.total}
            </span>
            <div className="flex items-center gap-1.5">
              <button
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage(p => p - 1)}
                className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-3.5 h-3.5 text-slate-600" />
              </button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
                <button
                  key={p}
                  onClick={() => setCurrentPage(p)}
                  className={`w-7 h-7 rounded-lg text-[11px] font-bold transition-all ${
                    p === currentPage
                      ? "bg-teal-600 text-white shadow-sm"
                      : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {p}
                </button>
              ))}
              <button
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage(p => p + 1)}
                className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
              </button>
            </div>
          </div>
        )}
      </Card>

      {/* Cancel Confirm Dialog */}
      {cancelTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 p-6 w-full max-w-sm mx-4">
            <div className="w-11 h-11 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center mb-4">
              <XCircle className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-extrabold text-slate-900 mb-1">Cancel Order?</h3>
            <p className="text-xs text-slate-500 mb-5">
              Cancel <span className="font-bold text-slate-800">{cancelTarget.order_number}</span> for{" "}
              {cancelTarget.patient?.first_name} {cancelTarget.patient?.last_name}?
              This action cannot be undone.
            </p>
            <div className="flex gap-2.5">
              <Button variant="outline" size="sm" className="flex-1 font-bold text-xs"
                onClick={() => setCancelTarget(null)} disabled={isCancelling}>
                Keep Order
              </Button>
              <Button variant="danger" size="sm" className="flex-1 font-bold text-xs"
                onClick={handleCancel} isLoading={isCancelling}>
                Cancel Order
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
