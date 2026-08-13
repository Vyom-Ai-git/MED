"use client";

import React from "react";
import { useAuth } from "@/hooks/useAuth";
import { usePathname } from "next/navigation";
import { ShieldX } from "lucide-react";
import { Button } from "../ui/primitives";

// Access permissions mapping paths to allowed role keys
const ROUTE_PERMISSIONS: Record<string, string[]> = {
  "/settings/users": ["admin"],
  "/patients": ["admin", "reception"],
  "/tests": ["admin"],
  "/orders": ["admin", "reception"],
};

export const RouteGuard = ({ children }: { children: React.ReactNode }) => {
  const { user, isLoading } = useAuth();
  const pathname = usePathname();

  if (isLoading) {
    return null; // AppLayout handles global spinner
  }

  // Bypass checks for login page
  if (pathname === "/login") {
    return <>{children}</>;
  }

  const userRole = user?.role || "technician";

  // Check if route matches any restricted paths
  const matchingRoute = Object.keys(ROUTE_PERMISSIONS).find(
    (route) => pathname.startsWith(route)
  );

  if (matchingRoute) {
    const allowedRoles = ROUTE_PERMISSIONS[matchingRoute];
    if (!allowedRoles.includes(userRole)) {
      return (
        <div className="flex flex-col items-center justify-center py-20 text-center select-none max-w-lg mx-auto w-full px-4 animate-in fade-in duration-200">
          <div className="w-16 h-16 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center mb-6 shadow-md shadow-rose-100 border border-rose-100/50">
            <ShieldX className="w-8 h-8" />
          </div>
          <h2 className="text-lg font-black text-slate-900 tracking-tight">Access Restricted</h2>
          <p className="text-sm text-slate-500 font-medium mt-2 leading-relaxed">
            You do not have permission to access this section. Please verify your credentials or contact your laboratory administrator.
          </p>
          <Button
            variant="secondary"
            onClick={() => (window.location.href = "/dashboard")}
            className="mt-6 font-bold shadow-sm"
          >
            Return to Dashboard
          </Button>
        </div>
      );
    }
  }

  return <>{children}</>;
};
export default RouteGuard;
