"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import {
  Card,
  Button,
  Toast,
  Badge
} from "@/components/ui/primitives";
import {
  Zap,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Play,
  FileText,
  Clock,
  ShieldCheck,
  ExternalLink,
  RefreshCw,
  Send,
  AlertCircle
} from "lucide-react";

interface IntegrationStatus {
  is_configured: boolean;
  webhook_url: string | null;
  status: string;
  sent_count: number;
  pending_count: number;
  failed_count: number;
  last_successful_delivery: string | null;
  last_failed_delivery: string | null;
}

export default function IntegrationsSettingsPage() {
  const { user } = useAuth();
  const [statusData, setStatusData] = useState<IntegrationStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Testing connection state
  const [isTesting, setIsTesting] = useState(false);
  const [toastSuccess, setToastSuccess] = useState<string | null>(null);
  const [toastError, setToastError] = useState<string | null>(null);

  const fetchStatus = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get<IntegrationStatus>("/integrations");
      setStatusData(data);
    } catch (err: any) {
      setError(err.detail || "Failed to load integration configuration status.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleTestConnection = async () => {
    setIsTesting(true);
    setToastSuccess(null);
    setToastError(null);
    try {
      const res = await api.post<{ success: boolean; message: string }>("/integrations/n8n/test", {});
      if (res.success) {
        setToastSuccess("n8n Test Connection Succeeded! Received HTTP 2xx from webhook.");
      } else {
        setToastError(`Test Failed: ${res.message}`);
      }
      fetchStatus();
    } catch (err: any) {
      setToastError(err.detail || "Failed to connect to n8n webhook target.");
    } finally {
      setIsTesting(false);
    }
  };

  const isConnected = statusData?.status === "Connected";
  const isError = statusData?.status === "Connection Error";

  return (
    <div className="flex flex-col gap-6 w-full animate-in fade-in duration-200">
      {/* Top Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2.5">
            <Zap className="w-5 h-5 text-teal-600" />
            <span>n8n & WhatsApp Automation</span>
          </h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            Configure secure webhook integration for automated report notifications and delivery tracking.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link href="/settings/integrations/logs">
            <Button variant="outline" className="flex items-center gap-2 text-xs font-bold py-2.5 px-4">
              <FileText className="w-4 h-4 text-slate-500" />
              <span>View Delivery Logs</span>
            </Button>
          </Link>
          <Button
            variant="primary"
            onClick={handleTestConnection}
            isLoading={isTesting}
            disabled={!statusData?.is_configured}
            className="flex items-center gap-2 text-xs font-bold py-2.5 px-4 shadow-sm"
          >
            <Play className="w-4 h-4" />
            <span>Test n8n Connection</span>
          </Button>
        </div>
      </div>

      {/* Notifications */}
      {toastSuccess && (
        <Toast type="success" text={toastSuccess} onClose={() => setToastSuccess(null)} />
      )}
      {toastError && (
        <Toast type="error" text={toastError} onClose={() => setToastError(null)} />
      )}

      {/* Main Connection Status Banner */}
      <Card className="p-6 border border-slate-200/80 shadow-sm bg-white relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${
              isConnected
                ? "bg-emerald-50 text-emerald-600"
                : isError
                ? "bg-amber-50 text-amber-600"
                : "bg-slate-100 text-slate-400"
            }`}>
              {isConnected ? (
                <CheckCircle2 className="w-6 h-6" />
              ) : isError ? (
                <AlertTriangle className="w-6 h-6" />
              ) : (
                <XCircle className="w-6 h-6" />
              )}
            </div>

            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-base font-extrabold text-slate-900">n8n Webhook Integration</h2>
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold border capitalize ${
                  isConnected
                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                    : isError
                    ? "bg-amber-50 text-amber-700 border-amber-200"
                    : "bg-slate-100 text-slate-600 border-slate-200"
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? "bg-emerald-500 animate-pulse" : isError ? "bg-amber-500" : "bg-slate-400"}`} />
                  {statusData?.status || "Checking..."}
                </span>
              </div>

              <p className="text-xs text-slate-500 font-medium mt-1">
                {statusData?.is_configured
                  ? `Configured Target: ${statusData.webhook_url}`
                  : "Webhook URL not set in environment configuration (N8N_WEBHOOK_URL)."}
              </p>

              <div className="flex items-center gap-4 mt-3 text-[11px] font-semibold text-slate-400">
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  Last Successful: {statusData?.last_successful_delivery
                    ? new Date(statusData.last_successful_delivery).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
                    : "Never"}
                </span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
                  HMAC-SHA256 Signed
                </span>
              </div>
            </div>
          </div>

          <Button
            variant="outline"
            onClick={fetchStatus}
            isLoading={isLoading}
            className="flex items-center gap-2 text-xs font-semibold self-start md:self-center"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh Status</span>
          </Button>
        </div>
      </Card>

      {/* Metrics Counter Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <Card className="p-5 border border-slate-200/80 shadow-sm bg-white">
          <div className="flex items-center justify-between">
            <span className="text-xs font-extrabold uppercase tracking-wider text-slate-400">Successfully Sent</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Send className="w-4 h-4" />
            </div>
          </div>
          <span className="block text-2xl font-black text-slate-900 mt-2">{statusData?.sent_count ?? 0}</span>
          <span className="block text-[11px] text-slate-500 font-semibold mt-1">Dispatched to n8n webhook</span>
        </Card>

        <Card className="p-5 border border-slate-200/80 shadow-sm bg-white">
          <div className="flex items-center justify-between">
            <span className="text-xs font-extrabold uppercase tracking-wider text-slate-400">Pending Delivery</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <span className="block text-2xl font-black text-slate-900 mt-2">{statusData?.pending_count ?? 0}</span>
          <span className="block text-[11px] text-slate-500 font-semibold mt-1">Queued or currently retrying</span>
        </Card>

        <Card className="p-5 border border-slate-200/80 shadow-sm bg-white">
          <div className="flex items-center justify-between">
            <span className="text-xs font-extrabold uppercase tracking-wider text-slate-400">Failed Delivery</span>
            <div className="w-8 h-8 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
              <AlertCircle className="w-4 h-4" />
            </div>
          </div>
          <span className="block text-2xl font-black text-slate-900 mt-2">{statusData?.failed_count ?? 0}</span>
          <span className="block text-[11px] text-slate-500 font-semibold mt-1">Manual retry available in logs</span>
        </Card>
      </div>

      {/* Integration Architecture & Contract Guidelines */}
      <Card className="p-6 border border-slate-200/80 shadow-sm bg-white flex flex-col gap-4">
        <h3 className="text-sm font-extrabold text-slate-900 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-teal-600" />
          <span>Integration Boundary & Security Policy</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1.5">
            <span className="font-bold text-slate-800">System of Record Safety</span>
            <p className="text-slate-600 leading-relaxed font-medium">
              LabOS is the single source of clinical truth. Results, reference ranges, and verified PDF reports remain strictly inside LabOS. WhatsApp credentials and third-party delivery logic reside entirely in n8n.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1.5">
            <span className="font-bold text-slate-800">AI Safety Boundary</span>
            <p className="text-slate-600 leading-relaxed font-medium">
              AI MUST NOT approve lab results, alter flags, diagnose patients, or modify official PDF reports. AI is used solely by n8n for communication formatting with automatic template fallback.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
