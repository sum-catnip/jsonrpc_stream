from jsonrpc_stream import exceptions
import enum
import types
import typing
import inspect
import functools


class DiscoverMode(enum.Enum):
    decorated = enum.auto()
    public    = enum.auto()
    all       = enum.auto()


class RequestType(enum.Enum):
    request = enum.auto()
    notification = enum.auto()


class DecoratedTarget:
    name: str
    type_: RequestType

    def __init__(self, name: str, type_: RequestType):
        self.name = name
        self.type_ = type_


def mark_method(
    target: typing.Callable,
    name: typing.Optional[str],
    type_: RequestType
):
    setattr(
        target,
        '__jsonrpc__',
        DecoratedTarget(name or target.__name__, type_)
    )


def request(
    method: typing.Callable = None, name: str = None
) -> typing.Callable:
    if not callable(method): return functools.partial(request, name=method)
    mark_method(method, name, RequestType.request)
    return method


def notification(
    method: typing.Callable = None, name: str = None
) -> typing.Callable:
    if not callable(method): return functools.partial(request, name=method)
    mark_method(method, name, RequestType.notification)
    return method


class DispatchNamespace:
    def __init__(self, obj: typing.Any, mode: DiscoverMode):
        if mode == DiscoverMode.decorated:
            def istarget(obj: typing.Any):
                return hasattr(obj, '__jsonrpc__')
        elif mode == DiscoverMode.public:
            def istarget(obj: typing.Any):
                return callable(obj) and not obj.__name__.startswith('_')
        elif mode == DiscoverMode.all:
            def istarget(obj: typing.Any): return callable(obj)

        targets = inspect.getmembers(obj, predicate=istarget)
        self.notifications: typing.Dict[str, typing.Callable] = {}
        self.requests: typing.Dict[str, typing.Callable] = {}
        for name, target in targets:
            mark = getattr(
                target,
                '__jsonrpc__',
                DecoratedTarget(name, RequestType.request)
            )
            if not inspect.iscoroutinefunction(target):
                t = target

                async def async_wrapper(*args, **kwargs):
                    return t(*args, **kwargs)
                target = async_wrapper
            if mark.type_ == RequestType.request:
                self.requests[mark.name] = target
            elif mark.type_ == RequestType.notification:
                self.notifications[mark.name] = target

    async def notify(self, method: str, *args, **kwargs):
        try: await self.notifications[method](*args, **kwargs)
        except KeyError:
            raise exceptions.JsonRpcMethodNotFound.from_method(method)
        except TypeError:
            raise exceptions.JsonRpcInvalidParams.from_method(method)

    async def call(self, method: str, *args, **kwargs):
        try: return await self.requests[method](*args, **kwargs)
        except KeyError:
            raise exceptions.JsonRpcMethodNotFound.from_method(method)
        except TypeError:
            raise exceptions.JsonRpcInvalidParams.from_method(method)


class ProxyNamespace:
    def __init__(
        self,
        name:     str,
        obj:      typing.Any,
        mode:     DiscoverMode,
        callback_request: typing.Callable,
        callback_notify: typing.Callable
    ):
        self.name = name
        if mode == DiscoverMode.decorated:
            def istarget(obj: typing.Any):
                return hasattr(obj, '__jsonrpc__')
        elif mode == DiscoverMode.public:
            def istarget(obj: typing.Any):
                return callable(obj) and not obj.__name__.startswith('_')
        elif mode == DiscoverMode.all:
            def istarget(obj: typing.Any):
                return isinstance(obj, types.MethodType)

        targets = inspect.getmembers(obj, predicate=istarget)
        self.targets: typing.Dict[str, typing.Callable] = {}

        for name, target in targets:
            mark = getattr(
                target,
                '__jsonrpc__',
                DecoratedTarget(name, RequestType.request)
            )

            def capture(mark=mark):
                @functools.wraps(target)
                async def request_wrapper(*args, **kwargs):
                    return await callback_request(
                        self.name, mark.name, *args, **kwargs
                    )

                @functools.wraps(target)
                async def notify_wrapper(*args, **kwargs):
                    return await callback_notify(
                        self.name, mark.name, *args, **kwargs
                    )

                if mark.type_ == RequestType.request: return request_wrapper
                elif mark.type_ == RequestType.notification:
                    return notify_wrapper

            setattr(obj, target.__name__, capture())
