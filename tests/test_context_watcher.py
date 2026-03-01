"""Tests for context graph file watcher."""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from watchfiles import Change


# --- Task 1: SourceFileFilter and FileWatcher ---


class TestSourceFileFilter:
    """Tests for SourceFileFilter extension/dir/gitignore filtering."""

    def _make_filter(self, tmp_path, gitignore_content=None):
        if gitignore_content:
            (tmp_path / ".gitignore").write_text(gitignore_content)
        from scripts.context.watcher import SourceFileFilter
        return SourceFileFilter(tmp_path)

    def test_accepts_source_extensions(self, tmp_path):
        """SourceFileFilter accepts .py/.ts/.go changes, rejects .md/.json."""
        f = self._make_filter(tmp_path)
        # Accepted extensions
        assert f(Change.modified, str(tmp_path / "app.py")) is True
        assert f(Change.modified, str(tmp_path / "index.ts")) is True
        assert f(Change.added, str(tmp_path / "main.go")) is True
        # Rejected extensions
        assert f(Change.modified, str(tmp_path / "README.md")) is False
        assert f(Change.modified, str(tmp_path / "data.json")) is False
        assert f(Change.modified, str(tmp_path / "image.png")) is False

    def test_rejects_default_skip_dirs(self, tmp_path):
        """SourceFileFilter rejects paths in _DEFAULT_SKIP dirs."""
        f = self._make_filter(tmp_path)
        assert f(Change.modified, str(tmp_path / "node_modules" / "pkg" / "index.js")) is False
        assert f(Change.modified, str(tmp_path / "__pycache__" / "mod.py")) is False
        assert f(Change.modified, str(tmp_path / ".git" / "hooks" / "pre-commit.py")) is False
        assert f(Change.modified, str(tmp_path / ".cnogo" / "scripts" / "foo.py")) is False

    def test_rejects_gitignore_matched_paths(self, tmp_path):
        """SourceFileFilter rejects gitignore-matched paths."""
        f = self._make_filter(tmp_path, gitignore_content="generated/\n*.generated.py\n")
        assert f(Change.modified, str(tmp_path / "generated" / "output.py")) is False
        assert f(Change.modified, str(tmp_path / "foo.generated.py")) is False
        # Non-matching file should pass
        assert f(Change.modified, str(tmp_path / "src" / "app.py")) is True


class TestFileWatcher:
    """Tests for FileWatcher start/stop and callback."""

    def test_start_calls_watchfiles_watch(self, tmp_path):
        """FileWatcher.start() calls watchfiles.watch with correct args."""
        from scripts.context.watcher import FileWatcher

        callback = MagicMock()
        watcher = FileWatcher(tmp_path, on_change=callback, debounce_ms=500)

        fake_changes = {(Change.modified, str(tmp_path / "app.py"))}

        with patch("scripts.context.watcher.watch") as mock_watch:
            # Simulate one batch of changes then stop
            mock_watch.return_value = iter([fake_changes])
            watcher.start()

        mock_watch.assert_called_once()
        call_kwargs = mock_watch.call_args
        # Check path arg
        assert call_kwargs[0][0] == tmp_path.resolve()
        # Check debounce
        assert call_kwargs[1]["debounce"] == 500
        # Check stop_event is a threading.Event
        assert isinstance(call_kwargs[1]["stop_event"], threading.Event)

    def test_stop_sets_event(self, tmp_path):
        """FileWatcher.stop() sets the stop event."""
        from scripts.context.watcher import FileWatcher

        watcher = FileWatcher(tmp_path, on_change=lambda c: None)
        assert not watcher._stop_event.is_set()
        watcher.stop()
        assert watcher._stop_event.is_set()

    def test_on_change_receives_batches(self, tmp_path):
        """on_change callback receives change batches."""
        from scripts.context.watcher import FileWatcher

        received = []
        watcher = FileWatcher(tmp_path, on_change=lambda c: received.append(c))

        batch1 = {(Change.modified, str(tmp_path / "a.py"))}
        batch2 = {(Change.added, str(tmp_path / "b.py")), (Change.modified, str(tmp_path / "c.ts"))}

        with patch("scripts.context.watcher.watch") as mock_watch:
            mock_watch.return_value = iter([batch1, batch2])
            watcher.start()

        assert len(received) == 2
        assert received[0] == batch1
        assert received[1] == batch2

    def test_works_with_empty_repo(self, tmp_path):
        """FileWatcher works with empty repo (no files, no changes)."""
        from scripts.context.watcher import FileWatcher

        callback = MagicMock()
        watcher = FileWatcher(tmp_path, on_change=callback)

        with patch("scripts.context.watcher.watch") as mock_watch:
            mock_watch.return_value = iter([])  # no changes
            watcher.start()

        callback.assert_not_called()


# --- Task 2: ContextGraph.watch() method ---


