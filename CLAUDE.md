# CLAUDE.md — codechu-ipc

Bootstrap per `codechu-org/ai/AGENTS.md` §0 before any work. Prefer
the local clone at `$org_home/codechu-org/ai/AGENTS.md` (if
`~/.config/codechu/config.toml` has `org_home` set); otherwise
WebFetch the public raw URL
<https://raw.githubusercontent.com/codechu/codechu-org/main/ai/AGENTS.md>.
This file lists only product-local overrides.

## Product-local notes

- Pure stdlib local IPC library. **No** external runtime
  dependencies. Linux-first (Unix sockets, FIFOs, PID files).
- Public API: `UnixServer`, `UnixClient`, `JsonLineProtocol`,
  `FifoChannel`, `pidfile`.
- JSON-line is the framing contract: one JSON object per `\n`. A
  message must never contain a literal newline outside a quoted
  string; framing changes are breaking.
- Socket paths must live under `$XDG_RUNTIME_DIR/codechu/<app>/`.
  Permissions are `0o600` for sockets and `0o644` for PID files —
  do not loosen.
- `pidfile()` uses `fcntl.flock(LOCK_EX | LOCK_NB)`; stale-file
  cleanup is the holder's responsibility, never the caller's.
- Coverage target: ≥80 % (bootstrap; will tighten as API stabilises).

## Discipline reminders (org rules apply)

- Conventional Commits, no AI signature.
- No `--no-verify`, no force push, no unapproved publish.
- See `codechu-org/ai/AGENTS.md` for the full list.
