"""User-agent parser adapter."""

from __future__ import annotations

from dataclasses import dataclass

from ua_parser import user_agent_parser


@dataclass(slots=True)
class UserAgentData:
    """Normalized user-agent enrichment output."""

    browser: str | None
    os: str | None
    device: str | None
    is_bot: bool


def parse_user_agent(user_agent: str | None) -> UserAgentData:
    """Parse user-agent string into browser, OS, and device dimensions."""
    if not user_agent:
        return UserAgentData(browser=None, os=None, device=None, is_bot=False)

    parsed = user_agent_parser.Parse(user_agent)
    browser = parsed.get("user_agent", {}).get("family")
    os_name = parsed.get("os", {}).get("family")
    device_family = parsed.get("device", {}).get("family")
    is_bot = "bot" in user_agent.lower()

    return UserAgentData(
        browser=_clean(browser),
        os=_clean(os_name),
        device=_clean(device_family),
        is_bot=is_bot,
    )


def _clean(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None

