from jsonrpc_stream import dispatcher as di
from jsonrpc_stream import exceptions

import pytest


@pytest.mark.asyncio
async def test_dispatcher_decorated():
    class Kek:
        @di.dispatch_target
        def topkek(self): return 'yee'

        @di.dispatch_target
        async def kektop(self, a: str): return a

    n = di.DispatchNamespace(Kek(), di.DiscoverMode.decorated)
    assert await n.call('topkek') == 'yee'
    assert await n.call('kektop', 'salad') == 'salad'


@pytest.mark.asyncio
async def test_dispatcher_public():
    class Kek:
        def topkek(self): return 'yee'

        @di.dispatch_target
        async def _kektop(self, a: str): return a

    n = di.DispatchNamespace(Kek(), di.DiscoverMode.public)
    assert await n.call('topkek') == 'yee'
    with pytest.raises(exceptions.JsonRpcMethodNotFound):
        await n.call('_kektop', 'salad')


@pytest.mark.asyncio
async def test_dispatcher_named():
    class Kek:
        @di.dispatch_target('yeet')
        def topkek(self): return 'yee'

    n = di.DispatchNamespace(Kek(), di.DiscoverMode.public)
    assert await n.call('yeet') == 'yee'


@pytest.mark.asyncio
async def test_dispatcher_all():
    class Kek:
        async def _kektop(self, a: str): return a

    n = di.DispatchNamespace(Kek(), di.DiscoverMode.all)
    assert await n.call('_kektop', 'a') == 'a'


@pytest.mark.asyncio
async def test_dispatcher_raises_paramserr():
    class Kek:
        async def kektop(self, a: str): return a

    n = di.DispatchNamespace(Kek(), di.DiscoverMode.all)
    with pytest.raises(exceptions.JsonRpcInvalidParams):
        await n.call('kektop', a='a', b='b')

    with pytest.raises(exceptions.JsonRpcInvalidParams):
        await n.call('kektop', 'a', 'b')

    with pytest.raises(exceptions.JsonRpcInvalidParams):
        await n.call('kektop')


@pytest.mark.asyncio
async def test_proxy_decorated():
    class Kek:
        @di.proxy_target
        def kektop(): pass

    async def callback(namespace, name, *args, **kwargs):
        return f'{namespace}/{name}/{args}/{kwargs}'

    k = Kek()
    di.ProxyNamespace('yee', k, di.DiscoverMode.decorated, callback)

    assert await k.kektop('a')       == 'yee/kektop/(\'a\',)/{}'
    assert await k.kektop(a='b')     == 'yee/kektop/()/{\'a\': \'b\'}'
    assert await k.kektop(1, 2, c=3) == 'yee/kektop/(1, 2)/{\'c\': 3}'
    assert await k.kektop()          == 'yee/kektop/()/{}'


@pytest.mark.asyncio
async def test_proxy_public():
    class Kek:
        # real params get ignored
        async def kektop(a, b, c): pass
        async def _topkek(self): pass

    async def callback(namespace, name, *args, **kwargs):
        return f'{namespace}/{name}/{args}/{kwargs}'

    k = Kek()
    di.ProxyNamespace('yee', k, di.DiscoverMode.public, callback)

    assert await k.kektop('a')       == 'yee/kektop/(\'a\',)/{}'
    assert await k.kektop(a='b')     == 'yee/kektop/()/{\'a\': \'b\'}'
    # make sure method doesnt get bound
    assert await k.kektop()
    assert await k.kektop(1, 2, c=3) == 'yee/kektop/(1, 2)/{\'c\': 3}'
    assert await k.kektop()          == 'yee/kektop/()/{}'

    assert await k._topkek() is None


@pytest.mark.asyncio
async def test_proxy_all():
    class Kek:
        # real params get ignored
        async def kektop(a, b, c): pass
        async def _topkek(self): pass

    async def callback(namespace, name, *args, **kwargs):
        return f'{namespace}/{name}/{args}/{kwargs}'

    k = Kek()
    di.ProxyNamespace('yee', k, di.DiscoverMode.all, callback)

    assert await k.kektop('a')       == 'yee/kektop/(\'a\',)/{}'
    assert await k.kektop(a='b')     == 'yee/kektop/()/{\'a\': \'b\'}'
    # make sure method doesnt get bound
    assert await k.kektop()
    assert await k.kektop(1, 2, c=3) == 'yee/kektop/(1, 2)/{\'c\': 3}'
    assert await k.kektop()          == 'yee/kektop/()/{}'

    assert await k._topkek() == 'yee/_topkek/()/{}'
