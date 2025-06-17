# Plan v1: Automated Cross-Chain Capital Management

## 1. Objective
To design a robust and extensible architecture that automates the management and rebalancing of capital across multiple heterogeneous blockchain networks, improving capital efficiency and reducing manual intervention.

## 2. Architecture Overview

The proposed architecture introduces a new central service, the `CrossChainManager`, which acts as the orchestrator for all rebalancing operations. It consumes rebalancing suggestions from the existing `CapitalAllocator`, enriches them with cross-chain execution details, and uses a system of generic `BridgeAdapters` to execute the transfers.

### Flow Diagram
```mermaid
graph TD
    subgraph "Input: High-Level Goal"
        A[CapitalAllocator Engine] -->|Generates RebalanceOrder| B(Rebalancing Goal: "Decrease Scroll by $1k")
    end

    subgraph "Orchestration: CrossChainManager"
        B --> C{CrossChainManager};
        C -->|1. Analyze Goal & Liquidity| D{Liquidity Thresholds};
        D -->|Deficit on Solana| C;
        C -->|2. Formulate Plan| E[Create RebalancingJob: Move $1k from Scroll to Solana];
        C -->|3. Select Bridge & Estimate Cost| F[BridgeAdapter Interface];
        F -->|Best route: Stargate| C;
        C -->|4. Execute Bridge Transfer| G[StargateAdapter];
        G -->|5. Track Transaction| H(RebalancingJob Status: PENDING -> IN_PROGRESS);
        H -->|Funds arrive on Solana| I(RebalancingJob Status: COMPLETED);
    end

    subgraph "Execution Layer"
        F --> G;
        F --> LayerZeroAdapter;
        F --> OfficialBridgeAdapter;
    end

    subgraph "Data Models"
        J[Chain Model] --> C;
        K[Wallet Model] --> C;
        L[RebalancingJob Model] --> H;
    end
```

## 3. Core Components

### 3.1. `CrossChainManager`
This will be a new, central class responsible for the entire cross-chain rebalancing lifecycle.

**Responsibilities:**
- **Consume Rebalancing Goals:** Listens for `RebalanceOrder` outputs from the `CapitalAllocator`.
- **Maintain Liquidity State:** Tracks current capital on each chain for each wallet.
- **Trigger Rebalancing:** Determines when to act based on predefined liquidity thresholds (e.g., "Solana wallet balance is below $500").
- **Cost-Benefit Analysis:** Uses `BridgeAdapter` to estimate transfer costs (gas, fees, slippage) and decides if a rebalancing operation is profitable.
- **Bridge Selection:** Chooses the optimal bridge based on cost, speed, and security for a given asset and chain pair.
- **Execution & Tracking:** Initiates the bridge transfer and monitors the `RebalancingJob` until completion or failure.

**High-Level Definition (`cross_chain_manager.py`):**
```python
class CrossChainManager:
    def __init__(self, wallet_provider, bridge_registry, job_tracker):
        # ...
        pass

    def evaluate_and_rebalance(self):
        # 1. Get current liquidity across all chains/wallets
        # 2. Check against liquidity thresholds
        # 3. If rebalance needed, formulate a RebalancingJob
        # 4. Estimate costs via BridgeAdapter
        # 5. If profitable, execute job
        pass

    def execute_rebalancing_job(self, job: RebalancingJob):
        # ...
        pass
```

### 3.2. `BridgeAdapter` Interface
A generic interface to abstract the specifics of different bridging protocols.

**High-Level Definition (`bridge_adapter.py`):**
```python
from abc import ABC, abstractmethod

class BridgeCostEstimate:
    source_gas_fee: Decimal
    bridge_fee: Decimal
    slippage_pct: Decimal
    total_cost_usd: Decimal

class BridgeAdapter(ABC):
    @abstractmethod
    def get_name(self) -> str:
        """Returns the name of the bridge (e.g., 'Stargate', 'LayerZero')."""
        pass

    @abstractmethod
    def estimate_cost(self, source_chain: Chain, dest_chain: Chain, token: str, amount: Decimal) -> BridgeCostEstimate:
        """Estimates the total cost of a bridge transfer."""
        pass

    @abstractmethod
    def bridge(self, job: RebalancingJob) -> str:
        """
        Initiates a bridge transfer.
        Returns the source chain transaction hash.
        """
        pass
```
The existing `LayerZeroProtocol` will be refactored into a `LayerZeroAdapter` that implements this interface.

