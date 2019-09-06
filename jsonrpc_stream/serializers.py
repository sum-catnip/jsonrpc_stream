from jsonrpc_stream import contracts
from jsonrpc_stream import protocol
from jsonrpc_stream import exceptions

try: import ujson as json
except ImportError: import json  # type: ignore


class BaseSerializer(contracts.RpcEntitySerializer):
    def __init__(self, version: str = '2.0'):
        self.version = version

    def handle_request(self, data: dict) -> protocol.RpcRequest:
        return protocol.RpcRequest(
            data['id'], data['method'], data.get('params'),
            jsonrpc=self.version
        )

    def handle_notification(self, data: dict) -> protocol.RpcNotification:
        return protocol.RpcNotification(
            data['method'], data.get('params'),
            jsonrpc=self.version
        )

    def handle_result(self, data: dict) -> protocol.RpcResult:
        return protocol.RpcResult(
            data['id'], data['result'], jsonrpc=self.version
        )

    def handle_error(self, data: dict) -> protocol.RpcEntity:
        try:
            return protocol.RpcError(
                data.get('id'), protocol.RpcErrorDetails(
                    data['error']['code'],
                    data['error']['message'],
                    data['error'].get('data'),
                ), jsonrpc=self.version
            )
        except KeyError as e:
            return protocol.RpcMalformed(
                data.get(id),
                exceptions.JsonRpcInvalidRequest(
                    message=f'missing attribute [{e}] in error: {data}'
                )
            )

    def handle_entity(self, data: dict) -> protocol.RpcEntity:
        if 'method' in data:
            if 'id' in data:
                return self.handle_request(data)
            else: return self.handle_notification(data)
        elif 'result' in data:
            return self.handle_result(data)
        elif 'error' in data:
            return self.handle_error(data)
        else: return protocol.RpcMalformed(
            data.get('id'),
            exceptions.JsonRpcInvalidRequest(
                message=f'failed to identify entity type. data: {data}'
            )
        )


class JsonSerializer(BaseSerializer):
    def __init__(self, encoding: str = 'utf-8', version: str = '2.0'):
        super().__init__(version)
        self.encoding = encoding

    def entity_to_bytes(self, entity: protocol.RpcEntity) -> bytes:
        return json.dumps(
            entity.to_dict(), default=lambda o: o.__dict__
        ).encode(self.encoding)

    def bytes_to_entity(self, data: bytes) -> protocol.RpcEntity:
        try: deserialized: dict = json.loads(data.decode(self.encoding))
        except ValueError as e:
            return protocol.RpcMalformed(
                None, exceptions.JsonRpcParseError.from_ex(e)
            )

        if isinstance(deserialized, list):
            return protocol.RpcBatch(
                [self.handle_entity(x) for x in deserialized]
            )
        else: return self.handle_entity(deserialized)
