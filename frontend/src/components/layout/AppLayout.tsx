"use client";

import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { useAuth } from "@/hooks/useAuth";
import { usePathname } from "next/navigation";

export const AppLayout = ({ children }: { children: React.ReactNode }) => {
  const { token, isLoading } = useAuth();
  const pathname = usePathname();

  const isLoginPage = pathname === "/login";
  const isPublicPage = isLoginPage || pathname.startsWith("/verify/");

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-teal-500 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-xs font-semibold text-slate-500">Securing session...</span>
        </div>
      </div>
    );
  }

  // Login and public verification pages don't show sidebar or header
  if (isPublicPage) {
    return <>{children}</>;
  }

  // If not logged in, display blank during redirect
  if (!token) {
    return null;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      {/* Sidebar navigation */}
      <Sidebar />

      {/* Content wrapper */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Top bar */}
        <Header />

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          <div className="max-w-7xl mx-auto w-full flex flex-col gap-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};
export default AppLayout;