## 4. Data Models
New data models are required to support this system. These should be defined in `airdrops/shared/models.py`.

### 4.1. `Chain` Model
Stores chain-specific configuration.
```python
from pydantic import BaseModel, HttpUrl

class Chain(BaseModel):
    name: str               # e.g., "Ethereum"
    chain_id: int           # e.g., 1
    lz_chain_id: int        # LayerZero-specific chain ID
    rpc_url: HttpUrl
    explorer_url: HttpUrl
    native_token: str       # e.g., "ETH"
```

### 4.2. `Wallet` Model
Represents a single logical wallet with addresses across multiple chains.
```python
class Wallet(BaseModel):
    name: str
    private_key: str  # Should be stored securely, e.g., in a vault
    addresses: Dict[int, str]  # Mapping of chain_id to address
```

### 4.3. `RebalancingJob` Model
Tracks the state of a single cross-chain transfer.
```python
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class RebalancingJob(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.PENDING
    source_chain_id: int
    dest_chain_id: int
    source_wallet_address: str
    dest_wallet_address: str
    token: str
    amount: Decimal
    source_tx_hash: Optional[str] = None
    dest_tx_hash: Optional[str] = None
    created_at: datetime
    updated_at: datetime
```

## 5. Task Blocks

| ID | Description | Owner Mode | Deliverable | Acceptance Test |
|----|-------------|------------|-------------|-----------------|
| TB-1 | **Define Core Data Models** | Code | Implement `Chain`, `Wallet`, and `RebalancingJob` models in `airdrops/shared/models.py`. | Models are defined with Pydantic validation and pass unit tests. |
| TB-2 | **Create `BridgeAdapter` Interface** | Code | Create the abstract base class `BridgeAdapter` in `airdrops/protocols/bridge_adapter.py`. | The interface is defined with abstract methods for `estimate_cost` and `bridge`. |
| TB-3 | **Refactor `LayerZeroProtocol` to `LayerZeroAdapter`** | Code | Refactor the existing `layerzero.py` to implement the `BridgeAdapter` interface. | `LayerZeroAdapter` can successfully estimate costs and execute a bridge transaction via the common interface. |
| TB-4 | **Implement `CrossChainManager`** | Code | Create the `CrossChainManager` class with logic for evaluating and executing rebalancing jobs. | Given a liquidity deficit, the manager correctly creates and executes a `RebalancingJob` using a mock adapter. |
| TB-5 | **Extend `CapitalAllocator`** | Code | Modify `rebalance_portfolio` to be chain-aware and output cross-chain rebalancing suggestions. | The allocator can generate a plan to move funds from a high-liquidity chain to a low-liquidity one. |
| TB-6 | **Integrate Components** | Code | Wire the `CapitalAllocator`, `CrossChainManager`, and `BridgeAdapter`s together. | An E2E test successfully triggers a rebalance, which is executed by the `CrossChainManager` via the `LayerZeroAdapter`. |

## 6. PCRM Analysis

*   **Pros:**
    *   **High Automation:** Drastically reduces manual effort and reaction time for capital management.
    *   **Capital Efficiency:** Ensures capital is deployed where it's most needed, maximizing opportunities.
    *   **Extensible:** The adapter pattern makes it easy to add new bridges (e.g., official bridges, other third-party protocols) without changing the core logic.
*   **Cons:**
    *   **Increased Complexity:** Introduces several new components and state management requirements.
    *   **Smart Contract Risk:** Each new bridge adapter adds a dependency on external, unaudited smart contracts.
*   **Risks:**
    *   **Stuck Funds:** A failed bridge transaction could leave funds in a difficult-to-recover state.
    *   **Cost Inaccuracy:** Poor cost estimation could lead to unprofitable rebalancing operations.
    *   **Race Conditions:** Multiple rebalancing jobs running in parallel could interfere with each other if not managed carefully.
*   **Mitigations:**
    *   **Robust Job Tracking:** The `RebalancingJob` model is critical. Implement a state machine with timeouts and alerting for failed/stuck jobs.
    *   **Conservative Cost Estimation:** Add a buffer to all cost estimates to account for volatility.
    *   **Job Locking:** Implement a locking mechanism (e.g., by wallet or by chain) to ensure only one rebalancing job is active for a given scope at a time.

## 7. Next Step
Reply **Approve** to proceed with the implementation of this architectural plan, or suggest edits.