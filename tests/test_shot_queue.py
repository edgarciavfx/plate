from __future__ import annotations

from pathlib import Path

import pytest

from plate.models.shot_queue import QueueEntry, ShotQueue


@pytest.fixture(autouse=True)
def patch_queue_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    queue_dir = tmp_path / ".plate"
    monkeypatch.setattr("plate.models.shot_queue._QUEUE_DIR", queue_dir)
    monkeypatch.setattr("plate.models.shot_queue._QUEUE_PATH", queue_dir / "queue.json")
    return queue_dir / "queue.json"


class TestQueueEntry:
    def test_is_pending_returns_true(self):
        entry = QueueEntry(source="test.mov", in_frame=1, out_frame=10)
        assert entry.is_pending() is True

    def test_is_pending_returns_false_for_non_pending(self):
        entry = QueueEntry(source="test.mov", in_frame=1, out_frame=10, status="done")
        assert entry.is_pending() is False

    def test_default_status_is_pending(self):
        entry = QueueEntry(source="test.mov", in_frame=1, out_frame=10)
        assert entry.status == "pending"


class TestShotQueue:
    def test_empty_queue(self):
        q = ShotQueue()
        assert len(q) == 0
        assert q.pending_entries() == []

    def test_add_entry(self, patch_queue_path: Path):
        q = ShotQueue()
        entry = QueueEntry(source="a.mov", in_frame=1, out_frame=10)
        q.add(entry)
        assert len(q) == 1
        assert q[0].source == "a.mov"
        assert patch_queue_path.exists()

    def test_add_persists_to_disk(self, patch_queue_path: Path):
        q = ShotQueue()
        q.add(QueueEntry(source="a.mov", in_frame=1, out_frame=10))
        q2 = ShotQueue.load()
        assert len(q2) == 1
        assert q2[0].source == "a.mov"

    def test_remove_entry(self, patch_queue_path: Path):
        q = ShotQueue()
        q.add(QueueEntry(source="a.mov", in_frame=1, out_frame=10))
        q.add(QueueEntry(source="b.mov", in_frame=1, out_frame=10))
        q.remove(0)
        assert len(q) == 1
        assert q[0].source == "b.mov"

    def test_remove_out_of_bounds_does_nothing(self, patch_queue_path: Path):
        q = ShotQueue()
        q.add(QueueEntry(source="a.mov", in_frame=1, out_frame=10))
        q.remove(5)
        assert len(q) == 1
        q.remove(-1)
        assert len(q) == 1

    def test_move_up(self, patch_queue_path: Path):
        q = ShotQueue()
        q.add(QueueEntry(source="a.mov", in_frame=1, out_frame=10))
        q.add(QueueEntry(source="b.mov", in_frame=1, out_frame=10))
        q.move_up(1)
        assert q[0].source == "b.mov"
        assert q[1].source == "a.mov"

    def test_move_up_first_does_nothing(self, patch_queue_path: Path):
        q = ShotQueue()
        q.add(QueueEntry(source="a.mov", in_frame=1, out_frame=10))
        q.add(QueueEntry(source="b.mov", in_frame=1, out_frame=10))
        q.move_up(0)
        assert q[0].source == "a.mov"

    def test_move_down(self, patch_queue_path: Path):
        q = ShotQueue()
        q.add(QueueEntry(source="a.mov", in_frame=1, out_frame=10))
        q.add(QueueEntry(source="b.mov", in_frame=1, out_frame=10))
        q.move_down(0)
        assert q[0].source == "b.mov"
        assert q[1].source == "a.mov"

    def test_move_down_last_does_nothing(self, patch_queue_path: Path):
        q = ShotQueue()
        q.add(QueueEntry(source="a.mov", in_frame=1, out_frame=10))
        q.add(QueueEntry(source="b.mov", in_frame=1, out_frame=10))
        q.move_down(1)
        assert q[0].source == "a.mov"

    def test_clear_completed(self, patch_queue_path: Path):
        q = ShotQueue()
        q.add(QueueEntry(source="a.mov", in_frame=1, out_frame=10, status="done"))
        q.add(QueueEntry(source="b.mov", in_frame=1, out_frame=10, status="failed"))
        q.add(QueueEntry(source="c.mov", in_frame=1, out_frame=10, status="pending"))
        q.clear_completed()
        assert len(q) == 1
        assert q[0].source == "c.mov"

    def test_clear_all(self, patch_queue_path: Path):
        q = ShotQueue()
        q.add(QueueEntry(source="a.mov", in_frame=1, out_frame=10))
        q.add(QueueEntry(source="b.mov", in_frame=1, out_frame=10))
        q.clear_all()
        assert len(q) == 0

    def test_pending_entries(self, patch_queue_path: Path):
        q = ShotQueue()
        q.add(QueueEntry(source="a.mov", in_frame=1, out_frame=10, status="pending"))
        q.add(QueueEntry(source="b.mov", in_frame=1, out_frame=10, status="done"))
        q.add(QueueEntry(source="c.mov", in_frame=1, out_frame=10, status="processing"))
        pending = q.pending_entries()
        assert len(pending) == 1
        assert pending[0].source == "a.mov"

    def test_load_empty_when_no_file(self, patch_queue_path: Path):
        q = ShotQueue.load()
        assert len(q) == 0

    def test_load_corrupt_json_returns_empty(self, patch_queue_path: Path):
        patch_queue_path.parent.mkdir(parents=True, exist_ok=True)
        patch_queue_path.write_text("not json")
        q = ShotQueue.load()
        assert len(q) == 0

    def test_load_resets_processing_to_pending(self, patch_queue_path: Path):
        q = ShotQueue()
        q.add(QueueEntry(source="a.mov", in_frame=1, out_frame=10, status="processing"))
        q.add(QueueEntry(source="b.mov", in_frame=1, out_frame=10, status="done"))
        q2 = ShotQueue.load()
        assert q2[0].status == "pending"
        assert q2[0].error is None
        assert q2[1].status == "done"

    def test_len_and_getitem(self, patch_queue_path: Path):
        q = ShotQueue()
        q.add(QueueEntry(source="a.mov", in_frame=1, out_frame=10))
        assert len(q) == 1
        assert isinstance(q[0], QueueEntry)
        with pytest.raises(IndexError):
            _ = q[5]
