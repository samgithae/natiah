"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Shell } from "@/components/Shell";
import { Card, KpiCard } from "@/components/ui";
import { apiFetch } from "@/lib/api";

type Stats = { accounts: number; leads: number; campaigns: number };

type Overview = {
  connections_sent: number;
  connections_accepted: number;
  connection_acceptance_rate: number;
  replies: number;
  reply_rate: number;
  emails_sent: number;
  email_opens: number;
  email_open_rate: number;
  conversions: number;
  conversion_rate: number;
};

type DailyPoint = { date: string; connections_sent: number; replies: number; emails_sent: number };
type CampaignRow = {
  campaign_id: string;
  campaign_name: string;
  connections_sent: number;
  replies: number;
  emails_sent: number;
};

function pct(v: number) {
  if (!Number.isFinite(v)) return "0%";
  return `${Math.round(v * 1000) / 10}%`;
}

export default function AnalyticsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [daily, setDaily] = useState<DailyPoint[]>([]);
  const [campaigns, setCampaigns] = useState<CampaignRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      apiFetch<Stats>("/analytics/dashboard"),
      apiFetch<Overview>("/analytics/overview?days=30"),
      apiFetch<DailyPoint[]>("/analytics/daily-activity?days=30"),
      apiFetch<CampaignRow[]>("/analytics/campaign-performance?days=30"),
    ])
      .then(([s, o, d, c]) => {
        setStats(s);
        setOverview(o);
        setDaily(Array.isArray(d) ? d : []);
        setCampaigns(Array.isArray(c) ? c : []);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed"));
  }, []);

  const rateData = overview
    ? [
        { name: "Acceptance", value: overview.connection_acceptance_rate },
        { name: "Reply", value: overview.reply_rate },
        { name: "Open", value: overview.email_open_rate },
        { name: "Conversion", value: overview.conversion_rate },
      ]
    : [];
  const rateColors = ["#16a34a", "#2563eb", "#f59e0b", "#a855f7"];

  return (
    <Shell>
      <div className="flex items-baseline justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
      </div>

      {error ? <div className="mt-6 text-sm text-red-600">{error}</div> : null}

      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <KpiCard label="Connections sent" value={overview ? overview.connections_sent : "—"} />
        <KpiCard label="Acceptance rate" value={overview ? pct(overview.connection_acceptance_rate) : "—"} />
        <KpiCard label="Reply rate" value={overview ? pct(overview.reply_rate) : "—"} />
        <KpiCard label="Email open rate" value={overview ? pct(overview.email_open_rate) : "—"} />
        <KpiCard label="Conversion rate" value={overview ? pct(overview.conversion_rate) : "—"} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <KpiCard label="Accounts" value={stats ? stats.accounts : "—"} />
        <KpiCard label="Leads" value={stats ? stats.leads : "—"} />
        <KpiCard label="Campaigns" value={stats ? stats.campaigns : "—"} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card title="Daily Activity">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={daily}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tickMargin={8} />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="connections_sent" name="Connections" stroke="#2563eb" strokeWidth={2} />
                <Line type="monotone" dataKey="replies" name="Replies" stroke="#16a34a" strokeWidth={2} />
                <Line type="monotone" dataKey="emails_sent" name="Emails" stroke="#f59e0b" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Rates">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Tooltip formatter={(v) => pct(Number(v))} />
                <Legend />
                <Pie data={rateData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90}>
                  {rateData.map((_, idx) => (
                    <Cell key={idx} fill={rateColors[idx % rateColors.length]} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <div className="mt-6">
        <Card title="Campaign Performance">
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={campaigns}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="campaign_name" tickMargin={8} interval={0} height={70} angle={-20} textAnchor="end" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Legend />
                <Bar dataKey="connections_sent" name="Connections" fill="#2563eb" />
                <Bar dataKey="replies" name="Replies" fill="#16a34a" />
                <Bar dataKey="emails_sent" name="Emails" fill="#f59e0b" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </Shell>
  );
}
