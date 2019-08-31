from aio_json_rpc import protocol

import abc
import typing


class RpcEntitySerializer(abc.ABC):
    @abc.abstractmethod
    def entity_to_bytes(self, entity: protocol.RpcEntity) -> bytes:
        raise NotImplementedError

    @abc.abstractmethod
    def bytes_to_entity(self, data: bytes) -> protocol.RpcEntity:
        raise NotImplementedError


class RpcEntityStream(abc.ABC):
    @abc.abstractmethod
    def __init__(self, formatter: RpcEntitySerializer):
        self.formatter = formatter

    @abc.abstractmethod
    async def fetch_entity(self) -> typing.Optional[protocol.RpcEntity]:
        """
        returns an instance of a concrete jsonrpc entity subclasses
        when this returns None, or raises an exception,
        the stream is assumed to be closed
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def dispatch_entity(self, entity: protocol.RpcEntity):
        """
        uses its internal formatter to dispatch a jsonrpc entity
        to the remote party
        """
        raise NotImplementedError

    @abc.abstractmethod
    def close(self):
        """forcefully close the stream from the endpoint"""
        raise NotImplementedError
