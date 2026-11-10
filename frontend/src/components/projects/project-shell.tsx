"use client";

import { ArrowLeft, Check, Pencil, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { ProjectContext } from "@/components/projects/project-context";
import { ProjectForm } from "@/components/projects/project-form";
import { ProjectStatusBadge } from "@/components/projects/project-status";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { PageSpinner } from "@/components/ui/spinner";
import { cn } from "@/lib/cn";
import { errorMessage, projectsApi } from "@/lib/api";
import { plural } from "@/lib/format";
import { useResource } from "@/lib/use-resource";
import type { Project } from "@/types/api";

export function ProjectShell({ children }: { children: React.ReactNode }) {
  const { id } = useParams<{ id: string }>();
  const { data: project, error, loading, reload, setData } = useResource(`project:${id}`, () =>
    projectsApi.get(id),
  );

  if (loading) return <PageSpinner />;
  if (!project) {
    return (
      <Alert
        kind="error"
        title="Couldn't open this project"
        action={
          <Link href="/dashboard" className="font-medium underline">
            Back to projects
          </Link>
        }
      >
        {error}
      </Alert>
    );
  }

  return (
    <ProjectContext.Provider value={{ project, refreshProject: reload }}>
      <ProjectHeader project={project} onUpdated={setData} />
      <StepNav project={project} />
      <div className="mt-8">{children}</div>
    </ProjectContext.Provider>
  );
}

function ProjectHeader({
  project,
  onUpdated,
}: {
  project: Project;
  onUpdated: (p: Project) => void;
}) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function remove() {
    setPending(true);
    try {
      await projectsApi.remove(project.id);
      router.push("/dashboard");
    } catch (err) {
      setDeleteError(errorMessage(err));
      setPending(false);
    }
  }

  return (
    <div>
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900"
      >
        <ArrowLeft className="size-4" /> Projects
      </Link>
      <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{project.name}</h1>
            <ProjectStatusBadge project={project} />
          </div>
          <p className="mt-1 text-sm text-slate-600">
            {project.client_name}
            {project.client_company && `, ${project.client_company}`} · {project.client_email} ·{" "}
            {project.currency}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
            <Pencil className="size-3.5" /> Edit details
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setDeleting(true)}
            aria-label="Delete project"
          >
            <Trash2 className="size-4" />
          </Button>
        </div>
      </div>

      <Dialog
        open={editing}
        onClose={() => setEditing(false)}
        title="Project and client details"
        className="max-w-2xl"
      >
        <ProjectForm
          initial={project}
          submitLabel="Save changes"
          onCancel={() => setEditing(false)}
          onSubmit={async (data) => {
            onUpdated(await projectsApi.update(project.id, data));
            setEditing(false);
          }}
        />
      </Dialog>

      <Dialog
        open={deleting}
        onClose={() => setDeleting(false)}
        title="Delete this project?"
        description="All uploaded documents, suggested items and invoices in this project will be deleted. This can't be undone."
      >
        {deleteError && <Alert kind="error" className="mb-4">{deleteError}</Alert>}
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setDeleting(false)}>
            Cancel
          </Button>
          <Button className="bg-red-600 hover:bg-red-700" onClick={remove} disabled={pending}>
            {pending ? "Deleting…" : "Delete project"}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}

function StepNav({ project }: { project: Project }) {
  const pathname = usePathname();
  const base = `/projects/${project.id}`;
  const s = project.stats;
  const invoiceDone = s.invoice_status !== null;
  const reviewDone = s.item_count > 0 && s.pending_count === 0;

  const steps = [
    {
      href: base,
      label: "Documents",
      hint: s.document_count ? plural(s.document_count, "file") : "Upload contract & emails",
      done: s.document_count > 0,
    },
    {
      href: `${base}/review`,
      label: "Review",
      hint:
        s.item_count === 0
          ? "Analyze to get suggestions"
          : s.pending_count > 0
            ? `${s.pending_count} to decide${s.flagged_count ? `, ${s.flagged_count} flagged` : ""}`
            : "All items decided",
      done: reviewDone || invoiceDone,
    },
    {
      href: `${base}/invoice`,
      label: "Invoice",
      hint: s.invoice_status
        ? `${s.invoice_number} · ${s.invoice_status}`
        : "Confirm, send and track",
      done: s.invoice_status === "paid",
    },
  ];

  return (
    <nav aria-label="Project steps" className="mt-6">
      <ol className="grid gap-2 sm:grid-cols-3">
        {steps.map((step, i) => {
          const active = pathname === step.href;
          return (
            <li key={step.href}>
              <Link
                href={step.href}
                aria-current={active ? "step" : undefined}
                className={cn(
                  "flex items-center gap-3 rounded-xl border px-4 py-3 transition",
                  active
                    ? "border-ink-950 bg-white shadow-sm ring-1 ring-ink-950"
                    : "border-slate-200 bg-white/60 hover:border-slate-300 hover:bg-white",
                )}
              >
                <span
                  className={cn(
                    "grid size-7 shrink-0 place-items-center rounded-full text-xs font-semibold",
                    step.done
                      ? "bg-brand-600 text-white"
                      : active
                        ? "bg-ink-950 text-white"
                        : "bg-slate-100 text-slate-500",
                  )}
                >
                  {step.done ? <Check className="size-4" /> : i + 1}
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-medium text-slate-900">{step.label}</span>
                  <span className="block truncate text-xs text-slate-500">{step.hint}</span>
                </span>
              </Link>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
