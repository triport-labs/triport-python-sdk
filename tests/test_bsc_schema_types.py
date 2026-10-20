from __future__ import annotations

from typing import get_args

from triport.generated.rpc.bsc_wire import BscParams, BscResults


def test_bsc_params_and_results_are_schema_derived() -> None:
    call_params = BscParams.__annotations__["eth_call"]
    logs_result = BscResults.__annotations__["eth_getLogs"]
    syncing_result = BscResults.__annotations__["eth_syncing"]

    assert call_params is not object
    assert logs_result is not object
    assert syncing_result is not object
    assert get_args(call_params)
    assert get_args(logs_result)
    assert get_args(syncing_result)
