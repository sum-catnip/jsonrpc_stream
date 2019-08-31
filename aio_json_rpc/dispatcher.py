from aio_json_rpc import exceptions
import enum
import types
import typing
import inspect
import functools


class DuplicateMethodError(ValueError): pass


class MethodDispatcher:
    def __init__(self):
        self.methods: typing.Dict[str, typing.Callable] = {}

    def add_target(self, name: str, coro: typing.Callable):
        if name in self.methods: raise DuplicateMethodError(name)
        self.methods[name] = coro

    async def dispatch(
        self,
        name: str,
        params: typing.Any
    ) -> typing.Any:
        try:
            if isinstance(params, list):
                return await self.methods[name](*params)
            elif isinstance(params, dict):
                return await self.methods[name](**params)
            elif params is None:
                return await self.methods[name]()
            else: return await self.methods[name](params)
        except KeyError:
            raise exceptions.JsonRpcMethodNotFound.from_method(name)
        except TypeError:
            raise exceptions.JsonRpcInvalidParams.from_method(name)


class DiscoverMode(enum.Enum):
    decorated = enum.auto()
    public    = enum.auto()
    all       = enum.auto()


def dispatch_target(name: typing.Optional[str] = None) -> typing.Callable:
    if callable(name):
        name.__dict__['__jsonrpc_dispatch'] = name.__name__
        return name

    def decorator(method: typing.Callable) -> typing.Callable:
        method.__dict__['__jsonrpc_dispatch'] = name
        return method
    return decorator


class DispatchNamespace:
    def __init__(self, obj: typing.Any, mode: DiscoverMode):
        if mode == DiscoverMode.decorated:
            def istarget(obj: typing.Any):
                return hasattr(obj, '__jsonrpc_dispatch')
        elif mode == DiscoverMode.public:
            def istarget(obj: typing.Any):
                return callable(obj) and not obj.__name__.startswith('_')
        elif mode == DiscoverMode.all:
            def istarget(obj: typing.Any): return callable(obj)

        targets = inspect.getmembers(obj, predicate=istarget)
        self.targets: typing.Dict[str, typing.Callable] = {}
        for name, target in targets:
            name = getattr(target, '__jsonrpc_dispatch', name)
            if not inspect.iscoroutinefunction(target):
                async def async_wrapper(*args, **kwargs):
                    return target(*args, **kwargs)
                self.targets[name] = async_wrapper
            else: self.targets[name] = target

    async def call(self, method: str, *args, **kwargs):
        try: return await self.targets[method](*args, **kwargs)
        except KeyError:
            raise exceptions.JsonRpcMethodNotFound.from_method(method)
        except TypeError:
            raise exceptions.JsonRpcInvalidParams.from_method(method)

    async def call_paramsobj(self, method: str, params: typing.Any):
        if isinstance(params, list):
            return await self.call(method, *params)
        elif isinstance(params, dict):
            return await self.call(method, **params)
        elif params is None:
            return await self.call(method)
        else: return await self.call(method, params)


def proxy_target(name: typing.Optional[str] = None) -> typing.Callable:
    if callable(name):
        name.__dict__['__jsonrpc_proxy'] = name.__name__
        return name

    def decorator(method: typing.Callable) -> typing.Callable:
        method.__dict__['__jsonrpc_proxy'] = name
        return method
    return decorator


class ProxyNamespace:
    def __init__(
        self,
        name:     str,
        obj:      typing.Any,
        mode:     DiscoverMode,
        callback: typing.Callable
    ):
        self.name = name
        if mode == DiscoverMode.decorated:
            def istarget(obj: typing.Any):
                return hasattr(obj, '__jsonrpc_proxy')
        elif mode == DiscoverMode.public:
            def istarget(obj: typing.Any):
                return callable(obj) and not obj.__name__.startswith('_')
        elif mode == DiscoverMode.all:
            def istarget(obj: typing.Any):
                return isinstance(obj, types.MethodType)

        targets = inspect.getmembers(obj, predicate=istarget)
        self.targets: typing.Dict[str, typing.Callable] = {}

        for name, target in targets:
            name = getattr(target, '__jsonrpc_proxy', name)

            def capture(name=name):
                @functools.wraps(target)
                async def wrapper(*args, **kwargs):
                    return await callback(self.name, name, *args, **kwargs)
                return wrapper
            setattr(obj, target.__name__, capture())
