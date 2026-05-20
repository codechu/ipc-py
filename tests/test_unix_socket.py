from __future__ import annotations

import socket
import stat
import threading
import time
from pathlib import Path

import pytest

from codechu_ipc import UnixClient, UnixServer


def echo_handler(req: dict) -> dict:
    return {"echo": req}


def test_roundtrip(tmp_path: Path) -> None:
    sock = tmp_path / "echo.sock"
    with UnixServer(sock, echo_handler):
        client = UnixClient(sock, timeout=2.0)
        resp = client.request({"hello": "world"})
        assert resp == {"echo": {"hello": "world"}}


def test_socket_permissions_default_0600(tmp_path: Path) -> None:
    sock = tmp_path / "perm.sock"
    with UnixServer(sock, echo_handler):
        mode = stat.S_IMODE(sock.stat().st_mode)
        assert mode == 0o600


def test_socket_custom_mode(tmp_path: Path) -> None:
    sock = tmp_path / "perm.sock"
    with UnixServer(sock, echo_handler, mode=0o660):
        mode = stat.S_IMODE(sock.stat().st_mode)
        assert mode == 0o660


def test_stale_socket_cleanup(tmp_path: Path) -> None:
    sock = tmp_path / "stale.sock"
    # Create a "stale" socket file from a crashed previous run.
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind(str(sock))
    s.close()  # nobody listening — file remains
    assert sock.exists()

    with UnixServer(sock, echo_handler):
        # Server should have cleaned it up and bound a fresh one.
        client = UnixClient(sock, timeout=2.0, retries=0)
        assert client.request({"ping": 1}) == {"echo": {"ping": 1}}


def test_socket_in_use_refused(tmp_path: Path) -> None:
    sock = tmp_path / "busy.sock"
    with UnixServer(sock, echo_handler):
        with pytest.raises(FileExistsError):
            UnixServer(sock, echo_handler).start()


def test_concurrent_clients(tmp_path: Path) -> None:
    sock = tmp_path / "concurrent.sock"

    def handler(req: dict) -> dict:
        # Sleep a touch to force overlap.
        time.sleep(0.01)
        return {"n": req["n"] * 2}

    results: dict[int, int] = {}
    errors: list[Exception] = []

    def worker(i: int) -> None:
        try:
            c = UnixClient(sock, timeout=5.0)
            r = c.request({"n": i})
            results[i] = r["n"]
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    with UnixServer(sock, handler):
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

    assert not errors, errors
    assert results == {i: i * 2 for i in range(10)}


def test_notify_no_response(tmp_path: Path) -> None:
    sock = tmp_path / "notify.sock"
    seen: list[dict] = []

    def handler(req: dict) -> None:
        seen.append(req)
        return None

    with UnixServer(sock, handler):
        UnixClient(sock).notify({"event": "fire"})
        # Give the server thread a moment to consume.
        for _ in range(100):
            if seen:
                break
            time.sleep(0.01)
    assert seen == [{"event": "fire"}]


def test_client_retries_until_server_up(tmp_path: Path) -> None:
    sock = tmp_path / "late.sock"

    def start_late() -> None:
        time.sleep(0.3)
        srv = UnixServer(sock, echo_handler)
        srv.start()
        # keep alive long enough for the request
        time.sleep(1.0)
        srv.stop()

    t = threading.Thread(target=start_late, daemon=True)
    t.start()

    client = UnixClient(sock, timeout=2.0, retries=5, retry_backoff=0.15)
    resp = client.request({"slow": True})
    assert resp == {"echo": {"slow": True}}
    t.join(timeout=3)


def test_handler_exception_returns_error(tmp_path: Path) -> None:
    sock = tmp_path / "boom.sock"

    def handler(req: dict) -> dict:
        raise RuntimeError("kaboom")

    with UnixServer(sock, handler):
        resp = UnixClient(sock).request({"x": 1})
        assert resp["type"] == "RuntimeError"
        assert resp["error"] == "kaboom"


def test_double_start_rejected(tmp_path: Path) -> None:
    sock = tmp_path / "dbl.sock"
    srv = UnixServer(sock, echo_handler)
    srv.start()
    try:
        with pytest.raises(RuntimeError):
            srv.start()
    finally:
        srv.stop()


def test_socket_file_removed_on_stop(tmp_path: Path) -> None:
    sock = tmp_path / "cleanup.sock"
    srv = UnixServer(sock, echo_handler)
    srv.start()
    assert sock.exists()
    srv.stop()
    assert not sock.exists()