class TestContextGraphWatch:
    """Tests for ContextGraph.watch() method."""

    def _make_graph(self, tmp_path):
        from scripts.context import ContextGraph
        (tmp_path / ".cnogo").mkdir(exist_ok=True)
        return ContextGraph(repo_path=tmp_path)

    def test_watch_calls_initial_index(self, tmp_path):
        """watch() calls index() on initial run."""
        graph = self._make_graph(tmp_path)
        try:
            with patch.object(graph, "index", return_value={"files_indexed": 0, "files_skipped": 0, "files_removed": 0}) as mock_index:
                with patch("scripts.context.watcher.watch") as mock_watch:
                    mock_watch.return_value = iter([])  # no file changes
                    graph.watch()
            # index() called once for initial run
            mock_index.assert_called_once()
        finally:
            graph.close()

    def test_watch_creates_file_watcher(self, tmp_path):
        """watch() creates FileWatcher with correct args."""
        graph = self._make_graph(tmp_path)
        try:
            with patch.object(graph, "index", return_value={"files_indexed": 0, "files_skipped": 0, "files_removed": 0}):
                with patch("scripts.context.watcher.FileWatcher") as MockWatcher:
                    instance = MockWatcher.return_value
                    instance.start.return_value = None
                    graph.watch(debounce_ms=2000)
            MockWatcher.assert_called_once()
            call_kwargs = MockWatcher.call_args
            assert call_kwargs[1]["debounce_ms"] == 2000
        finally:
            graph.close()

    def test_on_cycle_callback_fires_with_initial_stats(self, tmp_path):
        """on_cycle callback fires with initial stats."""
        graph = self._make_graph(tmp_path)
        cycles = []
        try:
            with patch.object(graph, "index", return_value={"files_indexed": 5, "files_skipped": 0, "files_removed": 0}):
                with patch("scripts.context.watcher.FileWatcher") as MockWatcher:
                    instance = MockWatcher.return_value
                    instance.start.return_value = None
                    graph.watch(on_cycle=lambda s: cycles.append(s))
            assert len(cycles) >= 1
            assert cycles[0]["files_indexed"] == 5
        finally:
            graph.close()

    def test_file_change_triggers_reindex(self, tmp_path):
        """File change triggers re-index (index() called twice)."""
        graph = self._make_graph(tmp_path)
        try:
            index_calls = []

            def fake_index():
                call_num = len(index_calls) + 1
                result = {"files_indexed": call_num, "files_skipped": 0, "files_removed": 0}
                index_calls.append(result)
                return result

            with patch.object(graph, "index", side_effect=fake_index):
                with patch("scripts.context.watcher.FileWatcher") as MockWatcher:
                    # Capture the on_change callback and simulate a file change
                    def fake_init(repo, on_change, debounce_ms=1600):
                        # Simulate one file change during start()
                        mock_instance = MagicMock()
                        def fake_start():
                            on_change({(Change.modified, str(tmp_path / "app.py"))})
                        mock_instance.start = fake_start
                        return mock_instance
                    MockWatcher.side_effect = fake_init
                    graph.watch()

            assert len(index_calls) == 2  # initial + re-index
        finally:
            graph.close()

    def test_keyboard_interrupt_stops_gracefully(self, tmp_path):
        """KeyboardInterrupt stops gracefully."""
        graph = self._make_graph(tmp_path)
        try:
            with patch.object(graph, "index", return_value={"files_indexed": 0, "files_skipped": 0, "files_removed": 0}):
                with patch("scripts.context.watcher.FileWatcher") as MockWatcher:
                    instance = MockWatcher.return_value
                    instance.start.side_effect = KeyboardInterrupt
                    # Should not raise
                    result = graph.watch()
            instance.stop.assert_called_once()
            assert isinstance(result, dict)
        finally:
            graph.close()

    def test_returns_cumulative_stats(self, tmp_path):
        """Returns correct cumulative stats."""
        graph = self._make_graph(tmp_path)
        try:
            call_count = [0]

            def fake_index():
                call_count[0] += 1
                return {"files_indexed": 3, "files_skipped": 1, "files_removed": call_count[0] - 1}

            with patch.object(graph, "index", side_effect=fake_index):
                with patch("scripts.context.watcher.FileWatcher") as MockWatcher:
                    def fake_init(repo, on_change, debounce_ms=1600):
                        mock_instance = MagicMock()
                        def fake_start():
                            on_change({(Change.modified, str(tmp_path / "a.py"))})
                        mock_instance.start = fake_start
                        return mock_instance
                    MockWatcher.side_effect = fake_init
                    result = graph.watch()

            assert result["total_cycles"] == 2
            assert result["total_files_indexed"] == 6  # 3 + 3
            assert result["total_files_removed"] == 1  # 0 + 1
        finally:
            graph.close()
