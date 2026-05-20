"""Unix domain socket server.

One JSON-line request → optional one JSON-line response, per
connection. Multi-client via a thread per accepted connection.
"""

from __future__ import annotations

import json
import os
import socket
import stat
import threading
from pathlib import Path
from typing import Callable

from .protocol import JsonLineProtocol

Handler = Callable[[dict], "dict | None"]


class UnixServer:
    """Threaded Unix-domain-socket server speaking JSON lines.

    Parameters
    ----------
    path:
        Filesystem path for the socket (e.g.
        ``$XDG_RUNTIME_DIR/codechu/myapp/control.sock``).
    handler:
        Callable receiving the decoded request dict; its return value
        (a dict, or ``None`` for notification-only requests) is sent
        back as a JSON line.
    mode:
        Filesystem permissions applied to the socket file after bind.
        Defaults to ``0o600`` (owner-only).
    backlog:
        ``listen()`` backlog. Default 16.
    """

    def __init__(
        self,
        path: str | os.PathLike[str],
        handler: Handler,
        *,
        mode: int = 0o600,
        backlog: int = 16,
    ) -> None:
        self.path = Path(path)
        self.handler = handler
        self.mode = mode
        self.backlog = backlog
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._workers: list[threading.Thread] = []

    # ---- lifecycle ----------------------------------------------------

    def start(self) -> None:
        """Bind, listen, and start the accept loop in a daemon thread."""
        if self._thread is not None:
            raise RuntimeError("server already started")

        self._cleanup_stale()
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(str(self.path))
        os.chmod(self.path, self.mode)
        self._sock.listen(self.backlog)
        self._sock.settimeout(0.25)  # so accept() loop can poll _stop

        self._thread = threading.Thread(
            target=self._accept_loop, name=f"UnixServer({self.path.name})", daemon=True
        )
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        """Signal the accept loop to stop, close the socket, unlink the file."""
        self._stop.set()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None
        for w in self._workers:
            w.join(timeout=timeout)
        self._workers.clear()
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    # ---- context manager ---------------------------------------------

    def __enter__(self) -> "UnixServer":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

    # ---- internals ---------------------------------------------------

    def _cleanup_stale(self) -> None:
        """Remove a stale socket file from a previous (crashed) run."""
        if not self.path.exists():
            return
        try:
            st = self.path.stat()
        except FileNotFoundError:
            return
        if not stat.S_ISSOCK(st.st_mode):
            raise FileExistsError(
                f"{self.path} exists and is not a socket; refusing to overwrite"
            )
        # Probe: if nobody is listening, the connect will fail fast.
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        probe.settimeout(0.1)
        try:
            probe.connect(str(self.path))
        except (ConnectionRefusedError, FileNotFoundError, OSError):
            # Stale: safe to unlink.
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
        else:
            probe.close()
            raise FileExistsError(f"{self.path} is in use by another server")
        finally:
            try:
                probe.close()
            except OSError:
                pass

    def _accept_loop(self) -> None:
        assert self._sock is not None
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                # socket closed under us during stop()
                return
            worker = threading.Thread(
                target=self._handle_conn, args=(conn,), daemon=True
            )
            worker.start()
            self._workers.append(worker)

    def _handle_conn(self, conn: socket.socket) -> None:
        try:
            with conn, conn.makefile("rb") as r, conn.makefile("wb") as w:
                for request in JsonLineProtocol.decode_stream(r):
                    try:
                        response = self.handler(request)
                    except Exception as exc:  # noqa: BLE001
                        response = {"error": str(exc), "type": type(exc).__name__}
                    if response is None:
                        continue
                    try:
                        w.write(JsonLineProtocol.encode(response))
                        w.flush()
                    except BrokenPipeError:
                        return
        except (OSError, json.JSONDecodeError):
            return
