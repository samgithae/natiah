"use client";

import { useEffect, useState } from "react";

import { useToast } from "@/components/Toaster";
import { Button } from "@/components/ui";
import { apiFetch } from "@/lib/api";

type OAuthInitiateResult = { connect_url: string };
type CookieConnectLinkResult = { url: string };

export function ConnectLinkedInModal({
  open,
  accountId,
  onClose,
  onDone,
}: {
  open: boolean;
  accountId: string | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [cookieConnectUrl, setCookieConnectUrl] = useState<string | null>(null);
  const [connectUrl, setConnectUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !accountId) return;
    setError(null);
    setCookieConnectUrl(null);
    setConnectUrl(null);
    setLoading(true);

    apiFetch<CookieConnectLinkResult>(`/accounts/${accountId}/connect-link`, { method: "POST" })
      .then(({ url }) => setCookieConnectUrl(url))
      .catch((e) => {
        const msg = e instanceof Error ? e.message : "Failed";
        setError(msg);
        toast.error("Connect link failed", msg);
      })
      .finally(() => {
        apiFetch<OAuthInitiateResult>(`/accounts/${accountId}/oauth/init`, { method: "POST" })
          .then(({ connect_url }) => setConnectUrl(connect_url))
          .catch(() => {})
          .finally(() => setLoading(false));
      });
  }, [open, accountId]);

  if (!open || !accountId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-xl">
        <div className="text-lg font-semibold">Connect LinkedIn</div>
        <div className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">
          Use the Automation connect method to enable lead extraction, connection requests, and messages.
        </div>

        {error ? (
          <div className="mt-4">
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
              {error}
            </div>
          </div>
        ) : null}

        {loading ? <div className="mt-4 text-sm text-zinc-500">Preparing connect links...</div> : null}

        <div className="mt-6 flex items-center justify-end gap-2">
          <Button variant="secondary" disabled={loading} onClick={onClose}>
            Close
          </Button>
          {connectUrl ? (
            <a href={connectUrl} target="_blank" rel="noreferrer">
              <Button variant="secondary">OAuth (optional)</Button>
            </a>
          ) : null}
          {cookieConnectUrl ? (
            <a href={cookieConnectUrl} target="_blank" rel="noreferrer">
              <Button
                onClick={() =>
                  setTimeout(() => {
                    onDone();
                    onClose();
                  }, 1000)
                }
              >
                Connect for Automation
              </Button>
            </a>
          ) : null}
        </div>
      </div>
    </div>
  );
}
