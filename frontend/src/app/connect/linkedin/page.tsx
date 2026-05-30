"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { Shell } from "@/components/Shell";
import { useToast } from "@/components/Toaster";
import { Button, Card, Input } from "@/components/ui";
import { apiFetch } from "@/lib/api";

function ConnectLinkedInInner() {
  const toast = useToast();
  const sp = useSearchParams();
  const token = sp.get("token") || "";

  const [liAt, setLiAt] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [detail, setDetail] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    setStatus(null);
    setDetail(null);
    setLoading(true);
    try {
      const res = await apiFetch<{ status: string; detail?: string | null }>("/accounts/connect/complete", {
        method: "POST",
        body: JSON.stringify({ token, li_at: liAt }),
      });
      setStatus(res.status);
      setDetail(res.detail || null);
      if (res.status === "connected") toast.success("LinkedIn connected");
      else toast.error("Not connected", res.status);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed";
      setError(msg);
      toast.error("Failed to connect", msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Shell>
      <div className="mx-auto w-full max-w-2xl">
        <Card title="Connect LinkedIn">
          <div className="text-sm text-zinc-600 dark:text-zinc-300">
            Step 1: Open LinkedIn and log in (in any browser).
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <a href="https://www.linkedin.com/login" target="_blank" rel="noreferrer">
              <Button variant="secondary">Open LinkedIn login</Button>
            </a>
          </div>

          <div className="mt-6 text-sm text-zinc-600 dark:text-zinc-300">
            Step 2: Paste your LinkedIn session cookie value (<span className="font-medium">li_at</span>) to connect
            this account (no password stored).
          </div>
          <div className="mt-2">
            <Input value={liAt} onChange={setLiAt} placeholder="li_at cookie value" />
          </div>

          {error ? <div className="mt-4 text-sm text-red-600">{error}</div> : null}
          {status ? <div className="mt-4 text-sm">Status: {status}</div> : null}
          {detail ? <div className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">Detail: {detail}</div> : null}

          <div className="mt-6 flex items-center justify-end">
            <Button disabled={loading || !token || liAt.trim().length < 10} onClick={submit}>
              {loading ? "Connecting..." : "Connect my LinkedIn account"}
            </Button>
          </div>

          {!token ? (
            <div className="mt-4 text-sm text-red-600">Missing token. Please open this page from the Connect link.</div>
          ) : null}
        </Card>
      </div>
    </Shell>
  );
}

export default function ConnectLinkedInPage() {
  return (
    <Suspense>
      <ConnectLinkedInInner />
    </Suspense>
  );
}
