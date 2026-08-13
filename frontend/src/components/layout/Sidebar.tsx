"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import {
  Activity,
  Users,
  FlaskConical,
  Layers,
  Inbox,
  CheckSquare,
  FileText,
  Calendar,
  MessageSquare,
  BarChart2,
  Settings,
  ShieldAlert,
  History,
  LogOut,
  FolderOpen,
  Zap
} from "lucide-react";

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  disabled?: boolean;
}

export const Sidebar = () => {
  const pathname = usePathname();
  const { logout, user } = useAuth();

  const coreModules: NavItem[] = [
    { name: "Dashboard", href: "/dashboard", icon: Activity },
    { name: "Patients", href: "/patients", icon: Users },
    { name: "Tests Catalog", href: "/tests", icon: FlaskConical },
    { name: "Orders Registry", href: "/orders", icon: FolderOpen },
  ];

  const labModules: NavItem[] = [
    { name: "Samples Tracker", href: "/samples", icon: Layers },
    { name: "Technician Worklist", href: "/worklist", icon: Inbox },
    { name: "Verification Queue", href: "/verification", icon: CheckSquare },
    { name: "Reports Registry", href: "/reports", icon: FileText },
  ];

  const futureModules: NavItem[] = [
    { name: "Appointments", href: "#", icon: Calendar, disabled: true },
    { name: "Communication", href: "#", icon: MessageSquare, disabled: true },
    { name: "Analytics", href: "#", icon: BarChart2, disabled: true },
  ];

  const adminModules: NavItem[] = [
    { name: "n8n Integration", href: "/settings/integrations", icon: Zap },
    { name: "Users & Roles", href: "/settings/users", icon: ShieldAlert },
    { name: "Audit Trail", href: "/audit", icon: History },
  ];


  const role = user?.role || "technician";

  // Filter core modules by role
  const filteredCore = coreModules.filter(item => {
    if (role === "admin") return true;
    if (role === "reception") {
      return ["Dashboard", "Patients", "Orders Registry"].includes(item.name);
    }
    if (role === "technician" || role === "reviewer") {
      return ["Dashboard"].includes(item.name);
    }
    return false;
  });

  // Filter lab active modules by role
  const filteredLab = labModules.filter(item => {
    if (role === "admin") return true;
    if (role === "reception") {
      return ["Samples Tracker", "Reports Registry"].includes(item.name);
    }
    if (role === "technician") {
      return ["Samples Tracker", "Technician Worklist", "Reports Registry"].includes(item.name);
    }
    if (role === "reviewer") {
      return ["Samples Tracker", "Verification Queue", "Reports Registry"].includes(item.name);
    }
    return false;
  });

  const renderNavList = (items: NavItem[]) => {
    return items.map((item, index) => {
      const isActive = pathname.startsWith(item.href) && item.href !== "#";
      const Icon = item.icon;

      if (item.disabled) {
        return (
          <div
            key={index}
            className="flex items-center justify-between px-3.5 py-2.5 text-xs font-semibold text-slate-400 cursor-not-allowed select-none rounded-lg"
          >
            <div className="flex items-center gap-3">
              <Icon className="w-4 h-4" />
              <span>{item.name}</span>
            </div>
            <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-slate-100/80 text-slate-400">
              Soon
            </span>
          </div>
        );
      }

      return (
        <Link
          key={index}
          href={item.href}
          className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-semibold transition-all duration-150
            ${
              isActive
                ? "bg-teal-50 text-teal-700 shadow-sm border border-teal-100/50"
                : "text-slate-600 hover:bg-slate-50 hover:text-slate-900 border border-transparent"
            }`}
        >
          <Icon className="w-4 h-4" />
          <span>{item.name}</span>
        </Link>
      );
    });
  };

  return (
    <aside className="w-64 bg-white border-r border-slate-200/80 flex flex-col h-screen select-none">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-slate-100 gap-3 bg-slate-50/50">
        <div className="w-8 h-8 rounded-lg bg-teal-600 flex items-center justify-center text-white font-black text-sm shadow-md">
          L
        </div>
        <div>
          <span className="font-extrabold text-sm text-slate-900 tracking-tight">Vyoma LabOS</span>
          <span className="block text-[10px] text-slate-400 font-bold uppercase tracking-wider mt-0.5">
            Core Operations
          </span>
        </div>
      </div>

      {/* Nav Link Areas */}
      <div className="flex-1 overflow-y-auto px-4 py-6 flex flex-col gap-7">
        {/* Core Modules */}
        {filteredCore.length > 0 && (
          <div>
            <span className="block text-[10px] uppercase tracking-wider font-extrabold text-slate-400 px-3.5 mb-2.5">
              Core Registry
            </span>
            <nav className="flex flex-col gap-1">{renderNavList(filteredCore)}</nav>
          </div>
        )}

        {/* Lab Operations Modules */}
        {filteredLab.length > 0 && (
          <div>
            <span className="block text-[10px] uppercase tracking-wider font-extrabold text-slate-400 px-3.5 mb-2.5">
              Lab Operations
            </span>
            <nav className="flex flex-col gap-1">{renderNavList(filteredLab)}</nav>
          </div>
        )}

        {/* Future Modules */}
        {futureModules.length > 0 && (
          <div>
            <span className="block text-[10px] uppercase tracking-wider font-extrabold text-slate-400 px-3.5 mb-2.5">
              Future Modules
            </span>
            <nav className="flex flex-col gap-1">{renderNavList(futureModules)}</nav>
          </div>
        )}

        {/* Admin Configuration */}
        {user?.role === "admin" && (
          <div>
            <span className="block text-[10px] uppercase tracking-wider font-extrabold text-slate-400 px-3.5 mb-2.5">
              Administration
            </span>
            <nav className="flex flex-col gap-1">{renderNavList(adminModules)}</nav>
          </div>
        )}
      </div>

      {/* User Session Footer */}
      <div className="p-4 border-t border-slate-100 flex flex-col gap-2">
        <div className="flex items-center gap-3 px-2 py-1">
          <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center font-bold text-slate-700 text-xs">
            {user?.name.charAt(0)}
          </div>
          <div className="flex-1 min-w-0">
            <span className="block text-xs font-bold text-slate-800 truncate">{user?.name}</span>
            <span className="block text-[10px] text-slate-500 uppercase font-bold tracking-wider mt-0.5">
              {user?.role}
            </span>
          </div>
        </div>
        <button
          onClick={logout}
          className="flex items-center justify-center gap-2 w-full mt-2 px-3 py-2 text-xs font-semibold text-slate-600 hover:text-red-700 hover:bg-red-50 border border-slate-200 hover:border-red-200 rounded-lg transition-all"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
};
