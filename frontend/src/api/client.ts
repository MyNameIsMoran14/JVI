import { useAuthStore } from "../store/auth";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = useAuthStore.getState().token;
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`/api/v1${path}`, { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(response.status, body.detail ?? response.statusText);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
};

export async function authenticate(): Promise<void> {
  const { setSession, setStatus } = useAuthStore.getState();
  setStatus("loading");

  const initData = window.Telegram?.WebApp?.initData;
  if (!initData) {
    setStatus("error", "Открой это приложение через кнопку в Telegram-боте.");
    return;
  }

  try {
    const response = await fetch("/api/v1/auth/telegram", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ init_data: initData }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new ApiError(response.status, body.detail ?? "Не удалось войти");
    }
    const body = (await response.json()) as { access_token: string; name: string };
    setSession(body.access_token, body.name);
  } catch (error) {
    setStatus("error", error instanceof Error ? error.message : "Не удалось войти");
  }
}
