"""Persistencia y ciclo de vida de la academia sin abrir ventanas durante pytest."""
import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock

from src.gui import academy


def test_progress_survives_new_api_and_unicode_notes(tmp_path):
    path = tmp_path / "config" / "learning.json"
    first = academy.AcademyApi(path)
    state = {"version": 1, "name": "María", "courses": {"terminal": {"notes": {"0": "Comillas: < > & á"}, "exam": {"answers": [None] * 75}}}}
    assert first.save_learning(state) == {"success": True}
    assert academy.AcademyApi(path).load_learning()["state"] == state
    assert list(path.parent.iterdir()) == [path]


def test_corrupt_file_is_reported_without_replacing_data(tmp_path):
    path = tmp_path / "learning.json"
    path.write_text("incompleto", encoding="utf-8")
    assert academy.AcademyApi(path).load_learning()["success"] is False
    assert path.read_text() == "incompleto"


def test_invalid_or_oversized_progress_preserves_previous_state(tmp_path):
    api = academy.AcademyApi(tmp_path / "learning.json")
    state = {"version": 1, "courses": {}}
    assert api.save_learning(state)["success"]
    for bad in ([], {"version": 9, "courses": {}}, {"version": 1, "courses": []}, {"version": 1, "courses": {}, "notes": "á" * 600000}):
        assert not api.save_learning(bad)["success"]
    assert api.load_learning()["state"] == state


def test_failed_atomic_replace_keeps_previous_file(tmp_path, monkeypatch):
    path = tmp_path / "learning.json"
    api = academy.AcademyApi(path)
    initial = {"version": 1, "courses": {}, "name": "Antes"}
    api.save_learning(initial)
    monkeypatch.setattr(academy.Path, "replace", Mock(side_effect=OSError("disk full")))
    assert not api.save_learning({**initial, "name": "Después"})["success"]
    assert json.loads(path.read_text()) == initial
    assert list(tmp_path.iterdir()) == [path]


def test_concurrent_writes_remain_complete_json(tmp_path):
    api = academy.AcademyApi(tmp_path / "learning.json")
    states = [{"version": 1, "courses": {}, "name": str(i)} for i in range(12)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert all(r["success"] for r in pool.map(api.save_learning, states))
    assert api.load_learning()["state"] in states


def test_window_reused_and_recreated_after_close(monkeypatch, tmp_path):
    class ClosedEvent:
        def __iadd__(self, callback):
            self.callback = callback
            return self

    windows = []

    def create_window(*args, **kwargs):
        window = SimpleNamespace(restore=Mock(), show=Mock(), events=SimpleNamespace(closed=ClosedEvent()))
        windows.append((window, kwargs))
        return window

    monkeypatch.setattr(academy.webview, "create_window", create_window)
    manager = academy.AcademyWindow(academy.AcademyApi(tmp_path / "learning.json"))
    assert manager.open()["success"]
    assert manager.open()["success"]
    assert len(windows) == 1
    window, options = windows[0]
    window.show.assert_called_once()
    assert options["url"].endswith("academy.html#desktop")
    assert isinstance(options["js_api"], academy.AcademyApi)
    window.events.closed.callback()
    assert manager.open()["success"]
    assert len(windows) == 2


def test_summary_ignores_invalid_and_repeated_lesson_indices(tmp_path):
    api = academy.AcademyApi(tmp_path / "learning.json")
    api.save_learning({"version": 1, "courses": {"fundamentos": {"completed": [0, 0, 1, 30, -1, "3", True]}, "terminal": {"completed": [14]}}})
    summary = academy.AcademyWindow(api).summary()
    assert summary == {"success": True, "completed": 3, "total": 90}


def test_local_video_library_copies_lists_and_removes_media(tmp_path):
    source = tmp_path / "clase.mp4"
    source.write_bytes(b"video-de-prueba")
    api = academy.AcademyApi(tmp_path / "config" / "learning.json")
    api._window = SimpleNamespace(create_file_dialog=Mock(return_value=(str(source),)))

    added = api.add_learning_video()
    assert added["success"] is True
    assert added["video"]["title"] == "clase"
    assert added["video"]["url"].startswith("http://127.0.0.1:")
    from urllib.request import Request, urlopen
    with urlopen(Request(added["video"]["url"], headers={"Range": "bytes=0-4"}), timeout=5) as response:
        assert response.status == 206
        assert response.read() == b"video"
    assert api.list_learning_videos()["videos"][0]["size"] == len(b"video-de-prueba")
    copied = api._media_dir / added["video"]["file"]
    assert copied.read_bytes() == b"video-de-prueba"

    assert api.remove_learning_video(added["video"]["id"]) == {"success": True}
    assert not copied.exists()
    assert api.list_learning_videos()["videos"] == []


def test_video_library_rejects_unsupported_file(tmp_path):
    source = tmp_path / "notas.txt"
    source.write_text("no es video")
    api = academy.AcademyApi(tmp_path / "config" / "learning.json")
    api._window = SimpleNamespace(create_file_dialog=Mock(return_value=(str(source),)))
    assert api.add_learning_video()["success"] is False


def test_prepare_video_preserves_original_and_registers_copy(tmp_path, monkeypatch):
    source = tmp_path / "clase.mp4"
    source.write_bytes(b"original")
    api = academy.AcademyApi(tmp_path / "config" / "learning.json")
    api._window = SimpleNamespace(create_file_dialog=Mock(return_value=(str(source),)))
    added = api.add_learning_video()["video"]
    monkeypatch.setattr(academy.shutil, "which", lambda _: "/usr/bin/gst-launch-1.0")

    def convert(command, **kwargs):
        if "filesrc" not in command:
            return SimpleNamespace(returncode=0, stdout="video #1: H.264")
        destination = next(arg for arg in command if arg.startswith('location="') and arg.endswith('.webm"'))
        academy.Path(destination[len('location="'):-1]).write_bytes(b"converted")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(academy.subprocess, "run", convert)
    result = api.prepare_learning_video(added["id"])
    assert result["success"]
    assert result["video"]["file"].endswith(".webm")
    assert len(api.list_learning_videos()["videos"]) == 2
    assert (api._media_dir / added["file"]).read_bytes() == b"original"


def test_prepare_video_failure_keeps_library(tmp_path, monkeypatch):
    source = tmp_path / "clase.mp4"
    source.write_bytes(b"original")
    api = academy.AcademyApi(tmp_path / "config" / "learning.json")
    api._window = SimpleNamespace(create_file_dialog=Mock(return_value=(str(source),)))
    added = api.add_learning_video()["video"]
    monkeypatch.setattr(academy.shutil, "which", lambda _: "/usr/bin/gst-launch-1.0")
    monkeypatch.setattr(academy.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout=""))
    assert not api.prepare_learning_video(added["id"])["success"]
    assert len(api.list_learning_videos()["videos"]) == 1
    assert not list(api._media_dir.glob("*.webm"))


def test_export_uses_selected_path_and_handles_cancel(tmp_path):
    api = academy.AcademyApi(tmp_path / "learning.json")
    output = tmp_path / "constancia.txt"
    api._window = SimpleNamespace(create_file_dialog=Mock(return_value=(str(output),)))
    assert api.export_learning_certificate("terminal", "Constancia de María")["success"]
    assert output.read_text() == "Constancia de María"
    api._window.create_file_dialog.return_value = None
    assert api.export_learning_certificate("terminal", "texto")["cancelled"]
    assert not api.export_learning_certificate("../../other", "texto")["success"]
