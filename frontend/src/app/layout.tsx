import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/hooks/useAuth";
import { AppLayout } from "@/components/layout/AppLayout";
import { RouteGuard } from "@/components/layout/RouteGuard";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Vyoma LabOS — Reusable Laboratory Management Platform",
  description: "Modern, multi-tenant Medical Laboratory Management System by Vyoma.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full bg-slate-50 antialiased">
      <body className={`${inter.className} min-h-full flex flex-col`}>
        <AuthProvider>
          <RouteGuard>
            <AppLayout>{children}</AppLayout>
          </RouteGuard>
        </AuthProvider>
      </body>
    </html>
  );
}
