"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { authApi } from "@/lib/api";
import { tokenStore } from "@/lib/token";
import type { RegisterPayload, User } from "@/types/auth";

type Status = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  user: User | null;
  status: Status;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterPayload) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<Status>("loading");

  // Restore the session from a stored token on first load.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const current = tokenStore.get() ? await authApi.me().catch(() => null) : null;
      if (cancelled) return;
      if (!current) tokenStore.clear();
      setUser(current);
      setStatus(current ? "authenticated" : "unauthenticated");
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await authApi.login(email, password);
    tokenStore.set(access_token);
    setUser(await authApi.me());
    setStatus("authenticated");
  }, []);

  const register = useCallback(
    async (data: RegisterPayload) => {
      await authApi.register(data);
      await login(data.email, data.password);
    },
    [login],
  );

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  return (
    <AuthContext.Provider value={{ user, status, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
