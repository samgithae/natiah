"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Shell } from "@/components/Shell";
import { useToast } from "@/components/Toaster";
import { Button, Card, Input, Textarea } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import { clearToken, getToken } from "@/lib/auth";
import { getTheme, setTheme, type ThemeMode } from "@/lib/theme";

type MauticSettings = {
  mautic_url: string;
  username: string | null;
  password_set: boolean;
  api_token_set: boolean;
};

type EmailKeys = {
  hunter_api_key_set: boolean;
  apollo_api_key_set: boolean;
  prospeo_api_key_set: boolean;
};

type AppSettings = {
  default_account_daily_limit: number;
  max_connections_per_day: number;
  max_messages_per_day: number;
  max_profile_visits_per_day: number;
  delay_min_ms: number;
  delay_max_ms: number;
  proxy_url: string | null;
  proxy_username: string | null;
  proxy_password_set: boolean;
  work_start_min_hour: number;
  work_start_max_hour: number;
  work_end_min_hour: number;
  work_end_max_hour: number;
  campaign_timezone: string;
  campaign_work_days: number[];
  campaign_start_hour: number;
  campaign_end_hour: number;
  blacklist_domains: string[];
  blacklist_linkedin_urls: string[];
};

export default function SettingsPage() {
  const router = useRouter();
  const toast = useToast();
  const [theme, setThemeState] = useState<ThemeMode>("light");
  const token = getToken();
  const [mauticUrl, setMauticUrl] = useState("");
  const [mauticUsername, setMauticUsername] = useState("");
  const [mauticPassword, setMauticPassword] = useState("");
  const [mauticToken, setMauticToken] = useState("");
  const [mauticStatus, setMauticStatus] = useState<MauticSettings | null>(null);
  const [mauticError, setMauticError] = useState<string | null>(null);
  const [emailStatus, setEmailStatus] = useState<EmailKeys | null>(null);
  const [hunterKey, setHunterKey] = useState("");
  const [apolloKey, setApolloKey] = useState("");
  const [prospeoKey, setProspeoKey] = useState("");

  const [appSettings, setAppSettings] = useState<AppSettings | null>(null);
  const [appError, setAppError] = useState<string | null>(null);
  const [defaultDailyLimit, setDefaultDailyLimit] = useState("50");
  const [maxConnections, setMaxConnections] = useState("30");
  const [maxMessages, setMaxMessages] = useState("60");
  const [maxVisits, setMaxVisits] = useState("80");
  const [delayMinMs, setDelayMinMs] = useState("400");
  const [delayMaxMs, setDelayMaxMs] = useState("1600");
  const [proxyUrl, setProxyUrl] = useState("");
  const [proxyUsername, setProxyUsername] = useState("");
  const [proxyPassword, setProxyPassword] = useState("");
  const [workStartMin, setWorkStartMin] = useState("8");
  const [workStartMax, setWorkStartMax] = useState("11");
  const [workEndMin, setWorkEndMin] = useState("16");
  const [workEndMax, setWorkEndMax] = useState("21");
  const [campaignTz, setCampaignTz] = useState("UTC");
  const [campaignDays, setCampaignDays] = useState("1,2,3,4,5");
  const [campaignStartHour, setCampaignStartHour] = useState("9");
  const [campaignEndHour, setCampaignEndHour] = useState("17");
  const [blacklistDomains, setBlacklistDomains] = useState("");
  const [blacklistLinkedInUrls, setBlacklistLinkedInUrls] = useState("");

  useEffect(() => {
    setThemeState(getTheme());
  }, []);

  useEffect(() => {
    apiFetch<MauticSettings>("/integrations/mautic/settings")
      .then((s) => {
        setMauticStatus(s);
        setMauticUrl(s.mautic_url);
        setMauticUsername(s.username || "");
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    apiFetch<EmailKeys>("/integrations/email-enrichment/settings")
      .then(setEmailStatus)
      .catch(() => {});
  }, []);

  useEffect(() => {
    apiFetch<AppSettings>("/settings")
      .then((s) => {
        setAppSettings(s);
        setDefaultDailyLimit(String(s.default_account_daily_limit));
        setMaxConnections(String(s.max_connections_per_day));
        setMaxMessages(String(s.max_messages_per_day));
        setMaxVisits(String(s.max_profile_visits_per_day));
        setDelayMinMs(String(s.delay_min_ms));
        setDelayMaxMs(String(s.delay_max_ms));
        setProxyUrl(s.proxy_url || "");
        setProxyUsername(s.proxy_username || "");
        setWorkStartMin(String(s.work_start_min_hour));
        setWorkStartMax(String(s.work_start_max_hour));
        setWorkEndMin(String(s.work_end_min_hour));
        setWorkEndMax(String(s.work_end_max_hour));
        setCampaignTz(s.campaign_timezone || "UTC");
        setCampaignDays((s.campaign_work_days || []).join(","));
        setCampaignStartHour(String(s.campaign_start_hour));
        setCampaignEndHour(String(s.campaign_end_hour));
        setBlacklistDomains((s.blacklist_domains || []).join("\n"));
        setBlacklistLinkedInUrls((s.blacklist_linkedin_urls || []).join("\n"));
      })
      .catch(() => {});
  }, []);

  async function saveEmailKeys() {
    try {
      const payload: Record<string, unknown> = {};
      if (hunterKey.trim().length > 0) payload.hunter_api_key = hunterKey.trim();
      if (apolloKey.trim().length > 0) payload.apollo_api_key = apolloKey.trim();
      if (prospeoKey.trim().length > 0) payload.prospeo_api_key = prospeoKey.trim();
      const s = await apiFetch<EmailKeys>("/integrations/email-enrichment/settings", {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      setEmailStatus(s);
      setHunterKey("");
      setApolloKey("");
      setProspeoKey("");
      toast.success("Email API keys saved");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed";
      toast.error("Failed to save email API keys", msg);
    }
  }

  async function saveAppSettings() {
    setAppError(null);
    try {
      const payload: Record<string, unknown> = {
        default_account_daily_limit: Number(defaultDailyLimit || "0"),
        max_connections_per_day: Number(maxConnections || "0"),
        max_messages_per_day: Number(maxMessages || "0"),
        max_profile_visits_per_day: Number(maxVisits || "0"),
        delay_min_ms: Number(delayMinMs || "0"),
        delay_max_ms: Number(delayMaxMs || "0"),
        proxy_url: proxyUrl.trim().length > 0 ? proxyUrl.trim() : null,
        proxy_username: proxyUsername.trim().length > 0 ? proxyUsername.trim() : null,
        work_start_min_hour: Number(workStartMin || "0"),
        work_start_max_hour: Number(workStartMax || "0"),
        work_end_min_hour: Number(workEndMin || "0"),
        work_end_max_hour: Number(workEndMax || "0"),
        campaign_timezone: campaignTz.trim().length > 0 ? campaignTz.trim() : "UTC",
        campaign_work_days: campaignDays
          .split(",")
          .map((x) => x.trim())
          .filter(Boolean)
          .map((x) => Number(x)),
        campaign_start_hour: Number(campaignStartHour || "0"),
        campaign_end_hour: Number(campaignEndHour || "0"),
        blacklist_domains: blacklistDomains
          .split("\n")
          .map((x) => x.trim())
          .filter(Boolean),
        blacklist_linkedin_urls: blacklistLinkedInUrls
          .split("\n")
          .map((x) => x.trim())
          .filter(Boolean),
      };
      if (proxyPassword.trim().length > 0) payload.proxy_password = proxyPassword;

      const s = await apiFetch<AppSettings>("/settings", { method: "PUT", body: JSON.stringify(payload) });
      setAppSettings(s);
      setProxyPassword("");
      toast.success("Settings saved");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed";
      setAppError(msg);
      toast.error("Failed to save settings", msg);
    }
  }

  async function saveMautic() {
    setMauticError(null);
    try {
      const payload: Record<string, unknown> = {
        mautic_url: mauticUrl,
        username: mauticUsername || null,
      };
      if (mauticPassword.trim().length > 0) payload.password = mauticPassword;
      if (mauticToken.trim().length > 0) payload.api_token = mauticToken;

      const s = await apiFetch<MauticSettings>("/integrations/mautic/settings", {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      setMauticStatus(s);
      setMauticPassword("");
      setMauticToken("");
      toast.success("Mautic settings saved");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed";
      setMauticError(msg);
      toast.error("Failed to save Mautic settings", msg);
    }
  }

  return (
    <Shell>
      <div className="flex items-baseline justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card title="Appearance">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-sm font-medium">Theme</div>
              <div className="mt-1 text-sm text-zinc-600 dark:text-zinc-300">
                Toggle between light and dark mode.
              </div>
            </div>
            <Button
              variant="secondary"
              onClick={() => {
                const next: ThemeMode = theme === "dark" ? "light" : "dark";
                setTheme(next);
                setThemeState(next);
                toast.success("Theme updated");
              }}
            >
              {theme === "dark" ? "Dark" : "Light"}
            </Button>
          </div>
        </Card>

        <Card title="Account">
          <div className="text-sm text-zinc-600 dark:text-zinc-300">
            API: {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}
          </div>
          <div className="mt-4 flex items-center justify-between gap-3">
            <div className="text-sm text-zinc-600 dark:text-zinc-300">
              {token ? "Authenticated" : "Not authenticated"}
            </div>
            <Button
              variant="secondary"
              onClick={() => {
                clearToken();
                toast.success("Logged out");
                router.push("/login");
              }}
            >
              Logout
            </Button>
          </div>
        </Card>

        <Card title="Mautic">
          <div className="text-sm text-zinc-600 dark:text-zinc-300">
            Configure your Mautic instance for lead sync.
          </div>
          <div className="mt-4 space-y-4">
            <div>
              <div className="text-sm font-medium">Mautic URL</div>
              <div className="mt-1">
                <Input value={mauticUrl} onChange={setMauticUrl} placeholder="https://mautic.example.com" />
              </div>
            </div>
            <div>
              <div className="text-sm font-medium">Username</div>
              <div className="mt-1">
                <Input value={mauticUsername} onChange={setMauticUsername} placeholder="optional" />
              </div>
            </div>
            <div>
              <div className="text-sm font-medium">Password</div>
              <div className="mt-1">
                <Input value={mauticPassword} onChange={setMauticPassword} type="password" placeholder="set / update" />
              </div>
              <div className="mt-1 text-xs text-zinc-600 dark:text-zinc-300">
                Stored on the server. Current: {mauticStatus?.password_set ? "set" : "not set"}.
              </div>
            </div>
            <div>
              <div className="text-sm font-medium">API token</div>
              <div className="mt-1">
                <Input value={mauticToken} onChange={setMauticToken} type="password" placeholder="set / update" />
              </div>
              <div className="mt-1 text-xs text-zinc-600 dark:text-zinc-300">
                If provided, token auth is used. Current: {mauticStatus?.api_token_set ? "set" : "not set"}.
              </div>
            </div>
            {mauticError ? <div className="text-sm text-red-600">{mauticError}</div> : null}
            <div className="flex items-center justify-end">
              <Button variant="secondary" onClick={saveMautic}>
                Save
              </Button>
            </div>
          </div>
        </Card>

        <Card title="Email API keys">
          <div className="text-sm text-zinc-600 dark:text-zinc-300">
            Configure Hunter, Apollo, and Prospeo keys for email enrichment.
          </div>
          <div className="mt-4 space-y-4">
            <div>
              <div className="text-sm font-medium">Hunter API key</div>
              <div className="mt-1">
                <Input value={hunterKey} onChange={setHunterKey} type="password" placeholder="set / update" />
              </div>
              <div className="mt-1 text-xs text-zinc-600 dark:text-zinc-300">
                Current: {emailStatus?.hunter_api_key_set ? "set" : "not set"}.
              </div>
            </div>
            <div>
              <div className="text-sm font-medium">Apollo API key</div>
              <div className="mt-1">
                <Input value={apolloKey} onChange={setApolloKey} type="password" placeholder="set / update" />
              </div>
              <div className="mt-1 text-xs text-zinc-600 dark:text-zinc-300">
                Current: {emailStatus?.apollo_api_key_set ? "set" : "not set"}.
              </div>
            </div>
            <div>
              <div className="text-sm font-medium">Prospeo API key</div>
              <div className="mt-1">
                <Input value={prospeoKey} onChange={setProspeoKey} type="password" placeholder="set / update" />
              </div>
              <div className="mt-1 text-xs text-zinc-600 dark:text-zinc-300">
                Current: {emailStatus?.prospeo_api_key_set ? "set" : "not set"}.
              </div>
            </div>
            <div className="flex items-center justify-end">
              <Button variant="secondary" onClick={saveEmailKeys}>
                Save
              </Button>
            </div>
          </div>
        </Card>

        <Card title="Automation settings">
          <div className="text-sm text-zinc-600 dark:text-zinc-300">
            Global defaults used by the rotation and anti-detection logic.
          </div>
          <div className="mt-4 space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <div className="text-sm font-medium">Default daily limit (per account)</div>
                <div className="mt-1">
                  <Input value={defaultDailyLimit} onChange={setDefaultDailyLimit} placeholder="50" />
                </div>
              </div>
              <div>
                <div className="text-sm font-medium">Max connections/day</div>
                <div className="mt-1">
                  <Input value={maxConnections} onChange={setMaxConnections} placeholder="30" />
                </div>
              </div>
              <div>
                <div className="text-sm font-medium">Max messages/day</div>
                <div className="mt-1">
                  <Input value={maxMessages} onChange={setMaxMessages} placeholder="60" />
                </div>
              </div>
              <div>
                <div className="text-sm font-medium">Max profile visits/day</div>
                <div className="mt-1">
                  <Input value={maxVisits} onChange={setMaxVisits} placeholder="80" />
                </div>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <div className="text-sm font-medium">Delay min (ms)</div>
                <div className="mt-1">
                  <Input value={delayMinMs} onChange={setDelayMinMs} placeholder="400" />
                </div>
              </div>
              <div>
                <div className="text-sm font-medium">Delay max (ms)</div>
                <div className="mt-1">
                  <Input value={delayMaxMs} onChange={setDelayMaxMs} placeholder="1600" />
                </div>
              </div>
            </div>

            <div>
              <div className="text-sm font-medium">Working hours (UTC)</div>
              <div className="mt-2 grid gap-4 md:grid-cols-4">
                <div>
                  <div className="text-xs text-zinc-600 dark:text-zinc-300">Start min</div>
                  <Input value={workStartMin} onChange={setWorkStartMin} placeholder="8" />
                </div>
                <div>
                  <div className="text-xs text-zinc-600 dark:text-zinc-300">Start max</div>
                  <Input value={workStartMax} onChange={setWorkStartMax} placeholder="11" />
                </div>
                <div>
                  <div className="text-xs text-zinc-600 dark:text-zinc-300">End min</div>
                  <Input value={workEndMin} onChange={setWorkEndMin} placeholder="16" />
                </div>
                <div>
                  <div className="text-xs text-zinc-600 dark:text-zinc-300">End max</div>
                  <Input value={workEndMax} onChange={setWorkEndMax} placeholder="21" />
                </div>
              </div>
            </div>

            <div>
              <div className="text-sm font-medium">Proxy</div>
              <div className="mt-2 space-y-3">
                <Input value={proxyUrl} onChange={setProxyUrl} placeholder="http://host:port" />
                <Input value={proxyUsername} onChange={setProxyUsername} placeholder="username (optional)" />
                <Input value={proxyPassword} onChange={setProxyPassword} type="password" placeholder="password (set / update)" />
                <div className="text-xs text-zinc-600 dark:text-zinc-300">
                  Current password: {appSettings?.proxy_password_set ? "set" : "not set"}.
                </div>
              </div>
            </div>

            <div>
              <div className="text-sm font-medium">Campaign schedule (defaults)</div>
              <div className="mt-2 grid gap-4 md:grid-cols-2">
                <div>
                  <div className="text-xs text-zinc-600 dark:text-zinc-300">Timezone</div>
                  <Input value={campaignTz} onChange={setCampaignTz} placeholder="UTC" />
                </div>
                <div>
                  <div className="text-xs text-zinc-600 dark:text-zinc-300">Work days (0-6)</div>
                  <Input value={campaignDays} onChange={setCampaignDays} placeholder="1,2,3,4,5" />
                </div>
                <div>
                  <div className="text-xs text-zinc-600 dark:text-zinc-300">Start hour</div>
                  <Input value={campaignStartHour} onChange={setCampaignStartHour} placeholder="9" />
                </div>
                <div>
                  <div className="text-xs text-zinc-600 dark:text-zinc-300">End hour</div>
                  <Input value={campaignEndHour} onChange={setCampaignEndHour} placeholder="17" />
                </div>
              </div>
            </div>

            <div>
              <div className="text-sm font-medium">Blacklists</div>
              <div className="mt-2 grid gap-4 md:grid-cols-2">
                <div>
                  <div className="text-xs text-zinc-600 dark:text-zinc-300">Domains (one per line)</div>
                  <Textarea value={blacklistDomains} onChange={setBlacklistDomains} placeholder="example.com" rows={6} />
                </div>
                <div>
                  <div className="text-xs text-zinc-600 dark:text-zinc-300">LinkedIn URLs (one per line)</div>
                  <Textarea
                    value={blacklistLinkedInUrls}
                    onChange={setBlacklistLinkedInUrls}
                    placeholder="https://www.linkedin.com/in/..."
                    rows={6}
                  />
                </div>
              </div>
            </div>

            {appError ? <div className="text-sm text-red-600">{appError}</div> : null}
            <div className="flex items-center justify-end">
              <Button variant="secondary" onClick={saveAppSettings}>
                Save
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </Shell>
  );
}
