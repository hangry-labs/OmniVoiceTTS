from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Literal


GenerationOutcome = Literal["completed", "failed", "cancelled"]


@dataclass
class GenerationOperation:
    device: str
    request_id: str | None
    queued_at: float
    started_at: float | None = None
    finished: bool = False


class GenerationDiagnostics:
    """Thread-safe aggregate queue and generation timing counters."""

    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self._lock = threading.Lock()
        self._started_at = time.time()
        self._devices: dict[str, dict[str, float | int | str | None]] = {}

    def queued(self, device: str, request_id: str | None = None) -> GenerationOperation:
        operation = GenerationOperation(device, request_id, time.monotonic())
        with self._lock:
            stats = self._device(device)
            stats["accepted"] += 1
            stats["queued"] += 1
        return operation

    def started(self, operation: GenerationOperation) -> None:
        now = time.monotonic()
        operation.started_at = now
        queue_seconds = max(0.0, now - operation.queued_at)
        with self._lock:
            stats = self._device(operation.device)
            stats["queued"] = max(0, int(stats["queued"]) - 1)
            stats["started"] += 1
            stats["active"] += 1
            stats["queue_seconds_total"] += queue_seconds
            stats["last_queue_seconds"] = queue_seconds
            stats["max_queue_seconds"] = max(float(stats["max_queue_seconds"]), queue_seconds)
            stats["last_request_id"] = operation.request_id

    def finished(self, operation: GenerationOperation, outcome: GenerationOutcome) -> None:
        if operation.finished:
            return
        operation.finished = True
        now = time.monotonic()
        generation_seconds = max(0.0, now - (operation.started_at or operation.queued_at))
        with self._lock:
            stats = self._device(operation.device)
            if operation.started_at is None:
                stats["queued"] = max(0, int(stats["queued"]) - 1)
            else:
                stats["active"] = max(0, int(stats["active"]) - 1)
                stats["generation_seconds_total"] += generation_seconds
                stats["last_generation_seconds"] = generation_seconds
                stats["max_generation_seconds"] = max(
                    float(stats["max_generation_seconds"]), generation_seconds
                )
            stats[outcome] += 1
            stats["last_outcome"] = outcome
            stats["last_request_id"] = operation.request_id

    def snapshot(self) -> dict:
        with self._lock:
            devices = {
                device: self._snapshot_device(stats)
                for device, stats in sorted(self._devices.items())
            }
        return {
            "capacity_per_device": self.capacity,
            "started_at_unix": self._started_at,
            "devices": devices,
            "totals": self._aggregate(devices),
        }

    def reset(self) -> None:
        with self._lock:
            self._devices.clear()
            self._started_at = time.time()

    def _device(self, device: str) -> dict[str, float | int | str | None]:
        return self._devices.setdefault(
            device,
            {
                "accepted": 0,
                "started": 0,
                "queued": 0,
                "active": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0,
                "queue_seconds_total": 0.0,
                "generation_seconds_total": 0.0,
                "last_queue_seconds": None,
                "max_queue_seconds": 0.0,
                "last_generation_seconds": None,
                "max_generation_seconds": 0.0,
                "last_outcome": None,
                "last_request_id": None,
            },
        )

    @staticmethod
    def _snapshot_device(stats: dict[str, float | int | str | None]) -> dict:
        result = dict(stats)
        started = int(result["started"])
        result["average_queue_seconds"] = (
            float(result["queue_seconds_total"]) / started if started else 0.0
        )
        finished = int(result["completed"]) + int(result["failed"]) + int(result["cancelled"])
        result["average_generation_seconds"] = (
            float(result["generation_seconds_total"]) / finished if finished else 0.0
        )
        return result

    @staticmethod
    def _aggregate(devices: dict[str, dict]) -> dict:
        integer_fields = (
            "accepted",
            "started",
            "queued",
            "active",
            "completed",
            "failed",
            "cancelled",
        )
        totals = {field: sum(int(item[field]) for item in devices.values()) for field in integer_fields}
        totals["queue_seconds_total"] = sum(
            float(item["queue_seconds_total"]) for item in devices.values()
        )
        totals["generation_seconds_total"] = sum(
            float(item["generation_seconds_total"]) for item in devices.values()
        )
        totals["average_queue_seconds"] = (
            totals["queue_seconds_total"] / totals["started"] if totals["started"] else 0.0
        )
        finished = totals["completed"] + totals["failed"] + totals["cancelled"]
        totals["average_generation_seconds"] = (
            totals["generation_seconds_total"] / finished if finished else 0.0
        )
        return totals
