from __future__ import annotations

import unittest

from prana_core.console.tx_phase import (
    MAX_TRANSLATION_CHARS,
    StationReadiness,
    TxFailure,
    TxPhase,
    TxState,
    apply_draft,
    apply_readiness,
    begin_recording,
    can_retry,
    can_start_recording,
    recording_tick,
    validate_translation,
)

READY = StationReadiness(
    online=True, running=True, ptt_ready=True, command_pending=False, holds_control=True
)


class RecordingGateTests(unittest.TestCase):
    def test_every_precondition_is_required(self):
        self.assertTrue(can_start_recording(TxState(), READY))
        for field in (
            "online",
            "running",
            "ptt_ready",
            "holds_control",
        ):
            with self.subTest(field=field):
                import dataclasses

                broken = dataclasses.replace(READY, **{field: False})
                self.assertFalse(can_start_recording(TxState(), broken))

    def test_a_command_in_flight_blocks_recording(self):
        import dataclasses

        pending = dataclasses.replace(READY, command_pending=True)
        self.assertFalse(can_start_recording(TxState(), pending))

    def test_operator_without_the_lease_cannot_key_the_radio(self):
        """The operator-specific gate: no lease, no transmitter."""
        import dataclasses

        no_lease = dataclasses.replace(READY, holds_control=False)
        self.assertFalse(no_lease.ready_to_transmit)
        self.assertFalse(can_start_recording(TxState(), no_lease))

    def test_recording_auto_stops_at_the_plan_ceiling(self):
        state = begin_recording(TxState(), "r1")
        self.assertEqual(recording_tick(state, 12.0, 60).phase, TxPhase.RECORDING)
        self.assertEqual(recording_tick(state, 60.0, 60).phase, TxPhase.PROCESSING)


class RetryPolicyTests(unittest.TestCase):
    def test_a_failed_transmission_is_never_auto_replayed(self):
        """Retry needs an explicit failed phase and a settled server draft."""
        state = TxState(
            phase=TxPhase.FAILED,
            failure=TxFailure.STATION_OFFLINE_DURING_TX,
            draft={"id": "d1", "status": "transmitting"},
        )
        # The job may in fact have gone out on air; not retryable yet.
        self.assertFalse(can_retry(state, READY))

        settled = TxState(
            phase=TxPhase.FAILED,
            failure=TxFailure.STATION_OFFLINE_DURING_TX,
            draft={"id": "d1", "status": "failed"},
        )
        self.assertTrue(can_retry(settled, READY))

    def test_retry_requires_a_ready_station(self):
        import dataclasses

        state = TxState(
            phase=TxPhase.FAILED,
            failure=TxFailure.TRANSMISSION_FAILED,
            draft={"id": "d1", "status": "failed"},
        )
        self.assertTrue(can_retry(state, READY))
        self.assertFalse(
            can_retry(state, dataclasses.replace(READY, ptt_ready=False))
        )

    def test_no_draft_means_nothing_to_retry(self):
        self.assertFalse(
            can_retry(TxState(phase=TxPhase.FAILED, failure=TxFailure.BUSY), READY)
        )


class ReadinessTransitionTests(unittest.TestCase):
    def test_going_offline_mid_transmission_needs_manual_settlement(self):
        import dataclasses

        queued = TxState(phase=TxPhase.QUEUED, draft={"id": "d1", "status": "queued"})
        result = apply_readiness(queued, dataclasses.replace(READY, online=False))
        self.assertEqual(result.phase, TxPhase.FAILED)
        self.assertEqual(result.failure, TxFailure.STATION_OFFLINE_DURING_TX)

    def test_losing_the_lease_fails_an_active_draft(self):
        import dataclasses

        active = TxState(phase=TxPhase.REVIEW_READY, draft={"id": "d1"})
        result = apply_readiness(
            active, dataclasses.replace(READY, holds_control=False)
        )
        self.assertEqual(result.phase, TxPhase.FAILED)
        self.assertEqual(result.failure, TxFailure.CONTROL_LOST)

    def test_ptt_loss_blocks_idle_and_recovers_cleanly(self):
        import dataclasses

        blocked = apply_readiness(
            TxState(), dataclasses.replace(READY, ptt_ready=False)
        )
        self.assertEqual(blocked.failure, TxFailure.PTT_UNAVAILABLE)
        recovered = apply_readiness(blocked, READY)
        self.assertEqual(recovered.phase, TxPhase.IDLE)
        self.assertIsNone(recovered.failure)


class DraftMappingTests(unittest.TestCase):
    def test_wire_statuses_map_to_phases(self):
        for status, phase in (
            ("review_ready", TxPhase.REVIEW_READY),
            ("queued", TxPhase.QUEUED),
            ("transmitting", TxPhase.TRANSMITTING),
            ("completed", TxPhase.COMPLETED),
        ):
            with self.subTest(status=status):
                result = apply_draft(TxState(), {"id": "d1", "status": status})
                self.assertEqual(result.phase, phase)

    def test_failed_draft_carries_a_mapped_failure(self):
        result = apply_draft(
            TxState(), {"id": "d1", "status": "failed", "error": "PTT_UNAVAILABLE"}
        )
        self.assertEqual(result.phase, TxPhase.FAILED)
        self.assertEqual(result.failure, TxFailure.PTT_UNAVAILABLE)


class TranslationValidationTests(unittest.TestCase):
    def test_empty_and_oversized_translations_are_rejected(self):
        self.assertFalse(validate_translation(""))
        self.assertFalse(validate_translation("   "))
        self.assertFalse(validate_translation("x" * (MAX_TRANSLATION_CHARS + 1)))
        self.assertTrue(validate_translation("hello"))
        self.assertTrue(validate_translation("x" * MAX_TRANSLATION_CHARS))

    def test_leaving_mid_draft_requires_confirmation(self):
        self.assertTrue(TxState(phase=TxPhase.RECORDING).requires_leave_confirmation)
        self.assertTrue(TxState(phase=TxPhase.REVIEW_READY).requires_leave_confirmation)
        self.assertFalse(TxState(phase=TxPhase.IDLE).requires_leave_confirmation)
        self.assertFalse(TxState(phase=TxPhase.COMPLETED).requires_leave_confirmation)


if __name__ == "__main__":
    unittest.main()
