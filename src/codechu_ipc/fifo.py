"""Named pipe (FIFO) channel with JSON-line framing.

FIFOs are unidirectional. A :class:`FifoChannel` instance is used
either to send or to receive — typically one side per process.
"""

from __future__ import annotations

import errno
import os
from pathlib import Path

from .protocol import JsonLineProtocol


class FifoChannel:
    """Named-pipe (FIFO) channel transporting JSON-line messages.

    Parameters
    ----------
    path:
        Filesystem path of the FIFO. Auto-created with ``mkfifo`` if
        missing. Permissions default to ``0o600``.
    mode:
        Filesystem permissions to apply when creating the FIFO.
    """

    def __init__(self, path: str | os.PathLike[str], *, mode: int = 0o600) -> None:
        self.path = Path(path)
        self._ensure(mode)

    # ---- public ------------------------------------------------------

    def send(self, payload: dict) -> None:
        """Write one JSON-line message.

        Opens the FIFO in non-blocking mode so the call does not hang
        when no reader is attached — raises
        :class:`BrokenPipeError` instead. Once at least one reader is
        present, the write proceeds normally.
        """
        data = JsonLineProtocol.encode(payload)
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_NONBLOCK)
        except OSError as exc:
            if exc.errno == errno.ENXIO:
                raise BrokenPipeError(f"no reader on FIFO {self.path}") from exc
            raise
        try:
            os.write(fd, data)
        finally:
            os.close(fd)

    def recv(self) -> dict:
        """Block until one JSON-line message arrives, then return it."""
        # Blocking open until a writer attaches.
        with open(self.path, "rb") as f:
            for obj in JsonLineProtocol.decode_stream(f):
                return obj
        raise ConnectionError(f"FIFO {self.path} closed before any message")

    def unlink(self) -> None:
        """Remove the FIFO from the filesystem."""
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    # ---- internals ---------------------------------------------------

    def _ensure(self, mode: int) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            if not self.path.is_fifo():
                raise FileExistsError(f"{self.path} exists and is not a FIFO")
            return
        os.mkfifo(self.path, mode)
