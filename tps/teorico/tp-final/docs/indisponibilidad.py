#!/usr/bin/env python3
"""Calcula indisponibilidad de las corridas de convergencia desde sus logs."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median


PING = re.compile(r"^\[(?P<time>\d+\.\d+)] (?:(?P<ok>64 bytes).*icmp_seq=(?P<seq>\d+).*|From .*)$")
EVENT = re.compile(r"^(?P<time>\S+) enlace-R2-R4-suspendido$")
SCHEMES = ("estatico", "rip", "ospf")
RUNS = range(1, 6)
GAP_SECONDS = 1.0
RECOVERY_REPLIES = 5


@dataclass
class Reply:
    timestamp: float
    sequence: int


def event_timestamp(path: Path) -> float:
    for line in path.read_text(encoding="utf-8").splitlines():
        match = EVENT.match(line)
        if match:
            return datetime.fromisoformat(match["time"].replace("Z", "+00:00")).replace(
                tzinfo=timezone.utc
            ).timestamp()
    raise ValueError(f"No se encontro el evento de suspension en {path}")


def ping_events(path: Path) -> list[tuple[float, Reply | None]]:
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = PING.match(line)
        if not match:
            continue
        timestamp = float(match["time"])
        if match["ok"]:
            events.append((timestamp, Reply(timestamp, int(match["seq"]))))
        else:
            events.append((timestamp, None))
    return events


def calculate(events: list[tuple[float, Reply | None]], suspended_at: float) -> tuple[float, float, float]:
    """Return outage start, sustained recovery and their difference in seconds."""
    first_loss = next(((index, timestamp) for index, (timestamp, reply) in enumerate(events)
                       if timestamp >= suspended_at and reply is None), None)

    inferred_gap = False
    if first_loss is None:
        for index in range(1, len(events)):
            previous_time, previous_reply = events[index - 1]
            timestamp, reply = events[index]
            if previous_reply and reply and previous_time < suspended_at <= timestamp and timestamp - previous_time >= GAP_SECONDS:
                first_loss = (index, timestamp)
                inferred_gap = True
                break

    if first_loss is None:
        raise ValueError("No se encontro evidencia de perdida posterior a la suspension")

    first_loss_index, _ = first_loss
    before_loss = next((reply for _, reply in reversed(events[:first_loss_index]) if reply), None)
    if before_loss is None:
        raise ValueError("No hay respuesta valida antes de la perdida")

    if inferred_gap:
        last_loss_index = first_loss_index - 1
    else:
        last_loss_index = max(index for index, (_, reply) in enumerate(events[first_loss_index:], first_loss_index) if reply is None)
    for index in range(last_loss_index + 1, len(events) - RECOVERY_REPLIES + 1):
        window = events[index:index + RECOVERY_REPLIES]
        replies = [reply for _, reply in window]
        if all(replies) and all(replies[offset].sequence == replies[0].sequence + offset for offset in range(RECOVERY_REPLIES)):
            recovery = replies[0]
            return before_loss.timestamp, recovery.timestamp, recovery.timestamp - before_loss.timestamp
    raise ValueError("No se encontro una recuperacion de cinco respuestas consecutivas")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, help="directorio tp-final")
    args = parser.parse_args()

    by_scheme: dict[str, list[float]] = {}
    print("esquema,id,inicio_perdida,reanudacion,indisponibilidad_s")
    for scheme in SCHEMES:
        values = []
        raw = args.root / "simulacion" / "escenarios" / scheme / "resultados" / "raw"
        for run in RUNS:
            identifier = f"{scheme}-falla-r{run:02d}"
            start, recovery, duration = calculate(
                ping_events(raw / f"{identifier}-ping.log"),
                event_timestamp(raw / f"{identifier}-eventos.log"),
            )
            values.append(duration)
            print(f"{scheme},{identifier},{start:.6f},{recovery:.6f},{duration:.3f}")
        by_scheme[scheme] = values

    print("\nresumen,mediana_s,min_s,max_s")
    for scheme, values in by_scheme.items():
        print(f"{scheme},{median(values):.3f},{min(values):.3f},{max(values):.3f}")


if __name__ == "__main__":
    main()
