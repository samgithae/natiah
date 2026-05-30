"use client";

import { useEffect, useState } from "react";

import { Shell } from "@/components/Shell";
import { useToast } from "@/components/Toaster";
import { Button, Card, Input, Pagination } from "@/components/ui";
import { apiFetch } from "@/lib/api";

type Campaign = {
  id: string;
  name: string;
  status: string;
  daily_limit: number;
};

export default function CampaignsPage() {
  const toast = useToast();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [name, setName] = useState("");
  const [dailyLimit, setDailyLimit] = useState("50");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  async function refresh() {
    setError(null);
    try {
      setCampaigns(await apiFetch<Campaign[]>("/campaigns"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiFetch<Campaign>("/campaigns", {
        method: "POST",
        body: JSON.stringify({ name, daily_limit: Number(dailyLimit || "0") }),
      });
      toast.success("Campaign created");
      setName("");
      setDailyLimit("50");
      await refresh();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed";
      setError(msg);
      toast.error("Failed to create campaign", msg);
    }
  }

  async function start(id: string) {
    setError(null);
    try {
      await apiFetch(`/campaigns/${id}/start`, { method: "POST" });
      toast.success("Campaign started");
      await refresh();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed";
      setError(msg);
      toast.error("Failed to start", msg);
    }
  }

  async function stop(id: string) {
    setError(null);
    try {
      await apiFetch(`/campaigns/${id}/stop`, { method: "POST" });
      toast.success("Campaign stopped");
      await refresh();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed";
      setError(msg);
      toast.error("Failed to stop", msg);
    }
  }

  async function onDelete(id: string) {
    setError(null);
    try {
      await apiFetch(`/campaigns/${id}`, { method: "DELETE" });
      toast.success("Campaign deleted");
      await refresh();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed";
      setError(msg);
      toast.error("Failed to delete", msg);
    }
  }

  const filtered = campaigns.filter((c) => {
    const q = search.trim().toLowerCase();
    if (!q) return true;
    return c.name.toLowerCase().includes(q) || c.status.toLowerCase().includes(q);
  });
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const paged = filtered.slice((safePage - 1) * pageSize, safePage * pageSize);

  return (
    <Shell>
      <div className="flex items-baseline justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">Campaigns</h1>
        <div className="w-full max-w-sm">
          <Input value={search} onChange={setSearch} placeholder="Search campaigns..." />
        </div>
      </div>

      {error ? <div className="mt-6 text-sm text-red-600">{error}</div> : null}

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <Card title="Create campaign">
            <form onSubmit={onCreate} className="space-y-4">
              <div>
                <div className="text-sm font-medium">Name</div>
                <div className="mt-1">
                  <Input value={name} onChange={setName} placeholder="Campaign name" />
                </div>
              </div>
              <div>
                <div className="text-sm font-medium">Daily limit</div>
                <div className="mt-1">
                  <Input value={dailyLimit} onChange={setDailyLimit} placeholder="50" />
                </div>
              </div>
              <Button type="submit">Create</Button>
            </form>
          </Card>
        </div>

        <div className="lg:col-span-3">
          <Card title="Campaigns">
            {paged.length === 0 ? (
              <div className="text-sm text-zinc-600 dark:text-zinc-300">No campaigns found.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs text-zinc-600 dark:text-zinc-300">
                    <tr>
                      <th className="py-2">Name</th>
                      <th className="py-2">Status</th>
                      <th className="py-2">Daily limit</th>
                      <th className="py-2"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {paged.map((c) => (
                      <tr key={c.id}>
                        <td className="py-3 font-medium">{c.name}</td>
                        <td className="py-3">{c.status}</td>
                        <td className="py-3">{c.daily_limit}</td>
                        <td className="py-3 text-right">
                          <div className="flex justify-end gap-2">
                            {c.status !== "running" ? (
                              <Button onClick={() => start(c.id)}>Start</Button>
                            ) : (
                              <Button variant="secondary" onClick={() => stop(c.id)}>
                                Stop
                              </Button>
                            )}
                            <Button variant="secondary" onClick={() => onDelete(c.id)}>
                              Delete
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
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
    </Shell>
  );
}
