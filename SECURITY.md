# Security policy

`codechu-ipc` is a stdlib-only local-IPC library. It speaks over
**Unix domain sockets and named pipes (FIFOs)** — no network sockets,
no TLS, no authentication beyond filesystem permissions. The
intended use is process-to-process communication on a single host,
typically between a daemon and a CLI run by the same user.

## Supported versions

| Version | Supported |
|---|:---:|
| `main` branch | ✅ |
| Latest minor release (0.x) | ✅ |
| Older releases | ❌ |

Pre-1.0.0 — only the latest minor receives security fixes.

## Reporting a vulnerability

### Preferred path — GitHub Security Advisory (private)

Open a **private** advisory at
[github.com/codechu/codechu-ipc-py/security/advisories/new](https://github.com/codechu/codechu-ipc-py/security/advisories/new).

### Alternative — Email

Write to `security@codechu.com`.

## Scope — what to report

**In scope:**

- Default permissions weaker than `0o600` on socket / FIFO / pidfile
  creation.
- Stale-socket cleanup that overwrites a live socket belonging to
  another process.
- TOCTOU races in the stale-socket probe that could be exploited by
  a same-user process to hijack a socket path.
- JSON decoding paths that crash the server on adversarial input
  (server is meant to log the error and keep serving).
- `pidfile` releasing its lock while the process is still alive,
  allowing a second instance to start.

**Out of scope:**

- Cross-user trust — a different user on the same host with FS access
  is outside the threat model; protect socket paths with directory
  permissions (`$XDG_RUNTIME_DIR` already does this).
- Resource exhaustion from a same-user attacker (you already control
  the process; `ulimit` is your friend).
- Anything network-related — this library does not open network
  sockets.

## Process

Reports are reviewed on a best-effort basis — no fixed SLA. We aim
for coordinated disclosure within **90 days** of the report.

Public disclosure is coordinated after the fix is released.

## Public disclosure

Once a confirmed fix is released:

- A summary is added to the CHANGELOG under the `### Security`
  category.
- A GitHub Security Advisory is published.
- If a CVE was assigned, its number is referenced.
