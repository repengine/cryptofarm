"""
Central Scheduler module for airdrops automation.

This module provides the CentralScheduler class for orchestrating airdrop-related
tasks using APScheduler with DAG-based dependency management and market awareness.
"""

from airdrops.scheduler.bot import CentralScheduler

__all__ = ["CentralScheduler"]
