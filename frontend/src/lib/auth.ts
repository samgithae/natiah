export const tokenStorageKey = "natiah_token";
const authEventName = "natiah-auth";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(tokenStorageKey);
}

export function setToken(token: string) {
  window.localStorage.setItem(tokenStorageKey, token);
  window.dispatchEvent(new Event(authEventName));
}

export function clearToken() {
  window.localStorage.removeItem(tokenStorageKey);
  window.dispatchEvent(new Event(authEventName));
}
