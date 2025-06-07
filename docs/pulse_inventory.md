# Pulse Inventory - Airdrop Automation Project

This document provides an inventory of all modules and key components within the airdrop automation project.

## Core Modules
*   `airdrops.core`: Shared utilities and base classes. (Details TBD)
*   `airdrops.scheduler`: Task scheduling and execution bot. (Details TBD)

## Protocol Modules
*   `airdrops.protocols.hyperliquid`: Module for interacting with the Hyperliquid protocol. Supports `stake_rotate`, `vault_cycle`, `spot_swap`, `evm_roundtrip`, `perform_random_onchain`. (See `airdrops/docs/protocols/hyperliquid.md`)
*   `airdrops.protocols.layerzero`: Module for LayerZero/Stargate cross-chain bridging. Supports `bridge`, `perform_random_bridge`. (See `airdrops/docs/protocols/layerzero.md`)
*   `airdrops.protocols.zksync`: Module for zkSync Era Layer 2 interactions. Supports `bridge_eth` for ETH bridging between L1 and L2, `swap_tokens` for DEX token swapping via SyncSwap, `lend_borrow` for lending protocol interactions via EraLend, and `perform_random_activity` for orchestrated random activity execution. (See `airdrops/docs/protocols/zksync.md`)
*   `airdrops.protocols.scroll`: Module for Scroll L2 interactions. Supports `bridge_assets` for ETH and ERC20 bridging between L1 and L2, `swap_tokens` for DEX token swapping via SyncSwap, `provide_liquidity_scroll` for adding/removing liquidity on SyncSwap, `lend_borrow_layerbank_scroll` for lending/borrowing on LayerBank V2 protocol, and `perform_random_activity_scroll` for orchestrated random activity execution across all Scroll protocols. (See `airdrops/docs/protocols/scroll.md`)
*   `airdrops.protocols.eigenlayer`: Module for EigenLayer restaking protocol interactions. Supports `restake_lst` for LST restaking (stETH, rETH), `restake_eth` for native ETH restaking via EigenPod, `withdraw` for multi-step withdrawal process with escrow period, `query_status` for comprehensive status queries, and `perform_random_activity` for automated restaking activity generation. (See `airdrops/docs/protocols/eigenlayer.md`)