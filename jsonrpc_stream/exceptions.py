import typing
import traceback

from jsonrpc_stream import protocol


class JsonRpcException(Exception):
    CODE: int = -32001

    def __init__(
        self,
        code:    int        = None,
        message: str        = None,
        data:    typing.Any = None
    ):
        self.message = str(message) or getattr(self.__class__, 'MESSAGE') or ''
        self.code = code or getattr(self.__class__, 'CODE', -32001)
        self.data = data

    @staticmethod
    def from_error(error: protocol.RpcErrorDetails):
        try:
            # is server error
            if -32000 <= error.code <= -32099:
                return JsonRpcServerError(
                    message=error.message,
                    data=error.data
                )
            else: return rpc_exceptions[error.code](
                message=error.message,
                data=error.data
            )
        except KeyError: return JsonRpcException(
            error.code, error.message, error.data
        )

    @classmethod
    def from_ex(cls, ex: Exception, msg: str = None) -> 'JsonRpcException':
        return cls(
            message=msg or str(ex),
            data=traceback.format_exc()
        )

    def to_error(self) -> protocol.RpcErrorDetails:
        return protocol.RpcErrorDetails(
            code=self.code,
            message=self.message,
            data=self.data
        )


rpc_exceptions: typing.Dict[int, typing.Type[JsonRpcException]] = {}


def exception_with_code(exception: typing.Type[JsonRpcException]) -> type:
    rpc_exceptions[exception.CODE] = exception
    return exception


@exception_with_code
class JsonRpcParseError(JsonRpcException):
    CODE:    int = -32700
    MESSAGE: str = 'received malformed json!'


@exception_with_code
class JsonRpcInvalidRequest(JsonRpcException):
    CODE:    int = -32600
    MESSAGE: str = 'invalid request!'


@exception_with_code
class JsonRpcMethodNotFound(JsonRpcException):
    CODE:    int = -32601
    MESSAGE: str = 'no such method found!'

    @classmethod
    def from_method(cls, method: str) -> 'JsonRpcMethodNotFound':
        return cls(
            message=f'no method with name {method}'
        )


@exception_with_code
class JsonRpcInvalidParams(JsonRpcException):
    CODE:    int = -32602
    MESSAGE: str = 'invalid parameters provided'

    @classmethod
    def from_method(cls, method: str) -> 'JsonRpcInvalidParams':
        return cls(
            message=f'invalid parameters in call to function {method}'
        )


@exception_with_code
class JsonRpcInternalError(JsonRpcException):
    CODE:    int = -32603
    MESSAGE: str = 'internal jsonrpc error!'


@exception_with_code
class JsonRpcServerError(JsonRpcException):
    CODE:    int = -32000
    MESSAGE: str = 'server error!'
