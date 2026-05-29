import base64
import hashlib
import secrets
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.core.config import settings


LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_API_URL = "https://api.linkedin.com/v2"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
LINKEDIN_TOKEN_INFO_URL = "https://api.linkedin.com/oauth/v2/introspectToken"


def generate_pkce_pair() -> tuple[str, str]:
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


@dataclass
class LinkedInTokenData:
    access_token: str
    refresh_token: str | None
    expires_in: int
    scope: str


def build_authorization_url(
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    scopes: list[str],
) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "scope": " ".join(scopes),
    }
    return f"{LINKEDIN_AUTH_URL}?{urllib.parse.urlencode(params)}"


async def exchange_code_for_token(
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    code_verifier: str | None,
) -> LinkedInTokenData:
    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as client:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        if code_verifier:
            data["code_verifier"] = code_verifier
        resp = await client.post(LINKEDIN_TOKEN_URL, data=data)
        if resp.status_code >= 400:
            raise RuntimeError(f"LinkedIn token exchange failed ({resp.status_code}): {resp.text}")
        data = resp.json()
        return LinkedInTokenData(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_in=data.get("expires_in", 5184000),
            scope=data.get("scope", ""),
        )


async def fetch_linkedin_userinfo(access_token: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as client:
        resp = await client.get(LINKEDIN_USERINFO_URL, headers=headers)
        if resp.status_code >= 400:
            raise RuntimeError(f"LinkedIn userinfo failed: {resp.text}")
        return resp.json()


async def introspect_token(access_token: str, client_id: str, client_secret: str) -> dict:
    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as client:
        resp = await client.post(
            LINKEDIN_TOKEN_INFO_URL,
            data={"token": access_token, "client_id": client_id, "client_secret": client_secret},
        )
        if resp.status_code >= 400:
            return {}
        return resp.json()


def token_expiry_time(expires_in: int) -> datetime:
    from datetime import timedelta
    return datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=expires_in)


def get_linkedin_scopes() -> list[str]:
    raw = getattr(settings, "linkedin_scopes", None) or ""
    if not raw:
        return ["openid", "profile", "email"]
    return [s.strip() for s in raw.split(",") if s.strip()]
