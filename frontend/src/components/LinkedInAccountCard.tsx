"use client";

import { Button, Card } from "@/components/ui";
import { StatusBadge } from "@/components/StatusBadge";

export type LinkedInAccount = {
  id: string;
  name: string;
  linkedin_email: string | null;
  daily_limit: number;
  status: string;
  last_connected_at: string | null;
};

function formatDate(s: string | null) {
  if (!s) return "—";
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString();
}

export function LinkedInAccountCard({
  account,
  onConnect,
  onVerify,
  onReconnect,
  onPauseToggle,
  onDelete,
}: {
  account: LinkedInAccount;
  onConnect: () => void;
  onVerify: () => void;
  onReconnect: () => void;
  onPauseToggle: () => void;
  onDelete: () => void;
}) {
  const paused = (account.status || "").toLowerCase() === "paused";
  const canConnect = (account.status || "").toLowerCase() === "pending";

  return (
    <Card title={account.name} actions={<StatusBadge status={account.status} />}>
      <div className="text-sm text-zinc-600 dark:text-zinc-300">{account.linkedin_email || "—"}</div>
      <div className="mt-4 grid gap-2 text-sm">
        <div className="flex items-center justify-between gap-4">
          <div className="text-zinc-600 dark:text-zinc-300">Daily limit</div>
          <div className="font-medium">{account.daily_limit}</div>
        </div>
        <div className="flex items-center justify-between gap-4">
          <div className="text-zinc-600 dark:text-zinc-300">Last connected</div>
          <div className="font-medium">{formatDate(account.last_connected_at)}</div>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {canConnect ? (
          <Button variant="secondary" onClick={onConnect}>
            Connect LinkedIn
          </Button>
        ) : null}
        <Button variant="secondary" onClick={onVerify}>
          Verify Session
        </Button>
        <Button variant="secondary" onClick={onReconnect}>
          Reconnect
        </Button>
        <Button variant="secondary" onClick={onPauseToggle}>
          {paused ? "Unpause" : "Pause"}
        </Button>
        <Button variant="secondary" onClick={onDelete}>
          Delete
        </Button>
      </div>
    </Card>
  );
}
