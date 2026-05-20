"""JSON-line framing protocol.

One JSON object per line; UTF-8 encoded; newline-terminated. Simple,
debuggable, and trivially parseable from any language.
"""

from __future__ import annotations

import json
from typing import IO, Any, Iterator


class JsonLineProtocol:
    """Encode/decode JSON-line framed messages.

    Encoding: ``json.dumps(payload) + "\\n"`` as UTF-8 bytes.

    Decoding: read one line at a time from a binary reader; each
    non-empty line is parsed as a JSON object.
    """

    @staticmethod
    def encode(payload: Any) -> bytes:
        """Encode a JSON-serialisable payload as one framed line.

        Raises :class:`ValueError` if the encoded payload itself
        contains an embedded newline (would break framing).
        """
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if "\n" in line:
            raise ValueError("encoded payload contains newline; framing broken")
        return (line + "\n").encode("utf-8")

    @staticmethod
    def decode_stream(reader: IO[bytes]) -> Iterator[dict]:
        """Yield parsed objects from a readable binary stream.

        Blank lines are skipped. Stops on EOF (empty read).
        """
        while True:
            line = reader.readline()
            if not line:
                return
            stripped = line.strip()
            if not stripped:
                continue
            yield json.loads(stripped)

    @staticmethod
    def decode_one(line: bytes) -> dict:
        """Decode a single framed line (with or without trailing newline)."""
        return json.loads(line.strip())
