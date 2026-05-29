"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { clearToken, getToken } from "@/lib/auth";
import { getTheme, setTheme, type ThemeMode } from "@/lib/theme";
import { useToast } from "@/components/Toaster";
import { Button, NavLink } from "@/components/ui";

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/accounts", label: "Accounts" },
  { href: "/leads", label: "Leads" },
  { href: "/campaigns", label: "Campaigns" },
  { href: "/sequences", label: "Sequences" },
  { href: "/analytics", label: "Analytics" },
  { href: "/settings", label: "Settings" },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const toast = useToast();
  const [token, setTokenState] = useState<string | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [theme, setThemeState] = useState<ThemeMode>("light");

  const isPublic = useMemo(() => pathname === "/" || pathname === "/login", [pathname]);

  useEffect(() => {
    const syncToken = () => setTokenState(getToken());
    syncToken();
    setAuthChecked(true);
    setThemeState(getTheme());

    window.addEventListener("storage", syncToken);
    window.addEventListener("natiah-auth", syncToken);
    return () => {
      window.removeEventListener("storage", syncToken);
      window.removeEventListener("natiah-auth", syncToken);
    };
  }, []);

  useEffect(() => {
    if (isPublic) return;
    if (!authChecked) return;
    if (!token) router.push("/login");
  }, [authChecked, isPublic, router, token]);

  return (
    <div className="min-h-full">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl">
        <aside className="hidden w-64 flex-col border-r border-border bg-card p-4 lg:flex">
          <div className="flex items-center justify-between gap-2 px-2 py-2">
            <Link href="/" className="text-sm font-semibold tracking-tight">
              Natiah
            </Link>
            <Button
              variant="ghost"
              onClick={() => {
                const next: ThemeMode = theme === "dark" ? "light" : "dark";
                setTheme(next);
                setThemeState(next);
                toast.info("Theme updated", next === "dark" ? "Dark mode enabled" : "Light mode enabled");
              }}
            >
              {theme === "dark" ? "Dark" : "Light"}
            </Button>
          </div>

          <nav className="mt-4 flex flex-1 flex-col gap-1">
            {links.map((l) => (
              <NavLink key={l.href} href={l.href} active={pathname === l.href}>
                {l.label}
              </NavLink>
            ))}
          </nav>

          <div className="mt-4 flex items-center gap-2">
            {!authChecked ? null : !token ? (
              <Button onClick={() => router.push("/login")}>Login</Button>
            ) : (
              <Button
                variant="secondary"
                onClick={() => {
                  clearToken();
                  setTokenState(null);
                  toast.success("Logged out");
                  router.push("/login");
                }}
              >
                Logout
              </Button>
            )}
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex items-center justify-between gap-3 border-b border-border bg-card px-4 py-3 lg:hidden">
            <Link href="/" className="text-sm font-semibold tracking-tight">
              Natiah
            </Link>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                onClick={() => {
                  const next: ThemeMode = theme === "dark" ? "light" : "dark";
                  setTheme(next);
                  setThemeState(next);
                }}
              >
                {theme === "dark" ? "Dark" : "Light"}
              </Button>
              {!authChecked ? null : !token ? (
                <Button onClick={() => router.push("/login")}>Login</Button>
              ) : (
                <Button
                  variant="secondary"
                  onClick={() => {
                    clearToken();
                    setTokenState(null);
                    router.push("/login");
                  }}
                >
                  Logout
                </Button>
              )}
            </div>
          </header>

          <main className="w-full flex-1 px-4 py-8 lg:px-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
