"use client";

import { FolderPlus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/providers/auth-provider";

export default function DashboardPage() {
  const { user } = useAuth();
  const name = user?.full_name?.split(" ")[0];

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
        {name ? `Welcome, ${name}` : "Welcome"}
      </h1>
      <p className="mt-1 text-sm text-slate-600">
        {user?.company_name ?? "Your workspace"}: projects, documents and invoices will appear here.
      </p>

      <div className="mt-10 rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center">
        <FolderPlus className="mx-auto size-10 text-slate-400" />
        <h2 className="mt-4 font-semibold text-slate-900">No projects yet</h2>
        <p className="mx-auto mt-1 max-w-sm text-sm text-slate-600">
          Projects hold a contract and its paper trail. Creating projects is coming soon.
        </p>
        <Button className="mt-6" disabled>
          New project
        </Button>
      </div>
    </div>
  );
}
