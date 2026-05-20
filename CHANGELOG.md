# Changelog

[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) + [SemVer](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2026-05-20

### Added
- `UnixServer(path, handler, *, mode=0o600, backlog=16)` — threaded
  Unix-domain-socket server speaking JSON lines. Auto-cleans stale
  socket files; refuses to overwrite a live socket. Handler
  exceptions are returned to the client as `{"error", "type"}`
  envelopes; the server keeps serving. Context-manager protocol.
- `UnixClient(path, *, timeout=5.0, retries=3, retry_backoff=0.5)` —
  synchronous client with `request()` (round-trip) and `notify()`
  (fire-and-forget). Exponential backoff retry on
  `ConnectionRefusedError` / `FileNotFoundError`.
- `JsonLineProtocol` — framing helper. `encode(payload) → bytes` and
  `decode_stream(reader)` generator over a binary stream.
- `FifoChannel(path, *, mode=0o600)` — JSON-line over a named pipe.
  Auto-creates the FIFO; non-blocking `send()` (raises
  `BrokenPipeError` when no reader is attached); blocking `recv()`.
- `pidfile(path)` — context manager that writes the current PID,
  takes an exclusive `flock` advisory lock, and removes the file on
  exit. Raises `BlockingIOError` if another process already holds
  the lock — drop-in "don't start twice" guard for sidecar daemons.

### Design notes
- Stdlib-only: `socket`, `threading`, `fcntl`, `os`, `json`.
- Linux is the primary target; BSD/macOS are best-effort.
- Permissions default to `0o600` everywhere (owner-only).
