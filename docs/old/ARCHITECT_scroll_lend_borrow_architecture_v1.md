## Plan v1: Scroll Lend/Borrow Architecture (LayerBank V2)

### Objective
Design the architecture for the `lend_borrow_layerbank_scroll` function to enable lending, borrowing, repaying, and withdrawing ETH and USDC on LayerBank V2 within the Scroll protocol module.

### Task Blocks
| ID   | Description                                                                 | Owner Mode | Deliverable                                                                 | Acceptance Test                                                                                                |
|------|-----------------------------------------------------------------------------|------------|-----------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| TB-1 | Define Function Signature & Parameters                                      | Architect  | Section in Arch. Doc                                                        | Signature clearly defined with all inputs (`web3_scroll`, `private_key`, `action`, `token_symbol`, `amount`).    |
| TB-2 | Design Core Logic: Lend (Supply)                                            | Architect  | Section in Arch. Doc                                                        | ETH & USDC lend logic detailed, including `mint()` and `enterMarkets()` calls.                                 |
| TB-3 | Design Core Logic: Withdraw (Redeem)                                        | Architect  | Section in Arch. Doc                                                        | ETH & USDC withdraw logic detailed, including `redeemUnderlying()` calls.                                      |
| TB-4 | Design Core Logic: Borrow                                                   | Architect  | Section in Arch. Doc                                                        | Borrow logic detailed, including `getAccountLiquidity()` pre-check and `borrow()` calls for ETH & USDC.        |
| TB-5 | Design Core Logic: Repay                                                    | Architect  | Section in Arch. Doc                                                        | Repay logic detailed, including `repayBorrow()` / `repayBorrowBehalf()` for ETH & USDC.                        |
| TB-6 | Detail Contract Interactions (Comptroller & lbTokens)                       | Architect  | Section in Arch. Doc                                                        | Specific contract functions identified for Comptroller and lbTokens.                                           |
| TB-7 | Plan Configuration Management (Addresses & ABIs)                            | Architect  | Section in Arch. Doc                                                        | Plan for storing addresses in `config.py` and ABIs in `abi/` directory.                                        |
| TB-8 | Outline Error Handling Strategy                                             | Architect  | Section in Arch. Doc                                                        | Custom exceptions from `ScrollLendingError`, `InsufficientCollateralError` etc. identified.                  |
| TB-9 | Conceptualize Helper Functions                                              | Architect  | Section in Arch. Doc                                                        | Helper functions like `_get_layerbank_lbtoken_address_scroll`, `_check_and_enter_layerbank_market_scroll`, etc. |

### Architectural Details

#### 1. Function Signature

```python
def lend_borrow_layerbank_scroll(
    web3_scroll: Web3,
    private_key: str,
    action: str,  # "lend", "borrow", "repay", "withdraw"
    token_symbol: str,  # "ETH", "USDC"
    amount: int  # Amount in Wei for ETH, smallest unit for USDC
) -> str: # Returns transaction hash
    """
    Handles lending, borrowing, repaying, and withdrawing assets on LayerBank V2 on Scroll.
    """
    # Implementation to be detailed by Code mode
    pass
```

#### 2. Core Logic - Lend (Supply)

*   **Common:**
    *   Resolve `lbToken` address based on `token_symbol` (e.g., using `_get_layerbank_lbtoken_address_scroll`).
