```text
   ┌─────────────────┐      ╔═════════════════╗
   │  codechu — ipc  │═════>║   your daemon   ║
   │  client         │ JSON ║   handler(req)  ║
   │  request()      │<═════║   → response    ║
   └─────────────────┘ line ╚═════════════════╝
        unix socket  ·  fifo  ·  json-line  ·  pidfile
```

[![PyPI](https://img.shields.io/pypi/v/codechu-ipc.svg)](https://pypi.org/project/codechu-ipc/)
[![Python](https://img.shields.io/pypi/pyversions/codechu-ipc.svg)](https://pypi.org/project/codechu-ipc/)
[![CI](https://github.com/codechu/ipc-py/actions/workflows/ci.yml/badge.svg)](https://github.com/codechu/ipc-py/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> *Local IPC the boring way — Unix sockets, FIFOs, one JSON object per line.*

# codechu-ipc

Stdlib-only local IPC for Linux daemons and sidecars: Unix domain
sockets, named pipes (FIFOs), JSON-line framing, server lifecycle
helpers. No third-party dependencies. Python 3.10+.

Linux is the primary target; BSD/macOS are best-effort (anything
POSIX-y with `AF_UNIX` and `mkfifo` should work).

## Install

```bash
pip install codechu-ipc
```

## API at a glance

```python
from codechu_ipc import UnixServer, UnixClient, FifoChannel, pidfile

# --- Server side ------------------------------------------------------
def handler(req: dict) -> dict:
    return {"echo": req}

with UnixServer("/run/codechu/myapp/control.sock", handler):
    ...  # serve until the context exits

# --- Client side ------------------------------------------------------
client = UnixClient("/run/codechu/myapp/control.sock")
response = client.request({"cmd": "status"})       # → {"echo": ...}
client.notify({"cmd": "shutdown"})                  # fire-and-forget

# --- FIFO -------------------------------------------------------------
ch = FifoChannel("/run/codechu/myapp/events.fifo")
ch.send({"event": "rescan-done"})                   # non-blocking
msg = ch.recv()                                     # blocks for next

# --- Lifecycle --------------------------------------------------------
with pidfile("/run/codechu/myapp/daemon.pid"):
    serve_forever()
```

## Why JSON-line?

- **One object per line.** Trivial to parse from any language, any
  shell pipeline, any log viewer.
- **No length prefixes, no schemas.** Easy to inspect with `nc -U`
  or `socat` while debugging.
- **Backpressure is the OS's problem.** The kernel's socket buffers
  do the queuing; this library stays a thin wrapper.

If you need binary framing, multiplexing, or RPC semantics, you want
gRPC, not this.

## `UnixServer(path, handler, *, mode=0o600, backlog=16)`

- Background accept-loop thread; one worker thread per connection.
- Default socket permissions: **owner-only (0o600)**. Override with
  `mode=`.
- Auto-cleans stale socket files from a crashed previous run; refuses
  to overwrite a live socket (raises `FileExistsError`).
- Handler returning `None` means "this was a notification, send no
  response". Anything else is encoded back as one JSON line.
- Handler exceptions are caught and returned to the client as
  `{"error": "...", "type": "..."}` — the server keeps serving.
- Context manager: `with UnixServer(...) as srv: ...` calls
  `start()`/`stop()` for you.

## `UnixClient(path, *, timeout=5.0, retries=3, retry_backoff=0.5)`

- `request(payload)` — send a JSON line, read one back.
- `notify(payload)` — send a JSON line, close. No response read.
- Retries on `ConnectionRefusedError` / `FileNotFoundError`, with
  exponential backoff (`0.5s, 1.0s, 2.0s, ...`). Useful for the
  short window between "daemon is starting" and "daemon is ready".

## `JsonLineProtocol`

The framing helper, exposed so you can build your own transport on
top of it.

```python
data = JsonLineProtocol.encode({"hello": "world"})  # → b'{"hello":"world"}\n'

with open("/var/log/myapp.jsonl", "rb") as f:
    for obj in JsonLineProtocol.decode_stream(f):
        print(obj)
```

## `FifoChannel(path, *, mode=0o600)`

- Auto-creates the FIFO with `mkfifo` if missing.
- `send()` opens write-side non-blocking — raises `BrokenPipeError`
  if no reader is attached, so you don't deadlock.
- `recv()` opens read-side blocking and yields one decoded message.
- FIFOs are unidirectional; for request/response use `UnixServer`.

## `pidfile(path)`

Context manager that:

1. Creates the parent directory.
2. Opens the pidfile and acquires an exclusive `flock`.
3. If another process holds the lock, raises `BlockingIOError`
   immediately — perfect for "don't start twice" guards.
4. Writes the current PID, releases the lock, removes the file on
   exit (including exceptions).

```python
try:
    with pidfile("/run/codechu/myapp/daemon.pid"):
        run()
except BlockingIOError:
    sys.exit("already running")
```

## Design

- **Pure stdlib.** `socket`, `threading`, `fcntl`, `os`, `json` — no
  more. The whole library is five small modules.
- **Linux-first.** AF_UNIX, `mkfifo`, `flock` — all POSIX, but Linux
  is the platform we run CI on. BSD/macOS work in practice.
- **No magic.** No global registry, no event loop, no decorators.
  You start the server, you stop the server.
- **Crash-safe.** Stale socket files are detected on startup; pidfiles
  are removed on exit; handler exceptions don't kill the server.

## Tests

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests
```

## Documentation

- [API reference](docs/API.md) — every public symbol, signatures, edge cases

## Codechu family

Companion libraries from the Codechu Python ecosystem:

| Library | Purpose |
|---------|---------|
| [codechu-fmt](https://pypi.org/project/codechu-fmt/) | Human-readable formatting — sizes, durations, rates, percent |
| [codechu-meter](https://pypi.org/project/codechu-meter/) | Timing primitives — Stopwatch, ETA, percentile, histogram |
| [codechu-spark](https://pypi.org/project/codechu-spark/) | Unicode sparklines, mini bar charts, heatmaps |
| [codechu-cli](https://pypi.org/project/codechu-cli/) | CLI primitives — colors, progress, spinners, prompts, table |
| [codechu-events](https://pypi.org/project/codechu-events/) | Thread-safe multi-channel pub/sub bus with replay |
| [codechu-xdg](https://pypi.org/project/codechu-xdg/) | XDG Base Directory helpers, vendor-namespaced |
| [codechu-treeviz](https://pypi.org/project/codechu-treeviz/) | Tree visualization — treemap, sunburst, icicle, flame |
| [codechu-fs](https://pypi.org/project/codechu-fs/) | Filesystem primitives — atomic write, XDG trash, safe walk |
| [codechu-term](https://pypi.org/project/codechu-term/) | Terminal capability detection, alt buffer, raw mode |
| [codechu-color](https://pypi.org/project/codechu-color/) | Color palettes, WCAG contrast, color-blind variants |
| [codechu-treedata](https://pypi.org/project/codechu-treedata/) | N-ary tree data structures and algorithms |
| [codechu-log](https://pypi.org/project/codechu-log/) | Structured logging — context, JSON, rotation, redaction |
| [codechu-i18n](https://pypi.org/project/codechu-i18n/) | Internationalization — locale, plural rules, RTL |
| [codechu-config](https://pypi.org/project/codechu-config/) | Schema-driven config — atomic save, migrations |

## Credits

- Unix domain socket + FIFO primitives per POSIX; JSON-line protocol convention from ndjson.org.

## License

MIT — see [LICENSE](LICENSE).
