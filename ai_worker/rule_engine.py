from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any

import psycopg
from psycopg.rows import dict_row

from config import (
    GATE_ZONES,
    POSTGRES_DSN,
    RESTRICTED_ZONES,
    UNKNOWN_ALERT_COOLDOWN_SECONDS,
    UNKNOWN_GATE_WARNING_FRAMES,
    UNKNOWN_STABLE_FRAMES,
    UNKNOWN_STABLE_SECONDS,
    WORKING_HOUR_END,
    WORKING_HOUR_START,
)
from tracker import Track


@dataclass(frozen=True)
class RuleDecision:
    should_alert: bool
    warning_type: str
    warning_level: str
    reason: str
    cooldown_seconds: int | None = None
    rule_config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AlertRule:
    rule_code: str
    warning_level: str
    is_enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)

    def get_int(self, key: str, default: int) -> int:
        return int(self.config.get(key, default))

    def get_float(self, key: str, default: float) -> float:
        return float(self.config.get(key, default))

    def get_str(self, key: str, default: str) -> str:
        return str(self.config.get(key, default))

    def get_list(self, key: str, default: list[str]) -> list[str]:
        value = self.config.get(key, default)
        if isinstance(value, list):
            return [str(item) for item in value]
        return default


DEFAULT_RULES = {
    "unknown_entered_restricted_area": AlertRule(
        rule_code="unknown_entered_restricted_area",
        warning_level="critical",
        config={"restricted_zones": RESTRICTED_ZONES},
    ),
    "unknown_outside_working_hours": AlertRule(
        rule_code="unknown_outside_working_hours",
        warning_level="high",
        config={"start": WORKING_HOUR_START, "end": WORKING_HOUR_END},
    ),
    "unknown_loitering_at_gate": AlertRule(
        rule_code="unknown_loitering_at_gate",
        warning_level="medium",
        config={"gate_zones": GATE_ZONES, "frames": UNKNOWN_GATE_WARNING_FRAMES},
    ),
    "stable_unknown_face": AlertRule(
        rule_code="stable_unknown_face",
        warning_level="low",
        config={
            "stable_seconds": UNKNOWN_STABLE_SECONDS,
            "legacy_stable_frames": UNKNOWN_STABLE_FRAMES,
            "cooldown_seconds": UNKNOWN_ALERT_COOLDOWN_SECONDS,
        },
    ),
    "unverified_in_restricted_area": AlertRule(
        rule_code="unverified_in_restricted_area",
        warning_level="medium",
        config={"restricted_zones": RESTRICTED_ZONES},
    ),
}


class RuleEngine:
    def __init__(self) -> None:
        self.rules = load_alert_rules()

    def evaluate_track(self, track: Track, current_time: datetime | None = None) -> RuleDecision:
        current_time = current_time or datetime.now()
        status = track.voted_status()
        zone = track.zone

        rule = self.rules["unknown_entered_restricted_area"]
        restricted_zones = rule.get_list("restricted_zones", RESTRICTED_ZONES)
        if rule.is_enabled and status == "unknown" and zone in restricted_zones:
            return alert_decision(
                rule,
                reason=f"Unknown track {track.track_id} entered restricted zone {zone}",
            )

        rule = self.rules["unknown_outside_working_hours"]
        start = rule.get_str("start", WORKING_HOUR_START)
        end = rule.get_str("end", WORKING_HOUR_END)
        if rule.is_enabled and status == "unknown" and not is_working_hour(current_time.time(), start, end):
            return alert_decision(
                rule,
                reason=f"Unknown track {track.track_id} appeared outside working hours",
            )

        rule = self.rules["unknown_loitering_at_gate"]
        gate_zones = rule.get_list("gate_zones", GATE_ZONES)
        frames = rule.get_int("frames", UNKNOWN_GATE_WARNING_FRAMES)
        if rule.is_enabled and status == "unknown" and zone in gate_zones and len(track.history) >= frames:
            return alert_decision(
                rule,
                reason=f"Unknown track {track.track_id} stayed in gate zone for {len(track.history)} processed frames",
            )

        rule = self.rules["stable_unknown_face"]
        stable_seconds = rule.get_float("stable_seconds", UNKNOWN_STABLE_SECONDS)
        now_seconds = current_time.timestamp()
        known_count = count_status(track, "known")
        if (
            rule.is_enabled
            and not track.unknown_alert_sent
            and track.is_unknown_stable(now_seconds, stable_seconds)
            and known_count == 0
        ):
            return alert_decision(
                rule,
                reason=f"Track {track.track_id} stayed unknown for at least {stable_seconds:.1f}s",
            )

        rule = self.rules["unverified_in_restricted_area"]
        restricted_zones = rule.get_list("restricted_zones", RESTRICTED_ZONES)
        if rule.is_enabled and status == "unverified" and zone in restricted_zones:
            return alert_decision(
                rule,
                reason=f"Unverified track {track.track_id} appeared in restricted zone {zone}",
            )

        return RuleDecision(
            should_alert=False,
            warning_type="none",
            warning_level="none",
            reason="No alert rule matched",
        )


def alert_decision(rule: AlertRule, reason: str) -> RuleDecision:
    cooldown = rule.config.get("cooldown_seconds")
    return RuleDecision(
        should_alert=True,
        warning_type=rule.rule_code,
        warning_level=rule.warning_level,
        reason=reason,
        cooldown_seconds=int(cooldown) if cooldown is not None else None,
        rule_config=rule.config,
    )


def count_status(track: Track, status: str) -> int:
    return sum(1 for result in track.history if result.recognition.status == status)


def is_working_hour(value: time, start_value: str, end_value: str) -> bool:
    start = parse_hhmm(start_value)
    end = parse_hhmm(end_value)
    return start <= value <= end


def load_alert_rules() -> dict[str, AlertRule]:
    rules = dict(DEFAULT_RULES)
    try:
        with psycopg.connect(POSTGRES_DSN, row_factory=dict_row, connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT rule_code, warning_level, is_enabled, config FROM alert_rules")
                for row in cur.fetchall():
                    if row["rule_code"] in rules:
                        rules[row["rule_code"]] = AlertRule(
                            rule_code=row["rule_code"],
                            warning_level=row["warning_level"],
                            is_enabled=row["is_enabled"],
                            config=row["config"] or {},
                        )
    except psycopg.Error:
        return rules
    return rules


def parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(hour=int(hour), minute=int(minute))
