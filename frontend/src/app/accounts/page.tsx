"use client";

import { useEffect, useState } from "react";

import { Shell } from "@/components/Shell";
import { useToast } from "@/components/Toaster";
import { ConnectLinkedInModal } from "@/components/ConnectLinkedInModal";
import { LinkedInAccountCard, type LinkedInAccount } from "@/components/LinkedInAccountCard";
import { Button, Card, Input, Pagination } from "@/components/ui";
import { apiFetch } from "@/lib/api";

export default function AccountsPage() {
  const toast = useToast();
  const [accounts, setAccounts] = useState<LinkedInAccount[]>([]);
  const [name, setName] = useState("");
  const [linkedinEmail, setLinkedinEmail] = useState("");
  const [dailyLimit, setDailyLimit] = useState("50");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 10;
  const [connectOpen, setConnectOpen] = useState(false);
  const [connectAccountId, setConnectAccountId] = useState<string | null>(null);

  async function refresh() {
    setError(null);
    try {
      const data = await apiFetch<LinkedInAccount[]>("/accounts");
      setAccounts(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function create(connectAfter: boolean) {
    setError(null);
    try {
      const trimmedName = name.trim();
      if (!trimmedName) {
        const msg = "Name is required";
        setError(msg);
        toast.error("Failed to create account", msg);
        return;
      }
      const parsedDailyLimit = Number(dailyLimit || "0");
      if (!Number.isFinite(parsedDailyLimit) || parsedDailyLimit <= 0) {
        const msg = "Daily limit must be a positive number";
        setError(msg);
        toast.error("Failed to create account", msg);
        return;
      }
      const created = await apiFetch<LinkedInAccount>("/accounts", {
        method: "POST",
        body: JSON.stringify({
          name: trimmedName,
          linkedin_email: linkedinEmail.trim() ? linkedinEmail.trim() : null,
          daily_limit: parsedDailyLimit,
        }),
      });
      toast.success("Account created");
      setName("");
      setLinkedinEmail("");
      setDailyLimit("50");
      await refresh();
      if (connectAfter) {
        setConnectAccountId(created.id);
        setConnectOpen(true);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed";
      setError(msg);
      toast.error("Failed to create account", msg);
    }
  }

  async function onDelete(id: string) {
    setError(null);
    try {
      await apiFetch(`/accounts/${id}`, { method: "DELETE" });
      toast.success("Account deleted");
      await refresh();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed";
      setError(msg);
      toast.error("Failed to delete account", msg);
    }
  }

  async function onVerify(id: string) {
    setError(null);
    try {
      const res = await apiFetch<{ status: string }>(`/accounts/${id}/verify`);
      toast.success("Session checked", res.status);
      await refresh();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed";
      setError(msg);
      toast.error("Verify failed", msg);
    }
  }

  async function onReconnect(id: string) {
    setError(null);
    try {
      await apiFetch<{ status: string }>(`/accounts/${id}/reconnect`, { method: "POST" });
      toast.success("Reconnect started");
      await refresh();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed";
      setError(msg);
      toast.error("Reconnect failed", msg);
    }
  }

  async function onPauseToggle(a: LinkedInAccount) {
    setError(null);
    const paused = (a.status || "").toLowerCase() === "paused";
    try {
      await apiFetch(`/accounts/${a.id}`, {
        method: "PUT",
        body: JSON.stringify({ status: paused ? "pending" : "paused" }),
      });
      toast.success(paused ? "Account unpaused" : "Account paused");
      await refresh();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed";
      setError(msg);
      toast.error("Failed to update account", msg);
    }
  }

  const filtered = accounts.filter((a) => {
    const q = search.trim().toLowerCase();
    if (!q) return true;
    return (
      a.name.toLowerCase().includes(q) ||
      (a.linkedin_email || "").toLowerCase().includes(q) ||
      (a.status || "").toLowerCase().includes(q)
    );
  });
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const paged = filtered.slice((safePage - 1) * pageSize, safePage * pageSize);

  return (
    <Shell>
      <div className="flex items-baseline justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">LinkedIn Accounts</h1>
        <div className="w-full max-w-sm">
          <Input value={search} onChange={setSearch} placeholder="Search accounts..." />
        </div>
      </div>

      {error ? <div className="mt-6 text-sm text-red-600">{error}</div> : null}

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <Card title="Add account">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void create(false);
              }}
              className="space-y-4"
            >
              <div>
                <div className="text-sm font-medium">Name</div>
                <div className="mt-1">
                  <Input value={name} onChange={setName} placeholder="Account name" />
                </div>
              </div>
              <div>
                <div className="text-sm font-medium">LinkedIn email</div>
                <div className="mt-1">
                  <Input value={linkedinEmail} onChange={setLinkedinEmail} placeholder="optional" type="email" />
                </div>
              </div>
              <div>
                <div className="text-sm font-medium">Daily limit</div>
                <div className="mt-1">
                  <Input value={dailyLimit} onChange={setDailyLimit} placeholder="50" />
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={!name.trim()}>
                  Create
                </Button>
                <Button variant="secondary" type="button" disabled={!name.trim()} onClick={() => create(true)}>
                  Create & Connect LinkedIn
                </Button>
              </div>
            </form>
          </Card>
        </div>

        <div className="lg:col-span-3">
          <Card title="Accounts">
            {paged.length === 0 ? (
              <div className="text-sm text-zinc-600 dark:text-zinc-300">No accounts found.</div>
            ) : (
              <div className="grid gap-4">
                {paged.map((a) => (
                  <LinkedInAccountCard
                    key={a.id}
                    account={a}
                    onConnect={() => {
                      setConnectAccountId(a.id);
                      setConnectOpen(true);
                    }}
                    onVerify={() => onVerify(a.id)}
                    onReconnect={() => onReconnect(a.id)}
                    onPauseToggle={() => onPauseToggle(a)}
                    onDelete={() => onDelete(a.id)}
                  />
                ))}
              </div>
            )}
            <Pagination
              page={safePage}
              canPrev={safePage > 1}
              canNext={safePage < totalPages}
              onPrev={() => setPage((p) => Math.max(1, p - 1))}
              onNext={() => setPage((p) => Math.min(totalPages, p + 1))}
            />
          </Card>
        </div>
      </div>

      <ConnectLinkedInModal
        open={connectOpen}
        accountId={connectAccountId}
        onClose={() => setConnectOpen(false)}
        onDone={refresh}
      />
    </Shell>
  );
}
