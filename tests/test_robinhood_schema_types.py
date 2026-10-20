from __future__ import annotations

from typing import get_args

from triport.generated.rpc.robinhood import ROBINHOOD_METHOD_TIERS
from triport.generated.rpc.robinhood_wire import RobinhoodParams, RobinhoodResults


def test_robinhood_params_and_results_are_schema_derived() -> None:
    call_params = RobinhoodParams.__annotations__["eth_call"]
    conditional_params = RobinhoodParams.__annotations__["eth_sendRawTransactionConditional"]
    logs_result = RobinhoodResults.__annotations__["eth_getLogs"]

    assert call_params is not object
    assert conditional_params is not object
    assert logs_result is not object
    assert get_args(call_params)
    assert get_args(conditional_params)
    assert get_args(logs_result)
    for method in ("eth_getLogs", "eth_getBlockReceipts", "eth_getProof"):
        assert ROBINHOOD_METHOD_TIERS[method].category == "robinhood_read_rpc_heavy"
