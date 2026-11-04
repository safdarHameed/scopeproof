import type { Metadata } from "next";

import { AuthCard } from "@/components/auth/auth-card";
import { RegisterForm } from "@/components/auth/register-form";

export const metadata: Metadata = { title: "Create account | ScopeProof" };

export default function RegisterPage() {
  return (
    <AuthCard
      title="Create your account"
      subtitle="Start turning agreements into accurate invoices."
      footer={{ text: "Already have an account?", linkLabel: "Log in", href: "/login" }}
    >
      <RegisterForm />
    </AuthCard>
  );
}
