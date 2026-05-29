"use client";

import { useEffect, useMemo, useState } from "react";

import { Shell } from "@/components/Shell";
import { useToast } from "@/components/Toaster";
import { Button, Card, Input, Select } from "@/components/ui";
import { apiFetch } from "@/lib/api";

type Campaign = { id: string; name: string; status: string; daily_limit: number };
type Sequence = {
  id: string;
  campaign_id: string;
  step_number: number;
  delay_days: number;
  message_template: string;
};

export default function SequencesPage() {
  const toast = useToast();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [campaignId, setCampaignId] = useState("");
  const [sequences, setSequences] = useState<Sequence[]>([]);
  const [search, setSearch] = useState("");

  const [stepNumber, setStepNumber] = useState("1");
  const [delayDays, setDelayDays] = useState("0");
  const [template, setTemplate] = useState("");

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Campaign[]>("/campaigns")
      .then((c) => {
        setCampaigns(c);
        if (!campaignId && c.length > 0) setCampaignId(c[0].id);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed"));
  }, []);

  async function refreshSequences(nextCampaignId: string) {
    setError(null);
    try {
      if (!nextCampaignId) {
        setSequences([]);
        return;
      }
      const data = await apiFetch<Sequence[]>(
        `/sequences?campaign_id=${encodeURIComponent(nextCampaignId)}`,
      );
      setSequences(data);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed";
      setError(msg);
    }
  }

  useEffect(() => {
    refreshSequences(campaignId);
  }, [campaignId]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      if (!campaignId) throw new Error("Select a campaign");
      await apiFetch<Sequence>("/sequences", {
        method: "POST",
        body: JSON.stringify({
          campaign_id: campaignId,
          step_number: Number(stepNumber || "1"),
          delay_days: Number(delayDays || "0"),
          message_template: template,
        }),
      });
      toast.success("Sequence step created");
      setTemplate("");
      await refreshSequences(campaignId);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed";
      setError(msg);
      toast.error("Failed to create step", msg);
    }
  }

  async function onDelete(id: string) {
    setError(null);
    try {
      await apiFetch(`/sequences/${id}`, { method: "DELETE" });
      toast.success("Sequence step deleted");
      await refreshSequences(campaignId);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed";
      setError(msg);
      toast.error("Failed to delete step", msg);
    }
  }

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return sequences;
    return sequences.filter((s) => s.message_template.toLowerCase().includes(q));
  }, [search, sequences]);

  return (
    <Shell>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">Sequences</h1>
        <div className="flex flex-wrap items-center gap-2">
          <div className="w-72">
            <Select
              value={campaignId}
              onChange={setCampaignId}
              options={[
                { value: "", label: campaigns.length === 0 ? "No campaigns" : "Select campaign" },
                ...campaigns.map((c) => ({ value: c.id, label: c.name })),
              ]}
            />
          </div>
          <div className="w-64">
            <Input value={search} onChange={setSearch} placeholder="Search templates..." />
          </div>
        </div>
      </div>

      {error ? <div className="mt-6 text-sm text-red-600">{error}</div> : null}

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <Card title="Add step">
            <form onSubmit={onCreate} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-sm font-medium">Step</div>
                  <div className="mt-1">
                    <Input value={stepNumber} onChange={setStepNumber} placeholder="1" />
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium">Delay (days)</div>
                  <div className="mt-1">
                    <Input value={delayDays} onChange={setDelayDays} placeholder="0" />
                  </div>
                </div>
              </div>
              <div>
                <div className="text-sm font-medium">Message template</div>
                <div className="mt-1">
                  <textarea
                    value={template}
                    onChange={(e) => setTemplate(e.target.value)}
                    className="h-32 w-full rounded-xl border border-border bg-card px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-zinc-400/40 dark:focus:ring-zinc-500/50"
                    placeholder="Hi {{first_name}}, ..."
                    required
                  />
                </div>
              </div>
              <Button type="submit">Create step</Button>
            </form>
          </Card>
        </div>

        <div className="lg:col-span-3">
          <Card title="Steps">
            {!campaignId ? (
              <div className="text-sm text-zinc-600 dark:text-zinc-300">Select a campaign to manage steps.</div>
            ) : filtered.length === 0 ? (
              <div className="text-sm text-zinc-600 dark:text-zinc-300">No steps yet.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs text-zinc-600 dark:text-zinc-300">
                    <tr>
                      <th className="py-2">Step</th>
                      <th className="py-2">Delay</th>
                      <th className="py-2">Template</th>
                      <th className="py-2"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {filtered.map((s) => (
                      <tr key={s.id}>
                        <td className="py-3 font-medium">{s.step_number}</td>
                        <td className="py-3">{s.delay_days}d</td>
                        <td className="py-3">
                          <div className="max-w-xl truncate">{s.message_template}</div>
                        </td>
                        <td className="py-3 text-right">
                          <Button variant="secondary" onClick={() => onDelete(s.id)}>
                            Delete
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      </div>
    </Shell>
  );
}

