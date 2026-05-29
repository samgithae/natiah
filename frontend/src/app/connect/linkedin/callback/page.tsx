"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Shell } from "@/components/Shell";
import { Button, Card } from "@/components/ui";

function CallbackContent() {
  const params = useSearchParams();
  const success = params.get("success");
  const error = params.get("error");
  const accountId = params.get("account_id");
  const name = params.get("name");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (success && accountId) {
      localStorage.setItem("li_connect_success", `1:${accountId}:${name || ""}`);
    }
  }, [success, accountId, name]);

  if (success) {
    return (
      <Shell>
        <div className="flex flex-col items-center justify-center gap-6 py-16 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
            <svg className="h-8 w-8 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <div>
            <h1 className="text-2xl font-bold">LinkedIn Account Connected!</h1>
            <p className="mt-2 text-zinc-600 dark:text-zinc-300">
              {name ? `"${name}"` : "Your LinkedIn account"} has been successfully connected to Natiah.
            </p>
          </div>
          <div className="w-full max-w-md rounded-xl border border-border bg-muted p-4 text-sm text-zinc-600 dark:text-zinc-300">
            <p>
              <strong>Next steps:</strong> Go back to the Accounts page to manage your LinkedIn account, set daily limits, and start outreach campaigns.
            </p>
          </div>
          <div className="flex gap-3">
            <a href="/accounts">
              <Button>Go to Accounts</Button>
            </a>
            <Button
              variant="secondary"
              onClick={() => {
                navigator.clipboard.writeText(window.location.href).catch(() => {});
                setCopied(true);
              }}
            >
              {copied ? "Copied!" : "Copy Success Link"}
            </Button>
          </div>
        </div>
      </Shell>
    );
  }

  const errorMessages: Record<string, string> = {
    state_not_found: "Authorization state expired. Please try connecting again.",
    state_mismatch: "State verification failed. Please try connecting again.",
    account_not_found: "Account not found. Please try again from the Accounts page.",
    invalid_state_file: "Internal error. Please try connecting again.",
    token_exchange_failed:
      "LinkedIn token exchange failed. Check your LinkedIn app Client ID/Secret and redirect URL, then try again.",
    invalid_redirect_uri:
      "LinkedIn rejected the redirect URL. Make sure this exact URL is added in your LinkedIn app: http://localhost:8000/api/v1/accounts/oauth/callback",
    invalid_client:
      "LinkedIn rejected the client credentials. Check LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET and try again.",
    unauthorized_scope:
      "LinkedIn rejected one of the requested permissions/scopes. Try without w_member_social or request LinkedIn approval for it.",
    userinfo_failed:
      "Connected to LinkedIn, but failed to fetch profile info. Try again; if it persists, verify your app has openid/profile/email enabled.",
    missing_code: "LinkedIn did not return an authorization code. Please try connecting again.",
  };

  return (
    <Shell>
      <div className="flex flex-col items-center justify-center gap-6 py-16 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-red-100 dark:bg-red-900">
          <svg className="h-8 w-8 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <div>
          <h1 className="text-2xl font-bold">Connection Failed</h1>
          <p className="mt-2 text-zinc-600 dark:text-zinc-300">
            {error ? errorMessages[error] || `Error: ${error}` : "An unknown error occurred."}
          </p>
        </div>
        <a href="/accounts">
          <Button variant="secondary">Back to Accounts</Button>
        </a>
      </div>
    </Shell>
  );
}

export default function LinkedInCallbackPage() {
  return (
    <Suspense fallback={
      <Shell>
        <div className="flex items-center justify-center py-16 text-zinc-500">Loading...</div>
      </Shell>
    }>
      <CallbackContent />
    </Suspense>
  );
}
