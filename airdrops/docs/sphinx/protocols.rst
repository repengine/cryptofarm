Protocols API
=============

The protocols module provides interfaces for interacting with various blockchain protocols and DeFi platforms. Each protocol implementation handles the specific requirements and APIs for that platform.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
--------

The protocols module enables automated interactions with multiple DeFi protocols:

* **Scroll** - Layer 2 scaling solution with full DeFi ecosystem
* **zkSync Era** - Layer 2 with native account abstraction
* **LayerZero** - Omnichain interoperability protocol
* **Hyperliquid** - High-performance perpetuals DEX
* **EigenLayer** - Ethereum restaking protocol

Each protocol provides operations like bridging, swapping, lending, and liquidity provision.

Main Protocols Module
---------------------

.. automodule:: airdrops.protocols
   :members:
   :undoc-members:
   :show-inheritance:

Hyperliquid Protocol
--------------------

.. automodule:: airdrops.protocols.hyperliquid
   :members:
   :undoc-members:
   :show-inheritance:

LayerZero Protocol
------------------

.. automodule:: airdrops.protocols.layerzero
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: airdrops.protocols.layerzero.layerzero
   :members:
   :undoc-members:
   :show-inheritance:

Scroll Protocol
---------------

.. automodule:: airdrops.protocols.scroll
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: airdrops.protocols.scroll.scroll
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: airdrops.protocols.scroll.exceptions
   :members:
   :undoc-members:
   :show-inheritance:

zkSync Protocol
---------------

.. automodule:: airdrops.protocols.zksync
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: airdrops.protocols.zksync.zksync
   :members:
   :undoc-members:
   :show-inheritance:

EigenLayer Protocol
-------------------

.. automodule:: airdrops.protocols.eigenlayer
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: airdrops.protocols.eigenlayer.eigenlayer
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: airdrops.protocols.eigenlayer.eigenlayer_config
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: airdrops.protocols.eigenlayer.exceptions
   :members:
   :undoc-members:
   :show-inheritance: