"use client";

import { useEffect, useState } from "react";

import { Shell } from "@/components/Shell";
import { Card, KpiCard } from "@/components/ui";
import { apiFetch } from "@/lib/api";

type Stats = { accounts: number; leads: number; campaigns: number };

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Stats>("/analytics/dashboard")
      .then(setStats)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed"));
  }, []);

  return (
    <Shell>
      <div className="flex items-baseline justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
      </div>

      {error ? <div className="mt-6 text-sm text-red-600">{error}</div> : null}

      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Connections sent" value="—" hint="Coming from automation events" />
        <KpiCard label="Acceptance rate" value="—" hint="Accepted / Sent" />
        <KpiCard label="Replies" value="—" hint="LinkedIn reply events" />
        <KpiCard label="Emails sent" value="—" hint="Email provider events" />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <KpiCard label="LinkedIn accounts" value={stats ? stats.accounts : "—"} />
        <KpiCard label="Leads" value={stats ? stats.leads : "—"} />
        <KpiCard label="Campaigns" value={stats ? stats.campaigns : "—"} />
      </div>

      <div className="mt-6">
        <Card title="Campaign performance">
          <div className="text-sm text-zinc-600 dark:text-zinc-300">
            Detailed campaign analytics will appear here once campaign events are tracked.
          </div>
        </Card>
      </div>
    </Shell>
  );
}
