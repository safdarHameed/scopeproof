const KEY = "scopeproof.access_token";

export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(KEY);
    } catch {
      return null;
    }
  },
  set(token: string) {
    try {
      localStorage.setItem(KEY, token);
    } catch {}
  },
  clear() {
    try {
      localStorage.removeItem(KEY);
    } catch {}
  },
};
