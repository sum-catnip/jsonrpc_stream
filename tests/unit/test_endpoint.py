from jsonrpc_stream.endpoint import JsonRpcEndpoint
from jsonrpc_stream import dispatcher
from jsonrpc_stream import protocol as pro

import pytest


@pytest.mark.asyncio
async def test_handle_request():
    class Kek:
        @dispatcher.dispatch_target
        async def yeet(self): return 'kektop'

    e = JsonRpcEndpoint(None)
    e.attach_dispatcher(Kek())
    r = await e._handle_request(pro.RpcRequest(0, 'Kek/yeet', None))
    assert r == pro.RpcResult(id=0, result='kektop', jsonrpc='2.0')


@pytest.mark.asyncio
async def test_handle_request_params():
    class Yeet:
        @dispatcher.dispatch_target
        async def yeet(self, a: str): return a

    e = JsonRpcEndpoint(None)
    e.attach_dispatcher(Yeet())
    r = await e._handle_request(
        pro.RpcRequest(0, 'Yeet/yeet', ['salad'])
    )
    assert r == pro.RpcResult(id=0, result='salad', jsonrpc='2.0')
