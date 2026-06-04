import { create } from "zustand";

interface AuthUser { id: string; email: string; name: string; role: string; practitioner_id: string | null; }
interface AuthStore { user: AuthUser | null; token: string | null; setAuth: (u: AuthUser, t: string) => void; logout: () => void; }

export const useAuthStore = create<AuthStore>((set) => ({
  user: JSON.parse(localStorage.getItem("user") || "null"),
  token: localStorage.getItem("token") || null,
  setAuth: (u, t) => { localStorage.setItem("token", t); localStorage.setItem("user", JSON.stringify(u)); set({ user: u, token: t }); },
  logout: () => { localStorage.removeItem("token"); localStorage.removeItem("user"); set({ user: null, token: null }); },
}))