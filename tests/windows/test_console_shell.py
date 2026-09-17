from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

try:
    from PySide6.QtWidgets import QApplication

    from prana_core.console.command_phase import CommandPhase, CommandState
    from prana_core.console.models import StationSummary, TranslationResult
    from prana_windows.ui.components.lease_banner import LeaseBanner
    from prana_windows.ui.components.station_row import StationRow
    from prana_windows.ui.console import StationController
    from prana_windows.ui.i18n import language
    from prana_windows.ui.pages.fleet import FleetPage
    from prana_windows.ui.pages.station_workspace import StationWorkspacePage
except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
    if not (exc.name or "").startswith("PySide6"):
        raise
    QApplication = None  # type: ignore[assignment]
    CommandPhase = CommandState = None  # type: ignore[assignment]
    StationSummary = TranslationResult = None  # type: ignore[assignment]
    LeaseBanner = StationRow = None  # type: ignore[assignment]
    StationController = None  # type: ignore[assignment]
    language = None  # type: ignore[assignment]
    FleetPage = StationWorkspacePage = None  # type: ignore[assignment]


def _station(**overrides) -> "StationSummary":
    data = {
        "station_id": "a" * 32,
        "name": "Bridge Pi",
        "owner_email": "owner@example.com",
        "platform": "Linux aarch64",
        "active": True,
        "capture_state": "listening",
        "last_seen_at": datetime.now(timezone.utc).isoformat(),
        "observed_generation": 1,
        "desired_state": {"generation": 1, "running": True, "target_language": "en"},
        "capabilities": {
            "capability_hash": "0" * 64,
            "capture_modes": ["device"],
            "audio_devices": [
                {
                    "id": "usb-input",
                    "name": "USB SoundCard",
                    "mode": "device",
                    "input_channels": 1,
                }
            ],
        },
    }
    data.update(overrides)
    return StationSummary.from_wire(data)


def _lease(holder_uid: str, seconds: int = 60, epoch: int = 1) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "holder_uid": holder_uid,
        "holder_kind": "operator",
        "holder_label": "Ops desk",
        "expires_at": (now + timedelta(seconds=seconds)).isoformat(),
        "epoch": epoch,
    }


class _FakeClient:
    """Stands in for OperatorStationClient without touching the network."""

    def __init__(self):
        self.operator_uid = "me"
        self.released: list[tuple[str, int]] = []

    def get_station(self, station_id):
        return _station(station_id=station_id)

    def live_results(self, _station_id):
        return []

    def release_control(self, station_id, epoch):
        self.released.append((station_id, epoch))


