```text
━━━━━━━━━━━━ c o d e c h u  ·  i p c ━━━━━━━━━━━━

   $ nc -U /run/codechu/myapp/control.sock
   {"cmd":"status"}
   {"running":true,"queue":42,"uptime":"3h12m"}
   {"cmd":"reload","section":"watchdog"}
   {"ok":true}

   unix socket  ·  fifo  ·  json-line  ·  pidfile

━━━━━━━━ local IPC the deliberately-boring way. ━━━━━━━━
```

[![PyPI](https://img.shields.io/pypi/v/codechu-ipc.svg)](https://pypi.org/project/codechu-ipc/)
[![Python](https://img.shields.io/pypi/pyversions/codechu-ipc.svg)](https://pypi.org/project/codechu-ipc/)
[![CI](https://github.com/codechu/ipc-py/actions/workflows/ci.yml/badge.svg)](https://github.com/codechu/ipc-py/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> *Local IPC the boring way — Unix sockets, FIFOs, one JSON object per line.*

# codechu-ipc

Stdlib-only local IPC for Linux daemons and sidecars: Unix domain
sockets, named pipes (FIFOs), JSON-line framing, pidfile lifecycle.
The deliberately-boring option for when you need a daemon and a
control socket and don't want gRPC, dbus, or a 200 MB dependency
tree.

## Install

```bash
pip install codechu-ipc
```

Python 3.10+. Zero third-party dependencies. Linux is the primary
target; BSD / macOS are best-effort.

## Quick example

```python
from codechu_ipc import UnixServer, UnixClient, FifoChannel, pidfile

# --- Server ----------------------------------------------------------
def handler(req: dict) -> dict | None:
    if req["cmd"] == "status":
        return {"running": True}
    if req["cmd"] == "shutdown":
        signal_stop()
        return None                  # → notification, no response

with pidfile("/run/codechu/myapp/daemon.pid"), \
     UnixServer("/run/codechu/myapp/control.sock", handler):
    serve_forever()

# --- Client ----------------------------------------------------------
client = UnixClient("/run/codechu/myapp/control.sock")
client.request({"cmd": "status"})    # → {"running": True}
client.notify({"cmd": "shutdown"})   # fire-and-forget

# --- FIFO (one-way event stream) -------------------------------------
ch = FifoChannel("/run/codechu/myapp/events.fifo")
ch.send({"event": "rescan-done"})
msg = ch.recv()
```

## What you get

- **`UnixServer(path, handler)`** — accept-loop thread, one worker
  per connection, owner-only socket (`0o600`) by default. Cleans
  stale sockets from prior crashed runs; refuses to overwrite a
  live one. Handler exceptions become JSON error responses.
- **`UnixClient(path)`** — `request()` (await response),
  `notify()` (fire-and-forget). Optional retries + backoff for
  start-up races against the server.
- **`FifoChannel(path)`** — bidirectional named-pipe helper with
  the same JSON-line framing as the socket transport.
- **`JsonLineProtocol`** — the shared framing primitive: one JSON
  object per `\n`-terminated line. Trivial to inspect with
  `nc -U` or `socat`.
- **`pidfile(path)`** — context manager that writes the current
  PID and removes the file on exit; refuses to start if a live
  process is already there.

## Why JSON-line?

One object per line. No length prefixes, no schemas, no framing
bugs. Easy to tail, easy to pipe, easy to debug. Backpressure is
the OS socket buffer's problem. If you need binary framing,
multiplexing, or RPC semantics — use gRPC, not this.

## Read more

- [API reference](docs/API.md) — every public symbol with full
  signatures.
- [Changelog](CHANGELOG.md)

## Family

| Library | Purpose |
|---------|---------|
| [codechu-events](https://pypi.org/project/codechu-events/) | Thread-safe multi-channel pub/sub bus |
| [codechu-log](https://pypi.org/project/codechu-log/) | Structured logging — context, JSON, rotation |
| [codechu-xdg](https://pypi.org/project/codechu-xdg/) | XDG Base Directory helpers, vendor-namespaced |
| [codechu-fs](https://pypi.org/project/codechu-fs/) | Filesystem primitives — atomic write, XDG trash |
| [codechu-config](https://pypi.org/project/codechu-config/) | Schema-driven config — atomic save, migrations |

Full ecosystem: [github.com/codechu](https://github.com/codechu).

## Credits

- JSON-line convention per [jsonlines.org](https://jsonlines.org/).
- POSIX `AF_UNIX` semantics per the
  [Linux unix(7) manual page](https://man7.org/linux/man-pages/man7/unix.7.html).

## License

MIT — see [LICENSE](LICENSE).

Part of [Codechu](https://github.com/codechu).
