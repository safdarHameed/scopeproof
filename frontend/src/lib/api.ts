import { config } from "@/lib/config";
import { tokenStore } from "@/lib/token";
import type {
  DocumentDetail,
  DocumentKind,
  DocumentMeta,
  InvoiceState,
  Item,
  ItemPayload,
  Project,
  ProjectPayload,
  ReviewState,
  UploadResult,
} from "@/types/api";
import type { RegisterPayload, TokenResponse, User } from "@/types/auth";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function send(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && typeof init.body === "string") headers.set("Content-Type", "application/json");

  let res: Response;
  try {
    res = await fetch(`${config.apiUrl}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Can't reach the server. Is the API running?");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, formatDetail(body?.detail) ?? res.statusText);
  }
  return res;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await send(path, init);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
});

// FastAPI returns either a string or a list of validation errors.
function formatDetail(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { loc?: string[]; msg?: string };
    const field = first.loc?.at(-1);
    return field ? `${field}: ${first.msg}` : (first.msg ?? null);
  }
  return null;
}

export function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : "Something went wrong";
}

/** Fetches a file with the auth header and hands it to the browser as a download. */
async function downloadFile(path: string, filename: string) {
  const blob = await (await send(path)).blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const authApi = {
  register: (data: RegisterPayload) => request<User>("/auth/register", json("POST", data)),

  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: new URLSearchParams({ username: email, password }),
    }),

  me: () => request<User>("/users/me"),
};

export const projectsApi = {
  list: () => request<Project[]>("/projects"),
  get: (id: string) => request<Project>(`/projects/${id}`),
  create: (data: ProjectPayload) => request<Project>("/projects", json("POST", data)),
  update: (id: string, data: Partial<ProjectPayload>) =>
    request<Project>(`/projects/${id}`, json("PATCH", data)),
  remove: (id: string) => request<void>(`/projects/${id}`, { method: "DELETE" }),
};

export const documentsApi = {
  list: (projectId: string) => request<DocumentMeta[]>(`/projects/${projectId}/documents`),
  get: (projectId: string, docId: string) =>
    request<DocumentDetail>(`/projects/${projectId}/documents/${docId}`),
  upload: (projectId: string, files: File[]) => {
    const body = new FormData();
    files.forEach((f) => body.append("files", f, f.name));
    return request<UploadResult>(`/projects/${projectId}/documents`, { method: "POST", body });
  },
  setKind: (projectId: string, docId: string, kind: DocumentKind) =>
    request<DocumentMeta>(`/projects/${projectId}/documents/${docId}`, json("PATCH", { kind })),
  remove: (projectId: string, docId: string) =>
    request<void>(`/projects/${projectId}/documents/${docId}`, { method: "DELETE" }),
  download: (projectId: string, doc: DocumentMeta) =>
    downloadFile(`/projects/${projectId}/documents/${doc.id}/file`, doc.filename),
};

export const reviewApi = {
  get: (projectId: string) => request<ReviewState>(`/projects/${projectId}/review`),
  analyze: (projectId: string) =>
    request<ReviewState>(`/projects/${projectId}/analysis`, { method: "POST" }),
  approveClear: (projectId: string) =>
    request<ReviewState>(`/projects/${projectId}/items/approve-clear`, { method: "POST" }),
  addItem: (projectId: string, data: ItemPayload) =>
    request<Item>(`/projects/${projectId}/items`, json("POST", data)),
  updateItem: (projectId: string, itemId: string, data: ItemPayload) =>
    request<Item>(`/projects/${projectId}/items/${itemId}`, json("PATCH", data)),
  removeItem: (projectId: string, itemId: string) =>
    request<void>(`/projects/${projectId}/items/${itemId}`, { method: "DELETE" }),
};

export const invoiceApi = {
  get: (projectId: string) => request<InvoiceState>(`/projects/${projectId}/invoice`),
  confirm: (projectId: string, data: { due_date?: string | null; note?: string | null }) =>
    request<InvoiceState>(`/projects/${projectId}/invoice`, json("POST", data)),
  reopen: (projectId: string) =>
    request<InvoiceState>(`/projects/${projectId}/invoice/reopen`, { method: "POST" }),
  send: (projectId: string) =>
    request<InvoiceState>(`/projects/${projectId}/invoice/send`, { method: "POST" }),
  refresh: (projectId: string) =>
    request<InvoiceState>(`/projects/${projectId}/invoice/refresh`, { method: "POST" }),
  cancel: (projectId: string) =>
    request<InvoiceState>(`/projects/${projectId}/invoice/cancel`, { method: "POST" }),
};
