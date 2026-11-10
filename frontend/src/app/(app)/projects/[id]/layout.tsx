import { Suspense } from "react";

import { ProjectShell } from "@/components/projects/project-shell";
import { PageSpinner } from "@/components/ui/spinner";

// The project id is only known at request time, so the shell (which reads it) sits
// behind a Suspense boundary, as Cache Components requires.
export default function ProjectLayout({ children }: LayoutProps<"/projects/[id]">) {
  return (
    <Suspense fallback={<PageSpinner />}>
      <ProjectShell>{children}</ProjectShell>
    </Suspense>
  );
}