*   **ETH Lend:**
    1.  Interact with the `mint()` function of the lbETH contract ([`0x7E08A050000201d938279b3A0e293A49A729505E`](https://scrollscan.com/address/0x7E08A050000201d938279b3A0e293A49A729505E)).
    2.  Send ETH as `msg.value` along with the `mint()` call.
*   **USDC Lend:**
    1.  Approve the lbUSDC contract ([`0x145600553A1448B7502577097755A0682755E521`](https://scrollscan.com/address/0x145600553A1448B7502577097755A0682755E521)) to spend the user's USDC.
        *   Use standard ERC20 `approve(spender_address, amount)` function on the USDC token contract (e.g., [`0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4`](https://scrollscan.com/address/0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4) on Scroll).
    2.  Interact with the `mint(uint mintAmount)` function of the lbUSDC contract, passing the `amount`.
*   **Enter Market (Post-Lend):**
    1.  After a successful lend operation, check if the corresponding `lbToken` is already enabled as collateral.
    2.  Query the Comptroller contract's ([`0xADC0A5309218B415B090477504B78A035245d54A`](https://scrollscan.com/address/0xADC0A5309218B415B090477504B78A035245d54A)) `checkMembership(address account, address cToken)` function.
    3.  If not entered, call `enterMarkets(address[] calldata cTokens)` on the Comptroller contract, passing an array containing the `lbToken` address.
        *   Helper function `_check_and_enter_layerbank_market_scroll` can encapsulate this.

#### 3. Core Logic - Withdraw (Redeem)

*   **Common:**
    *   Resolve `lbToken` address based on `token_symbol`.
*   **ETH Withdraw:**
    1.  Interact with `redeemUnderlying(uint redeemAmount)` function of the lbETH contract ([`0x7E08A050000201d938279b3A0e293A49A729505E`](https://scrollscan.com/address/0x7E08A050000201d938279b3A0e293A49A729505E)).
*   **USDC Withdraw:**
    1.  Interact with `redeemUnderlying(uint redeemAmount)` function of the lbUSDC contract ([`0x145600553A1448B7502577097755A0682755E521`](https://scrollscan.com/address/0x145600553A1448B7502577097755A0682755E521)).
*   **Alternative:** `redeem(uint redeemTokens)` can be used to withdraw based on lbToken amount. `redeemUnderlying` is prioritized.

#### 4. Core Logic - Borrow

*   **Common:**
    *   Resolve `lbToken` address based on `token_symbol`.
*   **Pre-Borrow Check:**
    1.  Call `getAccountLiquidity(address account)` on the Comptroller contract ([`0xADC0A5309218B415B090477504B78A035245d54A`](https://scrollscan.com/address/0xADC0A5309218B415B090477504B78A035245d54A)).
        *   Returns `(error, liquidity, shortfall)`. Proceed if `error` is 0, `liquidity` >= USD value of borrow amount, and `shortfall` is 0.
        *   Convert borrow `amount` to USD using the Price Oracle ([`0x009C08A07a13104f04251999C44866013903a015`](https://scrollscan.com/address/0x009C08A07a13104f04251999C44866013903a015)).
        *   Helper `_get_layerbank_account_liquidity_scroll` can assist.
    2.  If insufficient, raise [`InsufficientCollateralError`](airdrops/src/airdrops/protocols/scroll/exceptions.py:1).
*   **ETH Borrow:**
    1.  Interact with `borrow(uint borrowAmount)` function of the lbETH contract ([`0x7E08A050000201d938279b3A0e293A49A729505E`](https://scrollscan.com/address/0x7E08A050000201d938279b3A0e293A49A729505E)).
*   **USDC Borrow:**
    1.  Interact with `borrow(uint borrowAmount)` function of the lbUSDC contract ([`0x145600553A1448B7502577097755A0682755E521`](https://scrollscan.com/address/0x145600553A1448B7502577097755A0682755E521)).

#### 5. Core Logic - Repay

*   **Common:**
    *   Resolve `lbToken` address based on `token_symbol`.
*   **ETH Repay:**
    1.  Interact with `repayBorrow()` function of the lbETH contract ([`0x7E08A050000201d938279b3A0e293A49A729505E`](https://scrollscan.com/address/0x7E08A050000201d938279b3A0e293A49A729505E)), sending ETH as `msg.value` (equal to `amount`).
    2.  For full repayment, `amount` can be `type(uint256).max`. `msg.value` should cover `borrowBalanceStored(address account)` plus interest.
*   **USDC Repay:**
    1.  Approve the lbUSDC contract ([`0x145600553A1448B7502577097755A0682755E521`](https://scrollscan.com/address/0x145600553A1448B7502577097755A0682755E521)) to spend USDC.
    2.  Interact with `repayBorrow(uint repayAmount)` function of the lbUSDC contract, passing `amount`.
    3.  For full repayment, `repayAmount` can be `type(uint256).max`. Approval should cover debt plus interest.

#### 6. Contract Interaction Details

*   **Comptroller ([`0xADC0A5309218B415B090477504B78A035245d54A`](https://scrollscan.com/address/0xADC0A5309218B415B090477504B78A035245d54A)):**
    *   `enterMarkets(address[] cTokens)`
    *   `getAccountLiquidity(address account)`: Returns `(uint error, uint liquidity, uint shortfall)`.
    *   `markets(address cTokenAddress)`: Returns market info.
    *   `checkMembership(address account, address cToken)`: Checks if market entered.
*   **lbToken Contracts (e.g., lbETH [`0x7E08A050000201d938279b3A0e293A49A729505E`](https://scrollscan.com/address/0x7E08A050000201d938279b3A0e293A49A729505E), lbUSDC [`0x145600553A1448B7502577097755A0682755E521`](https://scrollscan.com/address/0x145600553A1448B7502577097755A0682755E521)):**
    *   `mint()` (for ETH)
    *   `mint(uint mintAmount)` (for ERC20)
    *   `redeemUnderlying(uint redeemAmount)`
    *   `redeem(uint redeemTokens)`
    *   `borrow(uint borrowAmount)`
    *   `repayBorrow()` (for ETH)
    *   `repayBorrow(uint repayAmount)` (for ERC20)
    *   `repayBorrowBehalf(address borrower, uint repayAmount)`
    *   `borrowBalanceStored(address account)`
    *   `balanceOf(address account)`
*   **USDC Token (e.g., [`0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4`](https://scrollscan.com/address/0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4) on Scroll):**
    *   `approve(address spender, uint256 amount)`
    *   `allowance(address owner, address spender)`
*   **Price Oracle ([`0x009C08A07a13104f04251999C44866013903a015`](https://scrollscan.com/address/0x009C08A07a13104f04251999C44866013903a015)):**
    *   `getUnderlyingPrice(address cToken)`: Returns USD price of underlying.

#### 7. Configuration Management

*   **Addresses in [`airdrops/src/airdrops/shared/config.py`](airdrops/src/airdrops/shared/config.py:1):**
    *   `LAYERBANK_COMPTROLLER_ADDRESS_SCROLL`
    *   `LAYERBANK_PRICE_ORACLE_ADDRESS_SCROLL`
    *   `LAYERBANK_LBETH_ADDRESS_SCROLL`
    *   `LAYERBANK_LBUSDC_ADDRESS_SCROLL`
    *   `SCROLL_USDC_TOKEN_ADDRESS`
*   **ABIs in [`airdrops/src/airdrops/protocols/scroll/abi/`](airdrops/src/airdrops/protocols/scroll/abi/):**
    *   `LayerBankComptroller.json`
    *   `LayerBankLbToken.json` (generic for lbTokens)
    *   `ERC20.json`
    *   `LayerBankPriceOracle.json`
    *   Source ABIs from Scrollscan.

#### 8. Error Handling

Use custom exceptions from [`airdrops/src/airdrops/protocols/scroll/exceptions.py`](airdrops/src/airdrops/protocols/scroll/exceptions.py:1):
*   [`ScrollLendingError`](airdrops/src/airdrops/protocols/scroll/exceptions.py:1) (base)
*   [`InsufficientCollateralError`](airdrops/src/airdrops/protocols/scroll/exceptions.py:1)
*   [`MarketNotEnteredError`](airdrops/src/airdrops/protocols/scroll/exceptions.py:1)
*   [`RepayAmountExceedsDebtError`](airdrops/src/airdrops/protocols/scroll/exceptions.py:1)
*   [`LayerBankComptrollerRejectionError`](airdrops/src/airdrops/protocols/scroll/exceptions.py:1) (map Comptroller error codes)
*   Standard exceptions: [`ApprovalError`](airdrops/src/airdrops/protocols/scroll/exceptions.py:1), [`TransactionRevertedError`](airdrops/src/airdrops/protocols/scroll/exceptions.py:1), etc.

#### 9. Helper Functions (Conceptual)

*   `_get_layerbank_lbtoken_address_scroll(token_symbol: str) -> str:`
*   `_check_and_enter_layerbank_market_scroll(web3_scroll: Web3, private_key: str, lbtoken_address: str, user_address: str) -> None:`
*   `_get_layerbank_account_liquidity_scroll(web3_scroll: Web3, comptroller_contract, price_oracle_contract, lbtoken_address: str, user_address: str, borrow_amount_units: int = 0) -> Tuple[int, int, int, bool]:` (returns error, liquidity_usd, shortfall_usd, can_borrow_flag)
*   `_get_asset_price_layerbank_scroll(web3_scroll: Web3, price_oracle_contract, lbtoken_address: str) -> int:`
*   `_approve_contract_spend_token_scroll(web3_scroll: Web3, private_key: str, token_address: str, spender_address: str, amount: int, user_address: str) -> None:`

### Flow Diagram (Conceptual for Lend ETH)
```mermaid
graph TD
    A[Start Lend ETH] --> B{Get lbETH Address};
    B --> C[Call lbETH.mint() with msg.value];
    C --> D{Transaction Successful?};
    D -- Yes --> E[Call _check_and_enter_layerbank_market_scroll for lbETH];
    E --> F{Market Entered/Enabled?};
    F -- Yes --> G[Return Tx Hash];
    F -- No / Error --> H[Raise ScrollLendingError];
    D -- No --> H;
    C -- Error --> H;
```

### PCRM Analysis
*   **Pros:** Enables core DeFi functionality on Scroll, utilizes LayerBank V2, increases capital efficiency.
*   **Cons:** Adds module complexity, smart contract risks, requires careful debt management.
*   **Risks:** Liquidation, contract pauses/upgrades, oracle price issues, gas price volatility.
*   **Mitigations:** Robust borrow pre-checks, try-except blocks, clear logging, use checksummed addresses, reliable ABI sources, thorough testing.

### Next Step
Reply **Approve** to proceed with creating this architectural document and updating the main planning file, or suggest edits.