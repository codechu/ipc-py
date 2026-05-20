"""Server lifecycle helpers: pidfile with advisory lock."""

from __future__ import annotations

import contextlib
import errno
import fcntl
import os
from pathlib import Path
from typing import Iterator


@contextlib.contextmanager
def pidfile(path: str | os.PathLike[str]) -> Iterator[Path]:
    """Acquire an exclusive PID file for the lifetime of the context.

    Writes the current PID into ``path``, takes an exclusive
    :func:`fcntl.flock` advisory lock on it, and removes the file on
    exit. If another process already holds the lock, raises
    :class:`BlockingIOError` immediately — useful to prevent a sidecar
    daemon from starting twice.

    Parent directories are created as needed.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    fd = os.open(p, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                os.close(fd)
                raise BlockingIOError(
                    f"pidfile {p} is locked by another process"
                ) from exc
            os.close(fd)
            raise

        os.ftruncate(fd, 0)
        os.write(fd, f"{os.getpid()}\n".encode("ascii"))
        os.fsync(fd)

        try:
            yield p
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                p.unlink()
            except FileNotFoundError:
                pass
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
