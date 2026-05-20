"""codechu-ipc — stdlib-only local IPC.

Re-exports:

- :class:`UnixServer` / :class:`UnixClient` — JSON-line over a Unix
  domain socket.
- :class:`JsonLineProtocol` — encode/decode framing helper.
- :class:`FifoChannel` — JSON-line over a named pipe (FIFO).
- :func:`pidfile` — exclusive PID-file context manager for daemons.
"""

from __future__ import annotations

from .client import UnixClient
from .fifo import FifoChannel
from .lifecycle import pidfile
from .protocol import JsonLineProtocol
from .server import UnixServer

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "FifoChannel",
    "JsonLineProtocol",
    "UnixClient",
    "UnixServer",
    "pidfile",
]