@unittest.skipIf(QApplication is None, "PySide6 is not installed in this test environment")
class ConsoleShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_fleet_reconciles_rows_instead_of_rebuilding_them(self) -> None:
        """Rows survive a poll so the operator does not lose scroll or focus."""
        page = FleetPage()
        first = _station()
        page.set_stations([first])
        row = page._rows[first.station_id]
        page.set_stations([_station(capture_state="recording")])
        self.assertIs(page._rows[first.station_id], row)
        self.assertIn("RECORDING", row._detail.text())
        page.set_stations([])
        self.assertEqual(page._rows, {})
        self.assertFalse(page._empty.isHidden())
        page.close()

    def test_station_row_reflects_online_state(self) -> None:
        online = StationRow(_station())
        self.assertEqual(online._status.property("online"), "true")
        stale = StationRow(
            _station(
                last_seen_at=(
                    datetime.now(timezone.utc) - timedelta(minutes=5)
                ).isoformat()
            )
        )
        self.assertEqual(stale._status.property("online"), "false")
        online.close()
        stale.close()

    def test_lease_banner_distinguishes_mine_theirs_and_nobody(self) -> None:
        banner = LeaseBanner()
        banner.set_operator_uid("me")

        banner.set_lease(None)
        self.assertEqual(banner.property("lease"), "none")
        self.assertFalse(banner._take.isHidden())

        from prana_core.console.models import ControlLease

        banner.set_lease(ControlLease.from_wire(_lease("me")))
        self.assertEqual(banner.property("lease"), "self")
        self.assertTrue(banner._take.isHidden())

        banner.set_lease(ControlLease.from_wire(_lease("someone-else")))
        self.assertEqual(banner.property("lease"), "other")
        self.assertFalse(banner._take.isHidden())
        banner.close()

    def test_taking_a_held_lease_asks_for_force_not_a_plain_acquire(self) -> None:
        """Preemption must never be a side effect of the ordinary button."""
        from PySide6.QtTest import QSignalSpy
        from prana_core.console.models import ControlLease

        banner = LeaseBanner()
        banner.set_operator_uid("me")
        take = QSignalSpy(banner.take_requested)
        force = QSignalSpy(banner.force_requested)

        banner.set_lease(None)
        banner._take.click()
        self.assertEqual((take.count(), force.count()), (1, 0))

        banner.set_lease(ControlLease.from_wire(_lease("someone-else")))
        banner._take.click()
        self.assertEqual((take.count(), force.count()), (1, 1))
        banner.close()

    def test_workspace_appends_only_new_results(self) -> None:
        """The live endpoint replays the whole day on every poll."""
        page = StationWorkspacePage()
        page.set_station(_station())
        result = TranslationResult.from_wire(
            {
                "request_id": "r1",
                "transcript_restored": "xin chao",
                "translation": "hello",
                "detected_language": "vi",
            }
        )
        page.set_results([result])
        page.set_results([result])
        bubbles = [
            child
            for child in page.chat.findChildren(object)
            if getattr(child, "objectName", lambda: "")() == "ChatBubble"
        ]
        self.assertEqual(len(bubbles), 1)
        page.close()

    def test_control_bar_blocks_input_in_view_only(self) -> None:
        page = StationWorkspacePage()
        page.set_station(_station())
        page.set_state(CommandState(phase=CommandPhase.VIEW_ONLY))
        bar = page.control_bar
        self.assertFalse(bar._toggle.isEnabled())
        self.assertFalse(bar._language.isEnabled())
        self.assertFalse(bar._device.isEnabled())
        page.close()

    def test_console_pages_retranslate_without_rebuilding(self) -> None:
        fleet = FleetPage()
        workspace = StationWorkspacePage()
        workspace.set_station(_station())
        row_before = None
        fleet.set_stations([_station()])
        row_before = fleet._rows["a" * 32]

        language.set_locale("vi")
        self.app.processEvents()
        self.assertEqual(fleet._title.text(), "Danh sách Station")
        self.assertIn("Đang gắn vào", workspace._title.text())
        self.assertIs(fleet._rows["a" * 32], row_before)

        language.set_locale("en")
        self.app.processEvents()
        self.assertEqual(fleet._title.text(), "Stations")
        fleet.close()
        workspace.close()

    def test_detaching_stops_every_poll_and_releases_the_lease(self) -> None:
        from prana_core.console.models import ControlLease

        client = _FakeClient()
        controller = StationController(client, "a" * 32)
        controller.attach()
        self.assertTrue(controller._station_poll.running)
        self.assertTrue(controller._live_poll.running)
        controller.lease = ControlLease.from_wire(_lease("me", epoch=7))

        controller.detach()
        self.assertIsNone(controller._station_poll)
        self.assertIsNone(controller._live_poll)
        self.assertEqual(client.released, [("a" * 32, 7)])

    def test_pausing_content_leaves_lease_renewal_running(self) -> None:
        """Losing control because a window was minimised would be worse."""
        client = _FakeClient()
        controller = StationController(client, "a" * 32)
        controller.attach()
        controller._start_renewal()
        controller.pause_content()
        self.assertTrue(controller._station_poll._paused)
        self.assertTrue(controller._live_poll._paused)
        self.assertFalse(controller._renew_poll._paused)
        controller.detach()

    def test_tx_panel_blocks_recording_until_the_station_is_ready(self) -> None:
        from prana_core.console.tx_phase import TxState
        from prana_windows.ui.components.tx_panel import TxPanel

        panel = TxPanel()
        panel.set_state(TxState(), can_record=False, can_retry=False)
        self.assertFalse(panel._record.isEnabled())
        self.assertEqual(
            panel._status.text(),
            "Transmit needs an online, started Station with PTT ready.",
        )
        panel.set_state(TxState(), can_record=True, can_retry=False)
        self.assertTrue(panel._record.isEnabled())
        panel.close()

    def test_tx_review_seeds_once_and_keeps_operator_edits(self) -> None:
        """The draft poll keeps running; it must not overwrite what was typed."""
        from prana_core.console.tx_phase import TxPhase, TxState
        from prana_windows.ui.components.tx_panel import TxPanel

        panel = TxPanel()
        draft = {"id": "d1", "status": "review_ready",
                 "transcript": "xin chao", "translation": "hello"}
        review = TxState(phase=TxPhase.REVIEW_READY, draft=draft)
        panel.set_state(review, can_record=False, can_retry=False)
        self.assertEqual(panel._translation.toPlainText(), "hello")

        panel._translation.setPlainText("hello bridge")
        panel.set_state(review, can_record=False, can_retry=False)
        self.assertEqual(panel._translation.toPlainText(), "hello bridge")
        panel.close()

    def test_transmit_is_disabled_for_an_empty_translation(self) -> None:
        from prana_core.console.tx_phase import TxPhase, TxState
        from prana_windows.ui.components.tx_panel import TxPanel

        panel = TxPanel()
        draft = {"id": "d1", "status": "review_ready", "transcript": "t", "translation": ""}
        state = TxState(phase=TxPhase.REVIEW_READY, draft=draft)
        panel.set_state(state, can_record=False, can_retry=False)
        self.assertFalse(panel._transmit.isEnabled())
        panel._translation.setPlainText("hello")
        panel.set_state(state, can_record=False, can_retry=False)
        self.assertTrue(panel._transmit.isEnabled())
        panel.close()

    def test_every_tx_call_presents_the_current_control_epoch(self) -> None:
        """The API refuses TX without the epoch; the fake client must not hide that."""
        import threading

        from prana_core.console.tx_phase import (
            StationReadiness,
            TxFailure,
            TxPhase,
            TxState,
        )
        from prana_windows.ui.console import TxController

        class _TxClient:
            def __init__(self):
                self.calls: list[tuple[str, int]] = []
                self.changed = threading.Condition()

            def _record(self, name, epoch, result=None):
                with self.changed:
                    self.calls.append((name, epoch))
                    self.changed.notify_all()
                return result

            def wait_for(self, name) -> bool:
                with self.changed:
                    return self.changed.wait_for(
                        lambda: any(n == name for n, _ in self.calls), timeout=2
                    )

            def create_tx_draft(self, _sid, epoch, _audio, _lang, request_id=None):
                draft = {"id": "d1", "status": "processing"}
                return self._record("create", epoch, (draft, request_id))

            def get_tx_draft(self, _sid, epoch, _draft_id):
                return self._record("get", epoch, {"id": "d1", "status": "processing"})

            def confirm_tx_draft(self, _sid, epoch, _draft_id, _translation):
                return self._record("confirm", epoch, {"id": "d1", "status": "queued"})

            def retry_tx_draft(self, _sid, epoch, _draft_id):
                return self._record("retry", epoch, {"id": "d1", "status": "processing"})

            def cancel_tx_draft(self, _sid, epoch, _draft_id):
                self._record("cancel", epoch)

        class _Recorder:
            is_recording = False

            def stop(self):
                return bytes(1) * 32000  # one second of 16 kHz mono PCM

            def cancel(self):
                pass

        client = _TxClient()
        errors: list[str] = []

        def controller(epoch: int) -> TxController:
            tx = TxController(client, "a" * 32, _Recorder())
            tx.readiness = StationReadiness(
                online=True, running=True, ptt_ready=True,
                command_pending=False, holds_control=True,
            )
            tx.error.connect(errors.append)
            tx.set_epoch(epoch)
            return tx
        review = TxState(phase=TxPhase.REVIEW_READY, draft={"id": "d1", "status": "review_ready"})
        failed = TxState(
            phase=TxPhase.FAILED,
            failure=TxFailure.TRANSMISSION_FAILED,
            draft={"id": "d1", "status": "failed"},
        )

        def run(action, state, *expected) -> None:
            # A controller per step: shutdown is final, as it is on detach.
            client.calls.clear()
            tx = controller(7)
            tx.state = state
            action(tx)
            for name in expected:
                self.assertTrue(client.wait_for(name), f"no {name} call was made")
            tx.shutdown()
            with client.changed:
                seen.extend(client.calls)

        seen: list[tuple[str, int]] = []
        run(TxController.stop_recording, TxState(phase=TxPhase.RECORDING, request_id="r1"), "create", "get")
        run(lambda tx: tx.confirm("hello"), review, "confirm", "get")
        run(TxController.retry, failed, "retry", "get")
        run(TxController.cancel, review, "cancel")
        self.assertEqual({epoch for _name, epoch in seen}, {7})
        self.assertEqual({n for n, _ in seen}, {"create", "get", "confirm", "retry", "cancel"})

        # Without the lease nothing reaches the network, and a finished take is
        # dropped rather than left looking retryable.
        client.calls.clear()
        tx = controller(0)
        tx.state = TxState(phase=TxPhase.RECORDING, request_id="r2")
        tx.stop_recording()
        self.assertEqual(tx.state.phase, TxPhase.IDLE)
        tx.state = review
        tx.confirm("hello")
        tx.state = failed
        tx.retry()
        tx.state = review
        tx.cancel()
        self.assertEqual(client.calls, [])
        self.assertEqual(errors.count("error.CONTROL_LOST"), 3)
        tx.shutdown()

    def test_a_draft_poll_cannot_start_after_shutdown(self) -> None:
        """Detach can land while an upload thread is about to watch its draft.

        A poll started after shutdown would never be stopped and would go on
        polling a Station the operator has left.
        """
        from prana_core.console.tx_phase import TxPhase, TxState
        from prana_windows.ui.console import TxController

        class _Client:
            def get_tx_draft(self, *_args):
                return {"id": "d1", "status": "processing"}

        tx = TxController(_Client(), "a" * 32, recorder=None)
        tx.set_epoch(7)
        tx.state = TxState(phase=TxPhase.PROCESSING, draft={"id": "d1", "status": "processing"})
        tx._watch_draft()
        first = tx._draft_poll
        self.assertTrue(first.running)

        class _Recorder:
            is_recording = False

        tx._recorder = _Recorder()
        tx.shutdown()
        self.assertFalse(first.running)
        tx._watch_draft()  # the late worker thread
        self.assertIsNone(tx._draft_poll)


if __name__ == "__main__":
    unittest.main()
