from jsonrpc_stream import exceptions
from jsonrpc_stream import protocol
from jsonrpc_stream import contracts
from jsonrpc_stream import dispatcher

import logging
import asyncio
import typing
import uuid

logger = logging.getLogger(__name__)


class JsonRpcEndpoint:
    def __init__(
        self,
        stream: contracts.RpcEntityStream,
        namespace_seperator: str = '/',
        timeout: int = 0,
        loop: asyncio.AbstractEventLoop = None
    ):
        self.loop = loop or asyncio.get_event_loop()
        self._timeout = timeout
        self._requests: typing.Dict[typing.Any, asyncio.Future] = {}
        self.stream = stream
        self.namespace_seperator = namespace_seperator
        self.dispatchers: typing.Dict[str, dispatcher.DispatchNamespace] = {}
        self.proxies: typing.Dict[str, dispatcher.ProxyNamespace] = {}
        self._handlers: typing.Dict[type, typing.Callable] = {
            protocol.RpcRequest:      self._handle_request,
            protocol.RpcNotification: self._handle_notification,
            protocol.RpcResult:       self._handle_result,
            protocol.RpcError:        self._handle_error,
            protocol.RpcMalformed:    self._handle_malformed
        }

        self._paramsdispatchers: typing.Dict[type, typing.Callable] = {
            dict: self._dispatch_dict,
            list: self._dispatch_list,
            type(None): self._dispatch_none
        }

    async def _dispatch_dict(self, method, name, params):
        return await method(name, **params)

    async def _dispatch_list(self, method, name, params):
        return await method(name, *params)

    async def _dispatch_none(self, method, name, params):
        return await method(name)

    def _parse_methodname(self, methodname: str) -> typing.Tuple[str, str]:
        parts = methodname.split(self.namespace_seperator)
        try: return (parts[0], parts[1])
        except IndexError: return ('', parts[0])

    async def _dispatch_params(
        self,
        dispatcher: typing.Callable,
        meth: str,
        params: typing.Any
    ) -> typing.Any:
        try: return await self._paramsdispatchers[type(params)](
            dispatcher, meth, params
        )
        except KeyError: return await dispatcher(params)

    async def _handle_request(
        self, request: protocol.RpcRequest
    ) -> protocol.RpcEntity:
        try:
            logger.debug(f'handling request: {request}')
            namespace, method = self._parse_methodname(request.method)
            res = await self._dispatch_params(
                self.dispatchers[namespace].call, method, request.params
            )

            # make arbitrary classes serializable
            if hasattr(res, '__dict__'): res = res.__dict__
            logger.debug(f'method returned result: {res}')
            return protocol.RpcResult(request.id, res)
        except exceptions.JsonRpcException as e:
            logger.debug(f'dispatcher raised rpc exception: {e}')
            return protocol.RpcError(request.id, e.to_error())
        except KeyError:
            return protocol.RpcError(
                request.id,
                exceptions.JsonRpcMethodNotFound.from_method(
                    request.method
                ).to_error()
            )
        except Exception as e:
            logger.debug(f'method raised exception: {e}')
            return protocol.RpcError(
                request.id,
                exceptions.JsonRpcInternalError.from_ex(e).to_error()
            )

    async def _handle_notification(self, notify: protocol.RpcNotification):
        try:
            logger.debug(f'handling notification: {notify}')
            namespace, method = self._parse_methodname(notify.method)
            await self._dispatch_params(
                self.dispatchers[namespace].notify, method, notify.params
            )
        except Exception as e:
            logger.warning(f'error handling notification: {e}')

    async def _handle_result(self, result: protocol.RpcResult):
        try:
            logger.debug(f'handling result: {result}')
            fut = self._requests[result.id]
            if not fut.cancelled(): fut.set_result(result.result)
        except KeyError:
            logger.warning(
                f'received result to non existing request: {result}'
            )

    async def _handle_error(self, error: protocol.RpcError):
        try:
            logger.debug(f'handling error: {error}')
            if error.id is None:
                logger.error(f'received error without id: {error}')
                return

            self._requests[error.id].set_exception(
                exceptions.JsonRpcException.from_error(error.error)
            )
        except KeyError:
            logger.warning(
                f'received error result to non existing request: {error}'
            )

    async def _handle_malformed(
        self, malformed: protocol.RpcMalformed
    ) -> protocol.RpcError:

        logger.debug(f'handling malformed entity: {malformed}')
        exception: exceptions.JsonRpcException
        if isinstance(malformed.exception, exceptions.JsonRpcException):
            exception = malformed.exception
        else: exception = exceptions.JsonRpcInvalidRequest.from_ex(
            malformed.exception
        )

        return protocol.RpcError(malformed.id, exception.to_error())

    async def _handle_single_entity(
        self, entity: protocol.RpcEntity
    ) -> typing.Optional[protocol.RpcEntity]:
        return await self._handlers[type(entity)](entity)

    async def _handle_entity(self, entity: protocol.RpcEntity):
        response: typing.Optional[protocol.RpcEntity]
        if isinstance(entity, protocol.RpcBatch):
            collected: typing.List[protocol.RpcEntity] = []
            for e in entity.entities:
                res = await self._handle_single_entity(e)
                if res: collected.append(res)
            response = protocol.RpcBatch(collected)
        else: response = await self._handle_single_entity(entity)

        if response: await self.stream.dispatch_entity(response)

    async def _start(self):
        while not self.running.done():
            entity = await self.stream.fetch_entity()
            if entity: await self._handle_entity(entity)
            else: self.running.set_result(None)

    async def join(self): await self.running

    def close(self):
        self.stream.close()
        # a buggy stream might not properly return none after calling close
        self.running.set_result(None)

    def start(self) -> 'JsonRpcEndpoint':
        self.running: asyncio.Future = asyncio.Future(loop=self.loop)
        self.loop.create_task(self._start())
        return self

    def attach_dispatcher(
        self,
        target: typing.Any,
        namespace: str = None,
        mode: dispatcher.DiscoverMode = dispatcher.DiscoverMode.decorated
    ) -> 'JsonRpcEndpoint':
        namespace = namespace or target.__class__.__name__
        self.dispatchers[namespace] = dispatcher.DispatchNamespace(
            target, mode
        )

        return self

    def attach_proxy(
        self,
        target: typing.Any,
        namespace: str = None,
        mode: dispatcher.DiscoverMode = dispatcher.DiscoverMode.decorated
    ) -> 'JsonRpcEndpoint':
        namespace = namespace or target.__class__.__name__
        self.proxies[namespace] = dispatcher.ProxyNamespace(
            namespace, target, mode, self.call
        )

        return self

    async def kill_timeout(self, future: asyncio.Future):
        asyncio.sleep(self._timeout)
        future.cancel()

    async def notify(
        self,
        namespace: typing.Optional[str],
        name: str,
        *args: typing.Any,
        **kwargs: typing.Any
    ):
        if not self.running:
            raise RuntimeError('endpoint not running, please call [start]')

        if args and kwargs:
            raise ValueError(
                'request must either have positional or named arguments ' +
                'but not both'
            )

        if namespace: name = namespace + self.namespace_seperator + name
        await self.stream.dispatch_entity(
            protocol.RpcNotification(name, args or kwargs)
        )

    async def call(
        self,
        namespace: typing.Optional[str],
        name: str,
        *args: typing.Any,
        **kwargs: typing.Any
    ):
        if not self.running:
            raise RuntimeError('endpoint not running, please call [start]')

        if args and kwargs:
            raise ValueError(
                'request must either have positional or named arguments ' +
                'but not both'
            )

        id = str(uuid.uuid4())
        if namespace: name = namespace + self.namespace_seperator + name
        await self.stream.dispatch_entity(
            protocol.RpcRequest(id, name, args or kwargs)
        )

        res = self._requests[id] = asyncio.Future()
        if self._timeout: self.loop.create_task(self.kill_timeout(res))
        res = await res
        del self._requests[id]

        return res
