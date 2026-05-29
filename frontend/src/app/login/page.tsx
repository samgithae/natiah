"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { Shell } from "@/components/Shell";
import { useToast } from "@/components/Toaster";
import { Button, Card, Input } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import { setToken } from "@/lib/auth";

type Token = { access_token: string; token_type: string };

export default function LoginPage() {
  const router = useRouter();
  const toast = useToast();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const title = useMemo(() => (mode === "login" ? "Login" : "Create account"), [mode]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "register") {
        await apiFetch("/auth/register", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
      }

      const form = new URLSearchParams();
      form.set("username", email);
      form.set("password", password);

      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/auth/login`,
        { method: "POST", body: form },
      );
      if (!res.ok) throw new Error(await res.text());
      const token = (await res.json()) as Token;
      setToken(token.access_token);
      toast.success("Welcome back");
      router.push("/dashboard");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Login failed";
      setError(msg);
      toast.error("Authentication failed", msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Shell>
      <div className="mx-auto w-full max-w-md">
        <Card title={title}>
          <div className="text-sm text-zinc-600 dark:text-zinc-300">
            Use email + password to access your Natiah workspace.
          </div>

          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <div>
              <div className="text-sm font-medium">Email</div>
              <div className="mt-1">
                <Input value={email} onChange={setEmail} type="email" />
              </div>
            </div>
            <div>
              <div className="text-sm font-medium">Password</div>
              <div className="mt-1">
                <Input value={password} onChange={setPassword} type="password" />
              </div>
              <div className="mt-1 text-xs text-zinc-600 dark:text-zinc-300">Minimum 8 characters.</div>
            </div>

            {error ? <div className="text-sm text-red-600">{error}</div> : null}

            <Button disabled={loading} type="submit">
              {loading ? "Working..." : mode === "login" ? "Login" : "Register & Login"}
            </Button>
          </form>

          <div className="mt-4 text-sm text-zinc-600 dark:text-zinc-300">
            {mode === "login" ? (
              <button
                type="button"
                className="font-medium text-foreground"
                onClick={() => setMode("register")}
              >
                Create an account
              </button>
            ) : (
              <button
                type="button"
                className="font-medium text-foreground"
                onClick={() => setMode("login")}
              >
                Back to login
              </button>
            )}
          </div>
        </Card>
      </div>
    </Shell>
  );
}
