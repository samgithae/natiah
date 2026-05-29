from __future__ import annotations

from typing import Literal


JobType = Literal[
    "LOGIN",
    "CONNECT",
    "VISIT_PROFILE",
    "SEND_FOLLOW_UP",
    "MONITOR_INBOX",
    "SCRAPE_SALES_NAVIGATOR",
]

