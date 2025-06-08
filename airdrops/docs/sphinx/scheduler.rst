Scheduler API
=============

The scheduler module provides task orchestration and scheduling capabilities for the airdrops automation system. It manages the execution of tasks across different protocols with dependency management and error handling.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
--------

The scheduler system provides:

* Centralized task orchestration across all protocols
* Priority-based task queuing
* Dependency resolution between tasks
* Retry logic with exponential backoff
* Gas price monitoring and optimization
* Concurrent execution management

Scheduler Module
----------------

.. automodule:: airdrops.scheduler
   :members:
   :undoc-members:
   :show-inheritance:

Central Scheduler
-----------------

.. automodule:: airdrops.scheduler.bot
   :members:
   :undoc-members:
   :show-inheritance:

Key Classes
-----------

.. autoclass:: airdrops.scheduler.bot.CentralScheduler
   :members:
   :special-members: __init__

.. autoclass:: airdrops.scheduler.bot.TaskStatus
   :members:

.. autoclass:: airdrops.scheduler.bot.TaskPriority
   :members:

Usage Examples
--------------

Basic Task Scheduling
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from airdrops.scheduler.bot import CentralScheduler
   
   scheduler = CentralScheduler(config)
   
   # Schedule a task
   task_id = scheduler.schedule_task({
       "protocol": "scroll",
       "action": "swap",
       "wallet": "0x...",
       "params": {"token_in": "ETH", "token_out": "USDC", "amount": "0.1"}
   })

Task Dependencies
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Create dependent tasks
   bridge_task = scheduler.schedule_task({
       "protocol": "zksync",
       "action": "bridge",
       "params": {"amount": "1.0", "to_l2": True}
   })
   
   swap_task = scheduler.schedule_task({
       "protocol": "zksync", 
       "action": "swap",
       "dependencies": [bridge_task]
   })