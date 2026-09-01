"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import { api } from "@/lib/api";

interface User {
  id: number;
  organization_id: number;
  branch_id: number | null;
  name: string;
  email: string;
  role: string;
  status: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Load session from localStorage on mount
    const storedToken = localStorage.getItem("labos_token");
    const storedUser = localStorage.getItem("labos_user");

    if (storedToken && storedUser) {
      setToken(storedToken);
      try {
        setUser(JSON.parse(storedUser));
      } catch {
        // Parse error, clear storage
        localStorage.removeItem("labos_token");
        localStorage.removeItem("labos_user");
      }
    }

    setIsLoading(false);
  }, []);

  useEffect(() => {
    // Route guard
    if (!isLoading) {
      const isLoginPage = pathname === "/login";
      const isPublicPage = isLoginPage || pathname.startsWith("/verify/");
      if (!token && !isPublicPage) {
        router.replace("/login");
      } else if (token && isLoginPage) {
        router.replace("/dashboard");
      }
    }
  }, [token, isLoading, pathname, router]);

  const login = async (email: string, password: string) => {
    const res = await api.post<{ access_token: string; token_type: string; user: User }>(
      "/auth/login",
      { email, password }
    );

    localStorage.setItem("labos_token", res.access_token);
    localStorage.setItem("labos_user", JSON.stringify(res.user));
    setToken(res.access_token);
    setUser(res.user);

    router.push("/dashboard");
  };

  const logout = () => {
    localStorage.removeItem("labos_token");
    localStorage.removeItem("labos_user");
    setToken(null);
    setUser(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
