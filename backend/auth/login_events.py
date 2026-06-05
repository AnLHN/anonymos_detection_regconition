from fastapi import Request

from backend.database.postgres import execute, fetch_all


LOGIN_EVENT_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_login_events (
    id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    action TEXT NOT NULL,
    success BOOLEAN NOT NULL DEFAULT true,
    ip_address TEXT,
    user_agent TEXT,
    device_os TEXT,
    browser TEXT,
    location TEXT,
    isp TEXT,
    is_vpn BOOLEAN,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_user_login_events_user_created
ON user_login_events (username, created_at DESC);
"""


def ensure_login_event_schema() -> None:
    execute(LOGIN_EVENT_SCHEMA)


def write_login_event(username: str, action: str, success: bool, request: Request) -> None:
    try:
        ensure_login_event_schema()
        client_ip = request_ip(request)
        user_agent = request.headers.get("user-agent", "")
        device_os = detect_os(user_agent)
        browser = detect_browser(user_agent)
        location = "Local network" if is_private_ip(client_ip) else None
        execute(
            """
            INSERT INTO user_login_events
                (username, action, success, ip_address, user_agent, device_os, browser, location, isp, is_vpn)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (username or "unknown", action, success, client_ip, user_agent, device_os, browser, location, None, None),
        )
    except Exception:
        # Auth must keep working even when audit storage is temporarily unavailable.
        pass


def read_login_events(username: str, limit: int) -> list[dict]:
    ensure_login_event_schema()
    return fetch_all(
        """
        SELECT action, success, ip_address, user_agent, device_os, browser, location, isp, is_vpn, created_at
        FROM user_login_events
        WHERE username = %s
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (username, limit),
    )


def request_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip() or None
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else None


def is_private_ip(ip_address: str | None) -> bool:
    if not ip_address:
        return False
    return (
        ip_address.startswith("10.")
        or ip_address.startswith("192.168.")
        or ip_address.startswith("172.16.")
        or ip_address.startswith("172.17.")
        or ip_address.startswith("172.18.")
        or ip_address.startswith("172.19.")
        or ip_address.startswith("172.2")
        or ip_address in {"127.0.0.1", "::1"}
    )


def detect_os(user_agent: str) -> str | None:
    value = user_agent.lower()
    if "windows" in value:
        return "Windows"
    if "android" in value:
        return "Android"
    if "iphone" in value or "ipad" in value or "ios" in value:
        return "iOS"
    if "mac os" in value or "macintosh" in value:
        return "macOS"
    if "linux" in value:
        return "Linux"
    return None


def detect_browser(user_agent: str) -> str | None:
    value = user_agent.lower()
    if "edg/" in value:
        return "Edge"
    if "chrome/" in value and "chromium" not in value:
        return "Chrome"
    if "firefox/" in value:
        return "Firefox"
    if "safari/" in value and "chrome/" not in value:
        return "Safari"
    return None
