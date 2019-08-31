from aio_json_rpc.serializers import JsonSerializer
from aio_json_rpc import protocol as pro

import json
import pytest


@pytest.fixture
def utf8() -> JsonSerializer: return JsonSerializer('utf-8')


def test_request_to_bytes(utf8: JsonSerializer):
    r = pro.RpcRequest(0, 'kek', None)
    data = {'jsonrpc': "2.0", 'method': 'kek', 'id': 0}
    serialized = json.loads(
        utf8.entity_to_bytes(r).decode('utf-8')
    )
    assert serialized == data


def test_bytes_to_request(utf8: JsonSerializer):
    r = pro.RpcRequest(0, 'kek', None)
    expectation = r.to_dict()
    reality = utf8.bytes_to_entity(utf8.entity_to_bytes(r)).to_dict()

    assert expectation == reality


def test_bytes_to_notification(utf8: JsonSerializer):
    r = pro.RpcNotification('kek', None)
    expectation = r.to_dict()
    reality = utf8.bytes_to_entity(utf8.entity_to_bytes(r)).to_dict()

    assert expectation == reality


def test_bytes_to_result(utf8: JsonSerializer):
    r = pro.RpcResult(0, 'yeet')
    expectation = r.to_dict()
    reality = utf8.bytes_to_entity(utf8.entity_to_bytes(r)).to_dict()

    assert expectation == reality


def test_bytes_to_error_nodata(utf8: JsonSerializer):
    r = pro.RpcError(
        0, pro.RpcErrorDetails(
            123, 'yeet', None
        )
    )
    expectation = r.to_dict()
    reality = utf8.bytes_to_entity(utf8.entity_to_bytes(r)).to_dict()

    assert expectation == reality


def test_bytes_to_error_data(utf8: JsonSerializer):
    r = pro.RpcError(
        0, pro.RpcErrorDetails(
            123, 'yeet', 'additional errorz'
        )
    )
    expectation = r.to_dict()
    reality = utf8.bytes_to_entity(utf8.entity_to_bytes(r)).to_dict()

    assert expectation == reality


def test_deserialize_doesnt_raise(utf8: JsonSerializer):
    malformed = utf8.bytes_to_entity(b'{"jsonrpc": "2.0", "kek": "top"}')
    assert isinstance(malformed, pro.RpcMalformed)
    assert malformed.id is None


def test_deserialize_doesnt_raise_with_id(utf8: JsonSerializer):
    malformed = utf8.bytes_to_entity(b'{"jsonrpc": "2.0", "id": "yeet"}')
    assert isinstance(malformed, pro.RpcMalformed)
    assert malformed.id == 'yeet'


def test_parser_error_doesnt_raise(utf8: JsonSerializer):
    malformed = utf8.bytes_to_entity(b'{yeet}')
    assert isinstance(malformed, pro.RpcMalformed)
    assert malformed.id is None


def test_batch_with_malformed_to_entity(utf8: JsonSerializer):
    r = [
        {"jsonrpc": "2.0", "method": "sum", "params": [1, 2, 4], "id": "1"},
        {"jsonrpc": "2.0", "method": "notify_hello", "params": [7]},
        {"jsonrpc": "2.0", "method": "a", "params": [42, 23], "id": "2"},
        {"foo": "boo"},
        {"jsonrpc": "2.0", "method": "b", "params": {"x": "y"}, "id": "5"},
        {"jsonrpc": "2.0", "method": "get_data", "id": "9"}
    ]
    reality = utf8.bytes_to_entity(json.dumps(r).encode())
    expectation = pro.RpcBatch(entities=[
        pro.RpcRequest(id='1', method='sum', params=[1, 2, 4], jsonrpc='2.0'),
        pro.RpcNotification(method='notify_hello', params=[7], jsonrpc='2.0'),
        pro.RpcRequest(id='2', method='a', params=[42, 23], jsonrpc='2.0'),
        pro.RpcRequest(id='5', method='b', params={'x': 'y'}, jsonrpc='2.0'),
        pro.RpcRequest(id='9', method='get_data', params=None, jsonrpc='2.0')]
    )

    assert isinstance(reality, pro.RpcBatch)
    #  test if all entities are present except the malformed one
    #  because exceptions are sadly not equatable
    matches = len([x for x in expectation.entities if x in reality.entities])
    assert matches == len(expectation.entities)
    x = [x for x in reality.entities if isinstance(x, pro.RpcMalformed)]
    assert len(x) == 1
    assert not x[0].id
