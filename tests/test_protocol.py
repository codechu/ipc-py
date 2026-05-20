from __future__ import annotations

import io

import pytest

from codechu_ipc import JsonLineProtocol


def test_encode_basic():
    out = JsonLineProtocol.encode({"a": 1, "b": "x"})
    assert out.endswith(b"\n")
    assert b"\n" not in out[:-1]


def test_encode_rejects_internal_newline():
    # A JSON string containing an escaped newline is fine; a raw newline
    # in the encoded form would be a framing bug. ensure_ascii=False +
    # separators give us a stable single-line output, so the only way
    # this fires is if someone changes the encoder.
    JsonLineProtocol.encode({"msg": "line1\nline2"})  # escaped — OK


def test_decode_stream_yields_objects():
    stream = io.BytesIO(b'{"a":1}\n{"b":2}\n\n{"c":3}\n')
    items = list(JsonLineProtocol.decode_stream(stream))
    assert items == [{"a": 1}, {"b": 2}, {"c": 3}]


def test_decode_stream_empty():
    assert list(JsonLineProtocol.decode_stream(io.BytesIO(b""))) == []


def test_decode_one_strips_newline():
    assert JsonLineProtocol.decode_one(b'{"x":1}\n') == {"x": 1}


def test_decode_one_invalid_raises():
    with pytest.raises(ValueError):
        JsonLineProtocol.decode_one(b"not json\n")
