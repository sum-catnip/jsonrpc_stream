from aio_json_rpc import contracts
from aio_json_rpc import protocol

import asyncio
import typing
import logging


logger = logging.getLogger(__name__)


class ContentLengthEntityStream(contracts.RpcEntityStream):
    def __init__(
        self,
        formatter: contracts.RpcEntitySerializer,
        source: asyncio.StreamReader,
        sink:   asyncio.StreamWriter,
        encoding: str = 'utf-8'
    ):
        super().__init__(formatter)
        self.source = source
        self.sink   = sink
        self.encoding = encoding

    async def fetch_entity(self) -> typing.Optional[protocol.RpcEntity]:
        try:
            headers = {}

            async def read_header():
                temp = await self.source.readuntil(b'\r\n')
                temp = temp.decode(self.encoding).strip('\r\n')
                if not temp: return False

                logger.debug(f'received header: {temp}')
                temp = temp.split(':')
                try: headers[temp[0].strip()] = temp[1].strip()
                except IndexError:
                    logger.warning(f'skipping malformed header: {temp}.')
                return True

            while await read_header(): pass
            logger.debug(f'headers read, reading body now')
            entity = self.formatter.bytes_to_entity(
                await self.source.readexactly(int(headers['Content-Length']))
            )

            logger.debug(f'fetched entity: {entity}')
            return entity
        except KeyError:
            logger.exception('Content-Length header missing')
        except ValueError:
            logger.exception('malformed Content-Length header')
        except asyncio.streams.IncompleteReadError: pass
        logger.info(
            'source exhausted or unrecoverable error occured. ' +
            'exiting stream'
        )

        self.sink.close()
        return None

    async def dispatch_entity(self, entity: protocol.RpcEntity):
        logger.debug(f'dispatching entity: {entity}')
        body = self.formatter.entity_to_bytes(entity)
        self.sink.write(  # type: ignore
            f'Content-Length: {len(body)}\r\n\r\n'.encode() + body
        )
        await self.sink.drain()

    def close(self):
        self.source.feed_eof()
        self.sink.write_eof()
        self.sink.close()
