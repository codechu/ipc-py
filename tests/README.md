# Tests

```bash
pip install -e ".[dev]"
pytest -q
```

Coverage targets:

- `test_protocol.py` — JSON-line encode/decode, edge cases.
- `test_unix_socket.py` — round-trip, permissions, stale cleanup,
  concurrent clients (10x), retry-until-up, handler-exception
  envelope, double-start guard.
- `test_fifo.py` — auto-creation, send/recv round-trip,
  no-reader `BrokenPipeError`, non-FIFO file rejection.
- `test_lifecycle.py` — `pidfile` writes PID, removes on exit, blocks
  double-start (subprocess-based), can be re-acquired after release.

All tests use `tmp_path` for socket / FIFO files and do not touch
the host filesystem outside the temp dir.
