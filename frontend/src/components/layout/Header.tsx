"use client";

import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { Building2, ChevronRight, Bell, Calendar } from "lucide-react";
import { useEffect, useState } from "react";

export const Header = () => {
  const pathname = usePathname();
  const { user } = useAuth();
  const [currentDateStr, setCurrentDateStr] = useState("");

  useEffect(() => {
    const today = new Date();
    setCurrentDateStr(
      today.toLocaleDateString("en-US", {
        weekday: "short",
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    );
  }, []);

  // Compute breadcrumbs from path
  const pathSegments = pathname.split("/").filter((p) => p !== "");
  const pageTitle = pathSegments.length > 0
    ? pathSegments[pathSegments.length - 1].charAt(0).toUpperCase() + pathSegments[pathSegments.length - 1].slice(1)
    : "Dashboard";

  return (
    <header className="h-16 border-b border-slate-200/80 bg-white px-6 flex items-center justify-between select-none">
      {/* Breadcrumbs / Page context */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold text-slate-400">LabOS</span>
        {pathSegments.map((seg, idx) => (
          <div key={idx} className="flex items-center gap-2">
            <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
            <span
              className={`text-xs font-semibold uppercase tracking-wider ${
                idx === pathSegments.length - 1 ? "text-slate-700" : "text-slate-400"
              }`}
            >
              {seg}
            </span>
          </div>
        ))}
      </div>

      {/* Header Context / Org and Time */}
      <div className="flex items-center gap-6">
        {/* Date display */}
        <div className="hidden md:flex items-center gap-2 text-xs font-semibold text-slate-500 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-100">
          <Calendar className="w-3.5 h-3.5 text-slate-400" />
          <span>{currentDateStr}</span>
        </div>

        {/* Tenant/Organization Selector */}
        <div className="flex items-center gap-2.5 text-slate-700 bg-teal-50/50 hover:bg-teal-50 border border-teal-100/60 px-3 py-1.5 rounded-lg transition-colors cursor-pointer">
          <Building2 className="w-4 h-4 text-teal-600" />
          <div className="text-left">
            <span className="block text-[9px] uppercase font-black text-teal-700/85 tracking-wide leading-none">
              Active Tenant
            </span>
            <span className="block text-xs font-bold text-slate-800 leading-tight mt-0.5">
              Vyoma Diagnostics
            </span>
          </div>
        </div>

        {/* Notification bell stub */}
        <button className="relative text-slate-400 hover:text-slate-600 p-1.5 hover:bg-slate-50 rounded-lg transition-all">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-teal-500 rounded-full"></span>
        </button>
      </div>
    </header>
  );
};
