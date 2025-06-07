try:
    from airdrops.protocols.eigenlayer.eigenlayer import (
        restake_lst,
        _check_eigenlayer_deposit_cap,
        _get_eigenlayer_lst_strategy_details,
        _load_abi
    )
    from airdrops.protocols.eigenlayer.exceptions import (
        DepositCapReachedError,
        EigenLayerRestakeError,
        UnsupportedLSTError,
    )
    print("Manual import test PASSED for eigenlayer module.")
except ImportError as e:
    print(f"Manual import test FAILED for eigenlayer module: {e}")