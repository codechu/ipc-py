from __future__ import annotations

import threading
from pathlib import Path

import pytest

from codechu_ipc import FifoChannel


def test_fifo_is_created(tmp_path: Path) -> None:
    p = tmp_path / "ch.fifo"
    FifoChannel(p)
    assert p.is_fifo()


def test_fifo_send_recv_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "ch.fifo"
    ch = FifoChannel(p)

    received: list[dict] = []

    def reader() -> None:
        received.append(ch.recv())

    t = threading.Thread(target=reader, daemon=True)
    t.start()

    # Wait briefly so the reader has opened the FIFO before we write,
    # otherwise the non-blocking write would raise ENXIO.
    for _ in range(100):
        try:
            ch.send({"hello": "fifo"})
            break
        except BrokenPipeError:
            import time

            time.sleep(0.01)
    else:
        pytest.fail("reader never attached to FIFO")

    t.join(timeout=2.0)
    assert received == [{"hello": "fifo"}]


def test_fifo_send_without_reader_raises(tmp_path: Path) -> None:
    p = tmp_path / "noreader.fifo"
    ch = FifoChannel(p)
    with pytest.raises(BrokenPipeError):
        ch.send({"x": 1})


def test_fifo_rejects_non_fifo_path(tmp_path: Path) -> None:
    p = tmp_path / "regular"
    p.write_text("not a fifo")
    with pytest.raises(FileExistsError):
        FifoChannel(p)


def test_fifo_unlink(tmp_path: Path) -> None:
    p = tmp_path / "gone.fifo"
    ch = FifoChannel(p)
    assert p.is_fifo()
    ch.unlink()
    assert not p.exists()
