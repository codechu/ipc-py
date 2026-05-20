# API reference — codechu-ipc 0.1.0

Every public symbol, signatures, and edge cases.

## `JsonLineProtocol`

### `JsonLineProtocol.encode(payload: Any) → bytes`

Encode a JSON-serialisable payload as one framed line:
`json.dumps(payload) + "\n"`, UTF-8 encoded, with `ensure_ascii=False`
and compact separators `(",", ":")`.

Raises `ValueError` if the encoded payload itself somehow contains a
raw newline (would break framing).

### `JsonLineProtocol.decode_stream(reader: IO[bytes]) → Iterator[dict]`

Yield parsed objects from a readable binary stream. Reads one line
at a time; blank lines are skipped; iteration stops on EOF.

### `JsonLineProtocol.decode_one(line: bytes) → dict`

Decode a single framed line (trailing newline optional).

## `UnixServer(path, handler, *, mode=0o600, backlog=16)`

Threaded Unix-domain-socket server.

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `path` | `str` / `PathLike` | — | Filesystem path for the socket. |
| `handler` | `Callable[[dict], dict | None]` | — | Returns a dict to reply, `None` for fire-and-forget. |
| `mode` | `int` | `0o600` | Permissions applied with `chmod` after bind. |
| `backlog` | `int` | `16` | `listen()` backlog. |

### `.start() → None`

Bind, `chmod`, listen, start a daemon accept-loop thread. Raises
`RuntimeError` if already started. Cleans up stale socket files
(socket node exists but nobody listening); raises `FileExistsError`
if the path is in use by a live server or is not a socket node.

### `.stop(timeout: float = 2.0) → None`

Signal the accept loop, close the listening socket, join worker
threads (best-effort, up to `timeout` each), unlink the socket file.

### Context manager

`with UnixServer(...) as srv: ...` calls `start()` / `stop()`.

### Handler contract

- Returns `dict` → response is sent as one JSON line.
- Returns `None` → no response (notification).
- Raises `Exception` → server replies with
  `{"error": str(exc), "type": type(exc).__name__}` and continues
  serving.

## `UnixClient(path, *, timeout=5.0, retries=3, retry_backoff=0.5)`

Synchronous Unix-socket client.

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `path` | `str` / `PathLike` | — | Server socket path. |
| `timeout` | `float` | `5.0` | Per-connection socket timeout (seconds). |
| `retries` | `int` | `3` | Additional attempts after the first failure (4 total). |
| `retry_backoff` | `float` | `0.5` | Initial backoff (seconds); doubles per retry. |

### `.request(payload: dict) → dict`

Send one JSON line, read one JSON line back. Raises
`ConnectionError` if the server closes the connection without
responding, or if all retry attempts fail.

### `.notify(payload: dict) → None`

Send one JSON line and close. Does not read a response.

### Retry semantics

Retries cover the **connect** step only — `ConnectionRefusedError`
and `FileNotFoundError` (and other `OSError` subclasses raised by
`socket.connect()`). Backoff schedule: `0.5s, 1.0s, 2.0s, …`
(doubling). Once a connection succeeds, the subsequent `sendall` /
`readline` are not retried.

## `FifoChannel(path, *, mode=0o600)`

Named-pipe (FIFO) channel with JSON-line framing.

Constructor auto-creates the FIFO with `mkfifo(path, mode)` if
missing. Raises `FileExistsError` if the path exists and is not a
FIFO.

### `.send(payload: dict) → None`

Open the FIFO in `O_WRONLY | O_NONBLOCK` mode, write one JSON line,
close. Raises `BrokenPipeError` if no reader is attached (kernel
returns `ENXIO`).

### `.recv() → dict`

Open the FIFO blocking and return the next decoded message. Blocks
until a writer attaches and sends one full JSON line.

### `.unlink() → None`

Remove the FIFO from the filesystem (idempotent — no error if
already gone).

## `pidfile(path) → context manager → Path`

Exclusive PID-file context manager.

1. Creates the parent directory.
2. Opens the file with `O_RDWR | O_CREAT, mode=0o600`.
3. Takes `fcntl.flock(LOCK_EX | LOCK_NB)`. If another process holds
   the lock, raises `BlockingIOError` immediately.
4. Truncates and writes `f"{os.getpid()}\n"`, fsyncs.
5. On exit: releases the lock, removes the file, closes the fd.

Useful for sidecar daemons that must not run twice.

```python
try:
    with pidfile("/run/codechu/myapp/daemon.pid"):
        run()
except BlockingIOError:
    sys.exit("already running")
```
