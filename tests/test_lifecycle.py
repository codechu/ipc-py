from __future__ import annotations

import multiprocessing as mp
import os
import time
from pathlib import Path

import pytest

from codechu_ipc import pidfile


def test_pidfile_writes_pid_and_removes(tmp_path: Path) -> None:
    p = tmp_path / "app.pid"
    with pidfile(p) as path:
        assert path == p
        content = p.read_text().strip()
        assert int(content) == os.getpid()
    assert not p.exists()


def test_pidfile_creates_parent_dirs(tmp_path: Path) -> None:
    p = tmp_path / "nested" / "deeper" / "app.pid"
    with pidfile(p):
        assert p.exists()
    assert not p.exists()


def _child_holds(pid_path: str, ready_path: str, hold_seconds: float) -> None:
    """Helper run in a subprocess: acquire the pidfile and hold it."""
    from codechu_ipc import pidfile as _pidfile

    with _pidfile(pid_path):
        Path(ready_path).write_text("ready")
        time.sleep(hold_seconds)


def test_pidfile_prevents_double_start(tmp_path: Path) -> None:
    p = tmp_path / "single.pid"
    ready = tmp_path / "ready"

    proc = mp.Process(target=_child_holds, args=(str(p), str(ready), 1.5))
    proc.start()
    try:
        # Wait until the child has the lock.
        for _ in range(200):
            if ready.exists():
                break
            time.sleep(0.01)
        else:
            pytest.fail("child never reported ready")

        with pytest.raises(BlockingIOError):
            with pidfile(p):
                pass
    finally:
        proc.join(timeout=3)
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=1)


def test_pidfile_can_be_reacquired_after_release(tmp_path: Path) -> None:
    p = tmp_path / "reuse.pid"
    with pidfile(p):
        pass
    # File is gone; lock released.
    with pidfile(p):
        assert int(p.read_text().strip()) == os.getpid()
