"use client";

/**
 * Verification Badge
 * -------------------
 * Self-contained module: fetches the report's verification link and shows
 * the same QR code that's embedded server-side in the PDF (see
 * pdf_generator.py). Drop into any page with:
 *
 *   <VerificationBadge reportId={report.id} />
 */

import { useEffect, useState } from "react";
import { Card, Button } from "@/components/ui/primitives";
import { ShieldCheck, Copy, Check, ExternalLink } from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface ReportMeta {
  verification_url: string | null;
  verification_code: string | null;
}

export function VerificationBadge({ reportId }: { reportId: number | string }) {
  const [meta, setMeta] = useState<ReportMeta | null>(null);
  const [copied, setCopied] = useState(false);
  const [qrSrc, setQrSrc] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    const token = typeof window !== "undefined" ? localStorage.getItem("labos_token") : null;

    (async () => {
      try {
        const metaRes = await fetch(`${API_BASE_URL}/reports/${reportId}/metadata`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (metaRes.ok) setMeta(await metaRes.json());

        const qrRes = await fetch(`${API_BASE_URL}/reports/${reportId}/verification-qr`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (qrRes.ok) {
          const blob = await qrRes.blob();
          objectUrl = URL.createObjectURL(blob);
          setQrSrc(objectUrl);
        }
      } catch {
        // Silent — badge simply won't render if the report has no token yet
      }
    })();

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [reportId]);

  if (!meta?.verification_url) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(meta.verification_url!);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // clipboard unavailable — no-op
    }
  };

  return (
    <Card title="Authenticity Verification" subtitle="Public QR embedded on this report's PDF">
      <div className="flex items-center gap-5">
        <div className="w-24 h-24 rounded-lg border border-slate-200 bg-white p-1.5 flex-shrink-0 flex items-center justify-center">
          {qrSrc ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={qrSrc} alt="Report verification QR code" className="w-full h-full" />
          ) : (
            <div className="w-5 h-5 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />
          )}
        </div>
        <div className="flex-1 min-w-0 flex flex-col gap-2">
          <div className="flex items-center gap-1.5 text-teal-700">
            <ShieldCheck className="w-4 h-4" />
            <span className="text-xs font-extrabold uppercase tracking-wide">Verifiable Report</span>
          </div>
          {meta.verification_code && (
            <span className="font-mono text-[11px] font-bold text-slate-500">
              Code: {meta.verification_code}
            </span>
          )}
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleCopy}>
              {copied ? <Check className="w-3.5 h-3.5 mr-1.5" /> : <Copy className="w-3.5 h-3.5 mr-1.5" />}
              {copied ? "Copied" : "Copy Link"}
            </Button>
            <a href={meta.verification_url} target="_blank" rel="noopener noreferrer">
              <Button variant="ghost" size="sm">
                <ExternalLink className="w-3.5 h-3.5 mr-1.5" /> Open
              </Button>
            </a>
          </div>
        </div>
      </div>
    </Card>
  );
}

export default VerificationBadge;
