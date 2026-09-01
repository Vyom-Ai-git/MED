"use client";

import React, { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { Input, Button, Card, Toast } from "@/components/ui/primitives";
import { Lock, Mail, Activity } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError("Please fill in all fields.");
      return;
    }
    
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.detail || "Authentication failed. Please verify credentials.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50/50 px-4 py-12 relative overflow-hidden select-none">
      {/* Abstract Design Background Blurs */}
      <div className="absolute top-0 left-0 w-80 h-80 bg-teal-200/30 rounded-full filter blur-3xl -translate-x-1/2 -translate-y-1/2 pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-indigo-200/20 rounded-full filter blur-3xl translate-x-1/3 translate-y-1/3 pointer-events-none" />

      <div className="w-full max-w-md z-10">
        <Card className="shadow-xl/60 border border-slate-200/60 bg-white/95 backdrop-blur-md">
          {/* Header */}
          <div className="flex flex-col items-center text-center mb-8">
            <div className="w-12 h-12 rounded-xl bg-teal-600 flex items-center justify-center text-white shadow-lg mb-4">
              <Activity className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-black text-slate-900 tracking-tight">Vyoma LabOS</h2>
            <p className="text-xs text-slate-500 font-medium mt-1">
              Enter credentials to access the laboratory workspace
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <Input
              label="Email Address"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. admin@vyoma.com"
              icon={<Mail className="w-4 h-4" />}
              autoComplete="email"
              required
            />
            
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              icon={<Lock className="w-4 h-4" />}
              autoComplete="current-password"
              required
            />

            {/* Error Message Toast */}
            {error && (
              <div className="mt-2">
                <Toast type="error" text={error} onClose={() => setError(null)} />
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              className="w-full py-3 mt-2 shadow-md shadow-teal-600/10"
              isLoading={isSubmitting}
            >
              Sign In
            </Button>
          </form>

          {/* Helper Credentials Hint */}
          <div className="mt-6 pt-5 border-t border-slate-100 text-center">
            <span className="block text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-2">
              Seeded Development Accounts
            </span>
            <div className="flex flex-col gap-1 text-[11px] text-slate-500 font-medium bg-slate-50 py-2.5 px-3 rounded-lg border border-slate-100">
              <div className="flex justify-between">
                <span>Admin: <code className="text-slate-800 font-semibold">admin@vyoma.com</code></span>
                <span>pw: <code className="text-slate-800 font-semibold">admin123</code></span>
              </div>
              <div className="flex justify-between">
                <span>Technician: <code className="text-slate-800 font-semibold">tech@vyoma.com</code></span>
                <span>pw: <code className="text-slate-800 font-semibold">tech123</code></span>
              </div>
              <div className="flex justify-between">
                <span>Reviewer: <code className="text-slate-800 font-semibold">reviewer@vyoma.com</code></span>
                <span>pw: <code className="text-slate-800 font-semibold">reviewer123</code></span>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
