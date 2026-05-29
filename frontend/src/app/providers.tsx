"use client";

import { useEffect, useState } from "react";

import { ToasterProvider } from "@/components/Toaster";
import { getTheme, setTheme, type ThemeMode } from "@/lib/theme";

export function Providers({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const theme = getTheme();
    setTheme(theme);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    const onStorage = (e: StorageEvent) => {
      if (e.key !== "natiah_theme") return;
      const v = e.newValue === "dark" ? "dark" : "light";
      setTheme(v as ThemeMode);
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [mounted]);

  return <ToasterProvider>{children}</ToasterProvider>;
}

