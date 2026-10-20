import triport


def test_per_network_exports() -> None:
    expected = {
        "sol": ("SOL_METHOD_TIERS", "SolMethodName"),
        "eth": ("ETH_METHOD_TIERS", "EthMethodName"),
        "polygon": ("POLYGON_METHOD_TIERS", "PolygonMethodName"),
        "bsc": ("BSC_METHOD_TIERS", "BscMethodName"),
        "robinhood": ("ROBINHOOD_METHOD_TIERS", "RobinhoodMethodName"),
        "tron": ("TRON_METHOD_TIERS", "TronMethodName"),
        "stellar": ("STELLAR_METHOD_TIERS", "StellarMethodName"),
        "ton": ("TON_METHOD_TIERS", "TonMethodName"),
    }
    for network, names in expected.items():
        for name in names:
            assert hasattr(triport, name), f"missing {name} for {network}"
            assert name in triport.__all__


def test_bsc_schema_exports_remain_public() -> None:
    assert triport.BscParams is not None
    assert triport.BscResults is not None


def test_robinhood_schema_exports_are_public() -> None:
    assert triport.RobinhoodParams is not None
    assert triport.RobinhoodResults is not None
