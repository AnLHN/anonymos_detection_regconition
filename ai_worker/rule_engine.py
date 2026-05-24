from dataclasses import dataclass
from datetime import datetime, time

from config import GATE_ZONES, RESTRICTED_ZONES, UNKNOWN_GATE_WARNING_FRAMES, WORKING_HOUR_END, WORKING_HOUR_START
from tracker import Track


@dataclass(frozen=True)
class RuleDecision:
    should_alert: bool
    warning_type: str
    warning_level: str
    reason: str


class RuleEngine:
    def evaluate_track(self, track: Track, current_time: datetime | None = None) -> RuleDecision:
        current_time = current_time or datetime.now()
        status = track.voted_status()
        zone = track.zone

        if status == "unknown" and zone in RESTRICTED_ZONES:
            return RuleDecision(
                should_alert=True,
                warning_type="unknown_entered_restricted_area",
                warning_level="critical",
                reason=f"Unknown track {track.track_id} entered restricted zone {zone}",
            )

        if status == "unknown" and not is_working_hour(current_time.time()):
            return RuleDecision(
                should_alert=True,
                warning_type="unknown_outside_working_hours",
                warning_level="high",
                reason=f"Unknown track {track.track_id} appeared outside working hours",
            )

        if status == "unknown" and zone in GATE_ZONES and len(track.history) >= UNKNOWN_GATE_WARNING_FRAMES:
            return RuleDecision(
                should_alert=True,
                warning_type="unknown_loitering_at_gate",
                warning_level="medium",
                reason=f"Unknown track {track.track_id} stayed in gate zone for {len(track.history)} processed frames",
            )

        if status == "unknown":
            return RuleDecision(
                should_alert=True,
                warning_type="stable_unknown_face",
                warning_level="low",
                reason=f"Track {track.track_id} voted unknown after {len(track.history)} processed frames",
            )

        if status == "unverified" and zone in RESTRICTED_ZONES:
            return RuleDecision(
                should_alert=True,
                warning_type="unverified_in_restricted_area",
                warning_level="medium",
                reason=f"Unverified track {track.track_id} appeared in restricted zone {zone}",
            )

        return RuleDecision(
            should_alert=False,
            warning_type="none",
            warning_level="none",
            reason="No alert rule matched",
        )


def is_working_hour(value: time) -> bool:
    start = parse_hhmm(WORKING_HOUR_START)
    end = parse_hhmm(WORKING_HOUR_END)
    return start <= value <= end


def parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(hour=int(hour), minute=int(minute))
