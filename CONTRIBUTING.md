# Contributing to codechu-ipc

Thanks for thinking about contributing. `codechu-ipc` is a small set
of stdlib-only local-IPC primitives — Unix sockets, FIFOs, JSON-line
framing, pidfiles. Patches that stay focused, well-tested, and
dependency-free are warmly received.

## Development setup

```bash
git clone https://github.com/codechu/codechu-ipc-py.git
cd codechu-ipc-py
pip install -e ".[dev]"
pytest -q
ruff check src tests
```

## Workflow

- Branch names: `feature/<short>`, `fix/<short>`, `refactor/<short>`,
  `docs/<short>`, `test/<short>`.
- Commit messages: [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`).
- One change per PR — keep diffs reviewable.

## Bug reports

A useful bug report includes:

- OS + kernel version + Python version.
- The exact sequence of calls (server side and client side).
- The behaviour you observed vs. the behaviour you expected.
- For socket / FIFO permission bugs: `ls -la` on the socket file.

## Tests

- `pytest -q` must pass.
- New feature → new test. Use `tmp_path` for socket and FIFO files
  so tests stay hermetic.
- Concurrency tests should bound their waits — no unconditional
  `time.sleep`. Use a deadline loop with a tight poll interval.

## Public API discipline

The public surface is `UnixServer`, `UnixClient`, `JsonLineProtocol`,
`FifoChannel`, and `pidfile`. Wire formats (the JSON-line framing)
are part of the contract; changing them is a major version bump.

No external runtime dependencies. If you need one, the answer is
almost always "no, write it in stdlib".

## Style

- `ruff check` + `ruff format` clean.
- Type hints on public APIs (`from __future__ import annotations`).

## Security

If you find a security issue, see [SECURITY.md](SECURITY.md) — do not
open a public issue for it.
