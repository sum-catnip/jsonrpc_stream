from jsonrpc_stream import protocol as pro
import pytest


def test_creating_entity_raises():
    with pytest.raises(NotImplementedError):
        pro.RpcEntity()


def test_creating_identity_raises():
    with pytest.raises(NotImplementedError):
        pro.RpcIDEntity()


def test_request_noparams():
    reality = pro.RpcRequest(0, 'topkek', None).to_dict()
    expectation = {
        'id': 0,
        'method': 'topkek',
        'jsonrpc': '2.0'
    }

    assert expectation == reality


def test_request_params_array():
    reality = pro.RpcRequest(0, 'topkek', [1, 'hi']).to_dict()
    expectation = {
        'id': 0,
        'method': 'topkek',
        'jsonrpc': '2.0',
        'params': [1, 'hi']
    }

    assert expectation == reality


def test_request_params_dict():
    reality = pro.RpcRequest(0, 'topkek', {'kek': True}).to_dict()
    expectation = {
        'id': 0,
        'method': 'topkek',
        'jsonrpc': '2.0',
        'params': {'kek': True}
    }

    assert expectation == reality


def test_notification_noparams():
    reality = pro.RpcNotification('topkek', None).to_dict()
    expectation = {
        'method': 'topkek',
        'jsonrpc': '2.0',
    }

    assert expectation == reality


def test_notification_params():
    reality = pro.RpcNotification('topkek', {'ya': 'yeet'}).to_dict()
    expectation = {
        'method': 'topkek',
        'jsonrpc': '2.0',
        'params': {'ya': 'yeet'}
    }

    assert expectation == reality


def test_result():
    reality = pro.RpcResult(0, {'ya': 'yeet'}).to_dict()
    expectation = {
        'id': 0,
        'jsonrpc': '2.0',
        'result': {'ya': 'yeet'}
    }

    assert expectation == reality


def test_error_nodata():
    reality = pro.RpcError(0, pro.RpcErrorDetails(
        1234, 'hello there', None
    )).to_dict()

    expectation = {
        'id': 0,
        'jsonrpc': '2.0',
        'error': {
            'code': 1234,
            'message': 'hello there'
        }
    }

    assert expectation == reality


def test_error_data():
    reality = pro.RpcError(0, pro.RpcErrorDetails(
        1234, 'hello there', {'additional': 'datatz'}
    )).to_dict()

    expectation = {
        'id': 0,
        'jsonrpc': '2.0',
        'error': {
            'code': 1234,
            'message': 'hello there',
            'data': {'additional': 'datatz'}
        }
    }

    assert expectation == reality


def test_batch_request():
    expectation = [
        {'method': 'topkek1', 'jsonrpc': '2.0'},
        {'method': 'topkek2', 'jsonrpc': '2.0'},
        {'method': 'topkek3', 'jsonrpc': '2.0'},
    ]
    reality = pro.RpcBatch([
        pro.RpcNotification('topkek1', None),
        pro.RpcNotification('topkek2', None),
        pro.RpcNotification('topkek2', None),
    ])

    # order invariant equality check
    matches = len([x for x in reality.to_dict() if x in expectation])
    assert matches == len(expectation)
