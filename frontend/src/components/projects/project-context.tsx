"use client";

import { createContext, useContext } from "react";

import type { Project } from "@/types/api";

interface ProjectContextValue {
  project: Project;
  /** Re-fetch the project summary (step badges, totals) after a change. */
  refreshProject: () => Promise<unknown>;
}

export const ProjectContext = createContext<ProjectContextValue | null>(null);

export function useProject() {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error("useProject must be used inside a project page");
  return ctx;
}
