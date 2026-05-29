"use client";

import { useEffect, useState } from "react";

import { Shell } from "@/components/Shell";
import { useToast } from "@/components/Toaster";
import { Button, Card, Input, Pagination, Select, Textarea } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import { getToken } from "@/lib/auth";

type Lead = {
  id: string;
  account_id: string;
  first_name: string | null;
  last_name: string | null;
  company: string | null;
  job_title: string | null;
  linkedin_url: string;
  email: string | null;
  status: string;
};

type Account = { id: string; name: string };
type LeadMode = "single" | "extract";
type AutomationJobStatus = {
  id: string;
  account_id: string;
  job_type: string;
  status: string;
  attempts: number;
  locked_by: string | null;
  last_error: string | null;
};

function parseCsv(text: string): Record<string, string>[] {
  const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (lines.length === 0) return [];
  const header = lines[0].split(",").map((h) => h.trim());
  return lines.slice(1).map((line) => {
    const cols = line.split(",").map((c) => c.trim());
    const row: Record<string, string> = {};
    header.forEach((h, i) => {
      row[h] = cols[i] ?? "";
    });
    return row;
  });
};

export default function LeadsPage() {
  const toast = useToast();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountId, setAccountId] = useState<string>("");
  const [leads, setLeads] = useState<Lead[]>([]);
  const [mode, setMode] = useState<LeadMode>("single");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [searchUrl, setSearchUrl] = useState("");
  const [connectNote, setConnectNote] = useState("");
  const [message, setMessage] = useState("");
  const [followups, setFollowups] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const [activeExtractionJobId, setActiveExtractionJobId] = useState<string | null>(null);

  async function refresh() {
    setError(null);
    try {
      if (!accountId) return;
      const offset = (page - 1) * pageSize;
      const data = await apiFetch<Lead[]>(
        `/leads?account_id=${encodeURIComponent(accountId)}&limit=${pageSize}&offset=${offset}`,
      );
      setLeads(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  useEffect(() => {
    apiFetch<Account[]>("/accounts")
      .then((a) => {
        setAccounts(a);
        if (!accountId && a.length > 0) setAccountId(a[0].id);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
  }, [accountId, page]);

  useEffect(() => {
    if (!activeExtractionJobId) return;

    let stopped = false;
    let ticks = 0;

    const poll = async () => {
      if (stopped) return;
      ticks += 1;
      try {
        const st = await apiFetch<AutomationJobStatus>(
          `/leads/automation-jobs/${encodeURIComponent(activeExtractionJobId)}`,
        );
        if (st.status === "failed") {
          setActiveExtractionJobId(null);
          const raw = st.last_error || "Unknown error";
          const cleaned =
            raw.includes("LinkedIn login required for this account session") ||
            raw.includes("LinkedIn requires sign-in") ||
            raw.includes("LinkedIn is not accessible (login/checkpoint)")
              ? "LinkedIn session not connected. Go to Accounts → Connect LinkedIn and paste your li_at cookie, then retry extraction."
              : raw.startsWith("Traceback") && raw.includes("LinkedIn login required")
                ? "LinkedIn session not connected. Go to Accounts → Connect LinkedIn and paste your li_at cookie, then retry extraction."
                : raw;
          toast.error("Extraction failed", cleaned);
          return;
        }
        if (st.status === "done") {
          setActiveExtractionJobId(null);
          toast.success("Extraction finished");
          await refresh();
          return;
        }
        await refresh();
      } catch (e) {
        if (ticks >= 10) setActiveExtractionJobId(null);
      }
    };

    const id = window.setInterval(() => {
      poll().catch(() => {});
    }, 4000);

    poll().catch(() => {});
    return () => {
      stopped = true;
      window.clearInterval(id);
    };
  }, [activeExtractionJobId]);

  async function onAdd(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      if (!accountId) throw new Error("Select an account");
      if (mode === "single") {
        await apiFetch<Lead>("/leads", {
          method: "POST",
          body: JSON.stringify({ account_id: accountId, linkedin_url: linkedinUrl }),
        });
        toast.success("Lead saved");
        setLinkedinUrl("");
        setPage(1);
        await refresh();
        return;
      }

      const url = (searchUrl || "").trim();
      if (!url) throw new Error("Enter a LinkedIn search URL");
      if (!url.includes("linkedin.com/")) throw new Error("Enter a valid LinkedIn URL");

      const followupList = followups
        .split(/\r?\n/)
        .map((l) => l.trim())
        .filter((l) => l.length > 0);

      const res = await apiFetch<{ campaign_id: string; automation_job_id: string; status: string }>(
        "/leads/extract-search",
        {
          method: "POST",
          body: JSON.stringify({
            account_id: accountId,
            search_url: url,
            connect_note: connectNote.trim() || null,
            message: message.trim() || null,
            followups: followupList,
            lead_limit: 50,
          }),
        },
      );

      toast.success("Extraction started", "Leads will appear as they’re found");
      setActiveExtractionJobId(res.automation_job_id);
      setSearchUrl("");
      setConnectNote("");
      setMessage("");
      setFollowups("");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed";
      setError(msg);
      toast.error(mode === "single" ? "Failed to save lead" : "Failed to start extraction", msg);
    }
  }

  async function exportCsv() {
    setError(null);
    try {
      const token = getToken();
      if (!token) throw new Error("Not authenticated");
      if (!accountId) throw new Error("Select an account");
      const url = `${
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"
      }/leads/export.csv?account_id=${encodeURIComponent(accountId)}`;
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      const href = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = href;
      a.download = "leads.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(href);
      toast.success("CSV exported");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed";
      setError(msg);
      toast.error("Export failed", msg);
    }
  }

  async function onUploadCsv(file: File) {
    setError(null);
    try {
      if (!accountId) throw new Error("Select an account");
      const text = await file.text();
      const rows = parseCsv(text);
      if (rows.length === 0) throw new Error("Empty CSV");
      const toCreate = rows.slice(0, 200);
      for (const r of toCreate) {
        const payload = {
          account_id: accountId,
          first_name: r.first_name || null,
          last_name: r.last_name || null,
          company: r.company || null,
          job_title: r.job_title || null,
          linkedin_url: r.linkedin_url || "",
          email: r.email || null,
          status: r.status || "new",
        };
        if (!payload.linkedin_url) continue;
        await apiFetch<Lead>("/leads", { method: "POST", body: JSON.stringify(payload) });
      }
      toast.success("CSV imported", `Imported up to ${toCreate.length} rows`);
      setPage(1);
      await refresh();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed";
      setError(msg);
      toast.error("CSV import failed", msg);
    }
  }

  const visible = leads.filter((l) => {
    const q = search.trim().toLowerCase();
    if (!q) return true;
    const name = `${l.first_name || ""} ${l.last_name || ""}`.trim().toLowerCase();
    return (
      name.includes(q) ||
      (l.company || "").toLowerCase().includes(q) ||
      (l.job_title || "").toLowerCase().includes(q) ||
      l.linkedin_url.toLowerCase().includes(q) ||
      (l.email || "").toLowerCase().includes(q)
    );
  });

  return (
    <Shell>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">Leads</h1>
        <div className="flex flex-wrap items-center gap-2">
          <div className="w-56">
            <Select
              value={accountId}
              onChange={(v) => {
                setAccountId(v);
                setPage(1);
              }}
              options={[
                { value: "", label: accounts.length === 0 ? "No accounts" : "Select account" },
                ...accounts.map((a) => ({ value: a.id, label: a.name })),
              ]}
            />
          </div>
          <div className="w-64">
            <Input value={search} onChange={setSearch} placeholder="Search leads..." />
          </div>
          <Button variant="secondary" onClick={exportCsv}>
            Export CSV
          </Button>
          <label className="inline-flex cursor-pointer">
            <input
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onUploadCsv(f);
                e.currentTarget.value = "";
              }}
            />
            <span className="inline-flex items-center justify-center rounded-xl border border-border bg-card px-3 py-2 text-sm font-medium hover:bg-muted">
              Upload CSV
            </span>
          </label>
        </div>
      </div>

      {error ? <div className="mt-6 text-sm text-red-600">{error}</div> : null}

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <Card title={mode === "single" ? "Add lead" : "Extract a Search"}>
            <form onSubmit={onAdd} className="space-y-4">
              <div>
                <div className="text-sm font-medium">Mode</div>
                <div className="mt-1">
                  <Select
                    value={mode}
                    onChange={(v) => setMode(v as LeadMode)}
                    options={[
                      { value: "single", label: "Add single profile" },
                      { value: "extract", label: "Extract a Search" },
                    ]}
                  />
                </div>
              </div>

              {mode === "single" ? (
              <div>
                <div className="text-sm font-medium">LinkedIn URL</div>
                <div className="mt-1">
                  <Input
                    value={linkedinUrl}
                    onChange={setLinkedinUrl}
                    placeholder="https://www.linkedin.com/in/..."
                  />
                </div>
              </div>
              ) : (
                <>
                  <div>
                    <div className="text-sm font-medium">LinkedIn Search URL</div>
                    <div className="mt-1">
                      <Input
                        value={searchUrl}
                        onChange={setSearchUrl}
                        placeholder="https://www.linkedin.com/search/results/people/?keywords=..."
                      />
                    </div>
                  </div>
                  <div>
                    <div className="text-sm font-medium">Connection note (optional)</div>
                    <div className="mt-1">
                      <Textarea
                        value={connectNote}
                        onChange={setConnectNote}
                        rows={3}
                        placeholder="Short note to include with the connection request (optional)"
                      />
                    </div>
                  </div>
                  <div>
                    <div className="text-sm font-medium">First message (optional)</div>
                    <div className="mt-1">
                      <Textarea
                        value={message}
                        onChange={setMessage}
                        rows={5}
                        placeholder="Message sent after connecting (optional)"
                      />
                    </div>
                  </div>
                  <div>
                    <div className="text-sm font-medium">Follow-up messages (optional)</div>
                    <div className="mt-1">
                      <Textarea
                        value={followups}
                        onChange={setFollowups}
                        rows={6}
                        placeholder={"One follow-up per line"}
                      />
                    </div>
                  </div>
                </>
              )}
              <Button type="submit">{mode === "single" ? "Save" : "Start extraction"}</Button>
            </form>
          </Card>
        </div>

        <div className="lg:col-span-3">
          <Card title="Leads">
            {accountId ? (
              visible.length === 0 ? (
                <div className="text-sm text-zinc-600 dark:text-zinc-300">No leads found.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="text-xs text-zinc-600 dark:text-zinc-300">
                      <tr>
                        <th className="py-2">Name</th>
                        <th className="py-2">Company</th>
                        <th className="py-2">Title</th>
                        <th className="py-2">Email</th>
                        <th className="py-2">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {visible.map((l) => (
                        <tr key={l.id}>
                          <td className="py-3 font-medium">
                            {`${l.first_name || ""} ${l.last_name || ""}`.trim() || "—"}
                          </td>
                          <td className="py-3">{l.company || "—"}</td>
                          <td className="py-3">{l.job_title || "—"}</td>
                          <td className="py-3">{l.email || "—"}</td>
                          <td className="py-3">{l.status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
            ) : (
              <div className="text-sm text-zinc-600 dark:text-zinc-300">
                Create a LinkedIn account to start importing leads.
              </div>
            )}
            <Pagination
              page={page}
              canPrev={page > 1}
              canNext={leads.length === pageSize}
              onPrev={() => setPage((p) => Math.max(1, p - 1))}
              onNext={() => setPage((p) => p + 1)}
            />
          </Card>
        </div>
      </div>
    </Shell>
  );
}
