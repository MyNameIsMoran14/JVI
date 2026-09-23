import { create } from "zustand";

const STORAGE_KEY = "med-helper-token";

interface AuthState {
  token: string | null;
  name: string | null;
  status: "idle" | "loading" | "ready" | "error";
  error: string | null;
  setSession: (token: string, name: string) => void;
  setStatus: (status: AuthState["status"], error?: string) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem(STORAGE_KEY),
  name: null,
  status: "idle",
  error: null,
  setSession: (token, name) => {
    localStorage.setItem(STORAGE_KEY, token);
    set({ token, name, status: "ready", error: null });
  },
  setStatus: (status, error) => set({ status, error: error ?? null }),
}));
