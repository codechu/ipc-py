```text
   ┌─────────────────┐      ╔═════════════════╗
   │  codechu — ipc  │═════>║   your daemon   ║
   │  client         │ JSON ║   handler(req)  ║
   │  request()      │<═════║   → response    ║
   └─────────────────┘ line ╚═════════════════╝
        unix socket  ·  fifo  ·  json-line  ·  pidfile
```

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

## License

MIT — see [LICENSE](LICENSE).
