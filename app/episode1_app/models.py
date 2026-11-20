"""Shared state objects for the UI and backends."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


STATUS_READY = "READY"
STATUS_MOVING = "MOVING"
STATUS_HOLD = "HOLD"
STATUS_PROTECTED = "PROTECTED"
STATUS_OFFLINE = "OFFLINE"


@dataclass
class JointState:
    index: int
    name: str
    can_id: int
    angle: float = 0.0
    target: float = 0.0
    enabled: bool = False
    status: str = STATUS_HOLD
    min_deg: float = -180.0
    max_deg: float = 180.0
    gear_ratio: float = 25.0
    current_a: float = 0.0
    temp_c: float = 0.0


@dataclass
class Snapshot:
    connected: bool = False
    port: str = "—"
    protocol: str = "SLCAN / 500 kbit/s"
    voltage: float = 0.0
    current_a: float = 0.0
    temp_c: float = 0.0
    latency_ms: float = 0.0
    loop_hz: float = 20.0
    joints: List[JointState] = field(default_factory=list)
    timestamp: str = ""
