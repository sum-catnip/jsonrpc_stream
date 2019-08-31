# type: ignore
from jsonrpc_stream.streams   import ContentLengthEntityStream
from jsonrpc_stream.contracts import RpcEntityStream
from jsonrpc_stream import protocol
from jsonrpc_stream.serializers import JsonSerializer

import json
import asyncio
import pytest


class MockReader(asyncio.StreamReader):
    def __init__(self, string: str):
        super().__init__()
        self.feed_data(string.encode())
        self.feed_eof()


class MockWriter:
    def __init__(self):
        self.buffer = b''

    def write(self, data: bytes):
        self.buffer += data

    async def drain(self): pass
    def close(self): pass
    def write_enf(self): pass


def create_stream(source: str, sink: MockWriter) -> RpcEntityStream:
    return ContentLengthEntityStream(
        JsonSerializer('utf-8'), MockReader(source), sink
    )


async def fetch_entity_assert(expectation: dict, raw: str):
    s = create_stream(raw, MockWriter())
    reality = await s.fetch_entity()

    assert expectation == reality.to_dict()


@pytest.mark.asyncio
async def test_fetch_request_params():
    expectation = {
        "jsonrpc": "2.0",
        "method": "subtract",
        "params": [42, 23],
        "id": 1
    }
    raw = json.dumps(expectation)
    raw = f'Content-Length: {len(raw)}\r\n\r\n{raw}'

    await fetch_entity_assert(expectation, raw)


@pytest.mark.asyncio
async def test_fetch_request_noparams():
    expectation = {
        "jsonrpc": "2.0",
        "method": "subtract",
        "id": 1
    }
    raw = json.dumps(expectation)
    raw = f'Content-Length: {len(raw)}\r\n\r\n{raw}'

    await fetch_entity_assert(expectation, raw)


@pytest.mark.asyncio
async def test_fetch_header_tolerance():
    expectation = {
        "jsonrpc": "2.0",
        "method": "yeet",
    }
    raw = json.dumps(expectation)
    raw = [
        'salad: kek',
        f'Content-Length: {len(raw)}',
        'headerwithoutvalue',
        '',
        raw
    ]

    await fetch_entity_assert(expectation, '\r\n'.join(raw))


@pytest.mark.asyncio
async def test_fetch_multiple():
    count = 10

    expectation = {
        "jsonrpc": "2.0",
        "result": 1337,
        "id": "kek"
    }
    raw = json.dumps(expectation)
    raw = f'Content-Length: {len(raw)}\r\n\r\n{raw}'
    raw *= count

    s = create_stream(raw, MockWriter())
    for i in range(count):
        reality = await s.fetch_entity()
        assert expectation == reality.to_dict()

    for i in range(5):
        assert None is await s.fetch_entity()


@pytest.mark.asyncio
async def test_dispatch_request():
    expectation = protocol.RpcRequest(0, 'yeet', None)
    buffer = MockWriter()
    dispatch_stream = create_stream('', buffer)
    await dispatch_stream.dispatch_entity(expectation)

    fetch_stream = create_stream(
        buffer.buffer.decode('utf-8'), MockWriter
    )
    assert expectation == await fetch_stream.fetch_entity()


@pytest.mark.asyncio
async def test_fetch_no_contentlen():
    request = 'topkek: hi\r\n\r\n{"jsonrpc": "2.0", "method": "kek"}'
    s = create_stream(request, MockWriter())

    assert await s.fetch_entity() is None


@pytest.mark.asyncio
async def test_fetch_invalid_contentlen():
    request = 'Content-Length: hi\r\n\r\n{"jsonrpc": "2.0", "method": "kek"}'
    s = create_stream(request, MockWriter())

    assert await s.fetch_entity() is None
