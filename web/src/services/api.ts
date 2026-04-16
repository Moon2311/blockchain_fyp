/**
 * Backend integration — session cookies (credentials: include) via Vite proxy.
 */

const API = "/api";

async function parseError(res: Response): Promise<string> {
  try {
    const j = await res.json();
    if (j && typeof j.error === "string") return j.error;
    return res.statusText;
  } catch {
    return res.statusText || "Request failed";
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { credentials: "include" });
  if (res.status === 401) throw new Error("Unauthorized");
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<T>;
}

export async function apiPostJson<T>(
  path: string,
  body: Record<string, unknown>
): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.status === 401) throw new Error("Unauthorized");
  if (!res.ok) throw new Error(await parseError(res));
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

export async function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (res.status === 401) throw new Error("Unauthorized");
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<T>;
}

export type UserInfo = {
  email: string;
  name: string;
  role: string;
  id: number;
};

export async function fetchMe(): Promise<{ user: UserInfo | null }> {
  return apiGet("/auth/me");
}

export async function login(email: string, password: string) {
  return apiPostJson<{ user: UserInfo }>("/auth/login", { email, password });
}

export async function logout() {
  return apiPostJson<{ ok: boolean }>("/auth/logout", {});
}

export async function register(payload: {
  email: string;
  password: string;
  password2: string;
  name: string;
  role: string;
}) {
  return apiPostJson<{ ok?: boolean }>("/auth/register", payload);
}
