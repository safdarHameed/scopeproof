"use client";

import { FileText, FolderPlus, Plus } from "lucide-react";
import Link from "next/link";

import { ProjectStatusBadge } from "@/components/projects/project-status";
import { Alert } from "@/components/ui/alert";
import { ButtonLink } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/card";
import { PageSpinner } from "@/components/ui/spinner";
import { projectsApi } from "@/lib/api";
import { formatDate, formatMoney, plural } from "@/lib/format";
import { useResource } from "@/lib/use-resource";
import { useAuth } from "@/providers/auth-provider";

export default function DashboardPage() {
  const { user } = useAuth();
  const name = user?.full_name?.split(" ")[0];
  const { data: projects, error, loading } = useResource("projects", projectsApi.list);
  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            {name ? `Welcome, ${name}` : "Welcome"}
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Each project holds one client&apos;s contract and conversation, and the invoice built from
            them.
          </p>
        </div>
        {projects && projects.length > 0 && (
          <ButtonLink href="/projects/new">
            <Plus className="size-4" /> New project
          </ButtonLink>
        )}
      </div>

      {error && (
        <Alert kind="error" className="mt-6">
          {error}
        </Alert>
      )}

      <div className="mt-8">
        {loading ? (
          <PageSpinner />
        ) : !projects || projects.length === 0 ? (
          <EmptyState
            icon={FolderPlus}
            title="No projects yet"
            action={
              <ButtonLink href="/projects/new">
                <Plus className="size-4" /> New project
              </ButtonLink>
            }
          >
            Create a project for a client, upload the contract and emails, and ScopeProof will
            suggest invoice items backed by quotes.
          </EmptyState>
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((p) => (
              <li key={p.id}>
                <Link
                  href={`/projects/${p.id}`}
                  className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 hover:shadow-md"
                >
                  <div className="flex items-start justify-between gap-3">
                    <h2 className="font-semibold text-slate-900">{p.name}</h2>
                    <ProjectStatusBadge project={p} />
                  </div>
                  <p className="mt-1 text-sm text-slate-600">
                    {p.client_name}
                    {p.client_company && ` · ${p.client_company}`}
                  </p>
                  <div className="mt-auto flex items-end justify-between gap-3 pt-6 text-xs text-slate-500">
                    <span className="flex items-center gap-1.5">
                      <FileText className="size-3.5" />
                      {plural(p.stats.document_count, "document")} · {formatDate(p.created_at)}
                    </span>
                    {p.stats.approved_total > 0 && (
                      <span className="font-mono text-sm text-slate-900">
                        {formatMoney(p.stats.approved_total, p.currency)}
                      </span>
                    )}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
