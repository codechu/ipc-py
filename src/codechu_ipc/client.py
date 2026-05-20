"""Unix domain socket client with retry."""

from __future__ import annotations

import os
import socket
import time
from pathlib import Path

from .protocol import JsonLineProtocol


class UnixClient:
    """Synchronous Unix-socket client speaking JSON lines.

    Parameters
    ----------
    path:
        Server socket path.
    timeout:
        Per-connection socket timeout, in seconds. Default 5.0.
    retries:
        Number of additional attempts after the first failure when
        the server is not (yet) reachable. Default 3 (so up to 4
        attempts in total).
    retry_backoff:
        Initial backoff between retries, in seconds. Doubles each
        retry (exponential). Default 0.5.
    """

    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        timeout: float = 5.0,
        retries: int = 3,
        retry_backoff: float = 0.5,
    ) -> None:
        self.path = Path(path)
        self.timeout = timeout
        self.retries = retries
        self.retry_backoff = retry_backoff

    # ---- public ------------------------------------------------------

    def request(self, payload: dict) -> dict:
        """Send a JSON-line request and read a JSON-line response."""
        with self._connect() as sock:
            sock.sendall(JsonLineProtocol.encode(payload))
            with sock.makefile("rb") as r:
                line = r.readline()
                if not line:
                    raise ConnectionError("server closed connection without responding")
                return JsonLineProtocol.decode_one(line)

    def notify(self, payload: dict) -> None:
        """Fire-and-forget: send a JSON line, do not wait for response."""
        with self._connect() as sock:
            sock.sendall(JsonLineProtocol.encode(payload))

    # ---- internals ---------------------------------------------------

    def _connect(self) -> socket.socket:
        last_exc: Exception | None = None
        backoff = self.retry_backoff
        for attempt in range(self.retries + 1):
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            try:
                sock.connect(str(self.path))
                return sock
            except (ConnectionRefusedError, FileNotFoundError, OSError) as exc:
                last_exc = exc
                try:
                    sock.close()
                except OSError:
                    pass
                if attempt < self.retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
        assert last_exc is not None
        raise ConnectionError(f"could not connect to {self.path}: {last_exc}") from last_exc
