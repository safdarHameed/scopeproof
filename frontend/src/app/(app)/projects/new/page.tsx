"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { ProjectForm } from "@/components/projects/project-form";
import { Card } from "@/components/ui/card";
import { projectsApi } from "@/lib/api";

export default function NewProjectPage() {
  const router = useRouter();
  return (
    <div className="mx-auto max-w-2xl">
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900"
      >
        <ArrowLeft className="size-4" /> Projects
      </Link>
      <h1 className="mt-4 text-2xl font-semibold tracking-tight text-slate-900">New project</h1>
      <p className="mt-1 text-sm text-slate-600">
        Next you&apos;ll upload the contract and the email conversation with this client.
      </p>
      <Card className="mt-8 p-6 sm:p-8">
        <ProjectForm
          submitLabel="Create project"
          onCancel={() => router.push("/dashboard")}
          onSubmit={async (data) => {
            const project = await projectsApi.create(data);
            router.push(`/projects/${project.id}`);
          }}
        />
      </Card>
    </div>
  );
}
