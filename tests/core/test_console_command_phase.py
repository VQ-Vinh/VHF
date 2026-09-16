from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from prana_core.console.command_phase import (
    CommandPhase,
    CommandState,
    begin_send,
    can_toggle,
    reduce,
    sent,
)
from prana_core.console.models import StationSummary

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)


def station(**overrides) -> StationSummary:
    data = {
        "station_id": "a" * 32,
        "name": "Bridge Pi",
        "active": True,
        "last_seen_at": (NOW - timedelta(seconds=2)).isoformat(),
        "observed_generation": 1,
        "desired_state": {"generation": 1, "running": True},
    }
    data.update(overrides)
    return StationSummary.from_wire(data)


class CommandPhaseTests(unittest.TestCase):
    def test_awaiting_becomes_applied_once_the_station_catches_up(self):
        state = sent(begin_send(CommandState(), station(desired_state={"generation": 1})))
        self.assertEqual(state.baseline_generation, 1)
        pending = station(observed_generation=1, desired_state={"generation": 2})
        self.assertEqual(reduce(state, pending, NOW).phase, CommandPhase.AWAITING_STATION)
        caught_up = station(observed_generation=2, desired_state={"generation": 2})
        self.assertEqual(reduce(state, caught_up, NOW).phase, CommandPhase.APPLIED)

    def test_station_reported_failure_wins_over_awaiting(self):
        state = sent(begin_send(CommandState(), station()))
        failed = station(
            observed_generation=2,
            desired_state={"generation": 2},
            command_failed_generation=2,
            command_error="AUDIO_INPUT_DEVICE_NOT_FOUND",
        )
        result = reduce(state, failed, NOW)
        self.assertEqual(result.phase, CommandPhase.FAILED)
        self.assertEqual(result.error, "AUDIO_INPUT_DEVICE_NOT_FOUND")
        self.assertIsNone(result.pending_running)

    def test_offline_clears_a_pending_command(self):
        state = sent(begin_send(CommandState(), station(), running=True))
        offline = station(last_seen_at=(NOW - timedelta(minutes=5)).isoformat())
        result = reduce(state, offline, NOW)
        self.assertEqual(result.phase, CommandPhase.OFFLINE)
        self.assertIsNone(result.pending_running)

    def test_view_only_outranks_offline_and_failure(self):
        """A console without the lease cannot land anything, so say so first."""
        lease = {
            "holder_uid": "other-operator",
            "holder_kind": "operator",
            "expires_at": (NOW + timedelta(seconds=60)).isoformat(),
            "epoch": 4,
        }
        seized = station(
            control_lease=lease,
            last_seen_at=(NOW - timedelta(minutes=5)).isoformat(),
            command_error="rx_start_failed",
            command_failed_generation=9,
        )
        state = sent(begin_send(CommandState(), station(), running=True))
        result = reduce(state, seized, NOW, holder_uid="me")
        self.assertEqual(result.phase, CommandPhase.VIEW_ONLY)
        self.assertIsNone(result.pending_running)

    def test_holding_the_lease_yourself_is_not_view_only(self):
        lease = {
            "holder_uid": "me",
            "holder_kind": "operator",
            "expires_at": (NOW + timedelta(seconds=60)).isoformat(),
            "epoch": 1,
        }
        result = reduce(CommandState(), station(control_lease=lease), NOW, holder_uid="me")
        self.assertEqual(result.phase, CommandPhase.IDLE)

    def test_expired_lease_returns_control(self):
        lease = {
            "holder_uid": "other-operator",
            "holder_kind": "operator",
            "expires_at": (NOW - timedelta(seconds=1)).isoformat(),
            "epoch": 4,
        }
        state = CommandState(phase=CommandPhase.VIEW_ONLY)
        result = reduce(state, station(control_lease=lease), NOW, holder_uid="me")
        self.assertEqual(result.phase, CommandPhase.IDLE)

    def test_toggle_stays_available_offline_so_a_stuck_running_can_be_cleared(self):
        offline_running = station(
            last_seen_at=(NOW - timedelta(minutes=5)).isoformat(),
            desired_state={"generation": 3, "running": True},
            observed_generation=1,
        )
        self.assertTrue(can_toggle(CommandState(), offline_running, NOW))

    def test_toggle_blocked_while_a_command_is_pending_on_an_online_station(self):
        pending = station(desired_state={"generation": 5, "running": True}, observed_generation=4)
        self.assertFalse(can_toggle(CommandState(), pending, NOW))

    def test_toggle_blocked_in_view_only(self):
        self.assertFalse(
            can_toggle(CommandState(phase=CommandPhase.VIEW_ONLY), station(), NOW)
        )


class StationModelTests(unittest.TestCase):
    def test_online_threshold_is_fifteen_seconds(self):
        self.assertTrue(
            station(last_seen_at=(NOW - timedelta(seconds=15)).isoformat()).is_online_at(NOW)
        )
        self.assertFalse(
            station(last_seen_at=(NOW - timedelta(seconds=16)).isoformat()).is_online_at(NOW)
        )

    def test_inactive_station_is_never_online(self):
        fresh = station(active=False, last_seen_at=NOW.isoformat())
        self.assertFalse(fresh.is_online_at(NOW))

    def test_wire_names_are_mapped(self):
        from prana_core.console.models import TranslationResult

        result = TranslationResult.from_wire(
            {
                "request_id": "r1",
                "transcript_restored": "restored text",
                "detected_language": "vi",
                "translation": "translated text",
            }
        )
        self.assertEqual(result.transcript, "restored text")
        self.assertEqual(result.language, "vi")


if __name__ == "__main__":
    unittest.main()
