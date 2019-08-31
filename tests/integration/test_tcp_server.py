from jsonrpc_stream import endpoint
from jsonrpc_stream import serializers
from jsonrpc_stream import streams
from jsonrpc_stream import dispatcher

import multiprocessing
import asyncio
import logging
import pytest
import sys


root = logging.getLogger()
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)

root.addHandler(handler)


def server_process():
    async def handle_incomming(reader, writer):
        class Yeet:
            @dispatcher.dispatch_target
            async def yeet(self, a: int): return a

        await endpoint.JsonRpcEndpoint(
            streams.ContentLengthEntityStream(
                serializers.JsonSerializer(), reader, writer
            )
        ).attach_dispatcher(Yeet()).start().join()
        sys.exit(0)

    async def server_main():
        server: asyncio.AbstractServer = await asyncio.start_server(
            handle_incomming, 'localhost', 1338
        )
        await server.serve_forever()

    asyncio.run(server_main())


@pytest.mark.asyncio
async def test_tcp_server_main():
    proc = multiprocessing.Process(target=server_process)
    proc.start()

    reader, writer = await asyncio.open_connection('localhost', 1338)

    e = endpoint.JsonRpcEndpoint(
        streams.ContentLengthEntityStream(
            serializers.JsonSerializer(), reader, writer
        )
    ).start()

    for i in range(100):
        assert await e.call('Yeet', 'yeet', i) == i

    e.close()
    proc.join()
