"""
Provider health state tracking and probe logic (Issue #26 — Self-Healing)

Tracks per-provider health status in memory. Probes are run as a background
asyncio task from main.py. State is intentionally non-persistent — it resets
on Hub restart, which is fine since health is re-established via probes.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import structlog

logger = structlog.get_logger()


class ProviderHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"   # Consecutive failures, retrying
    ERROR = "error"         # Sustained failure, fallback active


@dataclass
class HealthState:
    status: ProviderHealth = ProviderHealth.HEALTHY
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    degraded_since: Optional[float] = None          # epoch seconds
    last_failure_reason: Optional[str] = None
    last_probe_at: Optional[float] = None
    last_success_at: Optional[float] = field(default_factory=time.time)


class ProviderHealthTracker:
    """
    Thread-safe (asyncio-safe) in-memory tracker for provider health states.

    Lifecycle:
    - record_success(provider): resets failure counters; marks healthy after threshold
    - record_failure(provider, reason): increments failure counter; degrades on 1st fail
    - probe_and_recover(provider, probe_fn): runs a probe and updates state
    """

    def __init__(self, success_threshold: int = 3):
        self._states: dict[str, HealthState] = {}
        self._success_threshold = success_threshold
        self._lock = asyncio.Lock()

    def _state(self, provider: str) -> HealthState:
        if provider not in self._states:
            self._states[provider] = HealthState()
        return self._states[provider]

    async def record_success(self, provider: str) -> bool:
        """
        Record a successful request. Returns True if provider just recovered
        (transitioned from degraded/error → healthy).
        """
        async with self._lock:
            s = self._state(provider)
            s.consecutive_failures = 0
            s.consecutive_successes += 1
            s.last_success_at = time.time()
            recovered = False
            if s.status != ProviderHealth.HEALTHY and s.consecutive_successes >= self._success_threshold:
                logger.info("provider_recovered", provider=provider,
                            was=s.status.value, consecutive_successes=s.consecutive_successes)
                s.status = ProviderHealth.HEALTHY
                s.degraded_since = None
                s.last_failure_reason = None
                recovered = True
            return recovered

    async def record_failure(self, provider: str, reason: str = "") -> ProviderHealth:
        """
        Record a failed request. Returns the new health status.
        """
        async with self._lock:
            s = self._state(provider)
            s.consecutive_failures += 1
            s.consecutive_successes = 0
            s.last_failure_reason = reason
            if s.status == ProviderHealth.HEALTHY:
                s.status = ProviderHealth.DEGRADED
                s.degraded_since = time.time()
                logger.warning("provider_degraded", provider=provider,
                               reason=reason, consecutive_failures=s.consecutive_failures)
            elif s.consecutive_failures >= 5 and s.status == ProviderHealth.DEGRADED:
                s.status = ProviderHealth.ERROR
                logger.error("provider_error", provider=provider,
                             reason=reason, consecutive_failures=s.consecutive_failures)
            return s.status

    def get_status(self, provider: str) -> ProviderHealth:
        return self._state(provider).status

    def get_state(self, provider: str) -> HealthState:
        return self._state(provider)

    def is_healthy(self, provider: str) -> bool:
        return self.get_status(provider) == ProviderHealth.HEALTHY

    def degraded_providers(self) -> list[str]:
        return [
            p for p, s in self._states.items()
            if s.status in (ProviderHealth.DEGRADED, ProviderHealth.ERROR)
        ]

    def snapshot(self) -> dict:
        """Return a JSON-serialisable snapshot of all health states."""
        out = {}
        for p, s in self._states.items():
            out[p] = {
                "status": s.status.value,
                "consecutive_failures": s.consecutive_failures,
                "consecutive_successes": s.consecutive_successes,
                "degraded_since": datetime.fromtimestamp(s.degraded_since, tz=timezone.utc).isoformat()
                    if s.degraded_since else None,
                "last_failure_reason": s.last_failure_reason,
                "last_success_at": datetime.fromtimestamp(s.last_success_at, tz=timezone.utc).isoformat()
                    if s.last_success_at else None,
            }
        return out

    async def probe_and_recover(self, provider: str, probe_fn) -> bool:
        """
        Run a probe function (async callable, raises on failure).
        Returns True if the probe succeeded.
        """
        s = self._state(provider)
        s.last_probe_at = time.time()
        try:
            await probe_fn()
            recovered = await self.record_success(provider)
            logger.info("health_probe_success", provider=provider, recovered=recovered)
            return True
        except Exception as e:
            await self.record_failure(provider, str(e))
            logger.warning("health_probe_failed", provider=provider, error=str(e))
            return False


# Singleton — shared across the process
tracker = ProviderHealthTracker()
