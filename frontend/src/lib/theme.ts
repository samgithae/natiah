export type ThemeMode = "light" | "dark";

const key = "natiah_theme";

export function getTheme(): ThemeMode {
  if (typeof window === "undefined") return "light";
  const value = window.localStorage.getItem(key);
  return value === "dark" ? "dark" : "light";
}

export function setTheme(theme: ThemeMode) {
  window.localStorage.setItem(key, theme);
  if (theme === "dark") document.documentElement.classList.add("dark");
  else document.documentElement.classList.remove("dark");
}

