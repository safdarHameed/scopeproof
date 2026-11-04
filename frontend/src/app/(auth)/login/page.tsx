import type { Metadata } from "next";

import { AuthCard } from "@/components/auth/auth-card";
import { LoginForm } from "@/components/auth/login-form";

export const metadata: Metadata = { title: "Log in | ScopeProof" };

export default function LoginPage() {
  return (
    <AuthCard
      title="Welcome back"
      subtitle="Log in to your ScopeProof account."
      footer={{ text: "New to ScopeProof?", linkLabel: "Create an account", href: "/register" }}
    >
      <LoginForm />
    </AuthCard>
  );
}
