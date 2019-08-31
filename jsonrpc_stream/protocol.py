from dataclasses import dataclass
import typing


def add_if(data: dict, name: str, value: typing.Any) -> dict:
    if value: data[name] = value
    return data


@dataclass
class RpcEntity:
    def to_dict(self):                   raise NotImplementedError
    def __init__(self, *args, **kwargs): raise NotImplementedError


@dataclass
class RpcIDEntity(RpcEntity):
    id: typing.Union[int, str, None]
    def __init__(self, *args, **kwargs): raise NotImplementedError


@dataclass
class RpcRequest(RpcIDEntity):
    method: str
    params: typing.Union[tuple, list, dict, None]
    jsonrpc: str = '2.0'

    def to_dict(self):
        return add_if({
            'id': self.id,
            'method': self.method,
            'jsonrpc': self.jsonrpc
        }, 'params', self.params)


@dataclass
class RpcNotification(RpcEntity):
    method: str
    params: typing.Union[list, dict, None]
    jsonrpc: str = '2.0'

    def to_dict(self):
        return add_if({
            'method': self.method,
            'jsonrpc': self.jsonrpc
        }, 'params', self.params)


@dataclass
class RpcResult(RpcIDEntity):
    result: typing.Any
    jsonrpc: str = '2.0'

    def to_dict(self):
        return {
            'id': self.id,
            'result': self.result,
            'jsonrpc': self.jsonrpc
        }


@dataclass
class RpcErrorDetails:
    code:    int
    message: str
    data:    typing.Any

    def to_dict(self):
        return add_if({
            'code': self.code,
            'message': self.message,
        }, 'data', self.data)


@dataclass
class RpcError(RpcIDEntity):
    error: RpcErrorDetails
    jsonrpc: str = '2.0'

    def to_dict(self):
        return {
            'id': self.id,
            'error': self.error.to_dict(),
            'jsonrpc': self.jsonrpc
        }


@dataclass
class RpcBatch(RpcEntity):
    entities: typing.List[RpcEntity]

    def to_dict(self):
        return [x.to_dict() for x in self.entities]


@dataclass
class RpcMalformed(RpcIDEntity):
    exception: Exception

    def to_dict(self):
        raise NotImplementedError(
            'cannot serialize a malformed rpc entity'
        )
