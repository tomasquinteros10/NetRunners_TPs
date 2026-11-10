#!/usr/bin/env python3
"""Acota la convergencia de reenvio usando las rutas activas de R1 y R4."""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path


EVENT = re.compile(r"^(?P<time>\S+) enlace-R2-R4-suspendido$")
SAMPLE = re.compile(r"^(?P<time>\S+)\tnode=(?P<node>R[14])\t.*gateway=(?P<gateway>[^\s]+)")
BACKUP_GATEWAYS = {"R1": "10.10.13.2", "R4": "10.10.45.1"}


def timestamp(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(
        tzinfo=timezone.utc
    ).timestamp()


def event_time(path: Path) -> float:
    for line in path.read_text(encoding="utf-8").splitlines():
        match = EVENT.match(line)
        if match:
            return timestamp(match["time"])
    raise ValueError(f"No se encontro la suspension en {path}")


def transition(path: Path, node: str, suspended_at: float) -> tuple[float, float]:
    previous = suspended_at
    for line in path.read_text(encoding="utf-8").splitlines():
        match = SAMPLE.match(line)
        if not match:
            continue
        observed_at = timestamp(match["time"])
        if observed_at < suspended_at:
            continue
        gateway = match["gateway"].split("%", 1)[0]
        if gateway == BACKUP_GATEWAYS[node]:
            return previous, observed_at
        previous = observed_at
    raise ValueError(f"No se observo el respaldo de {node} en {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, help="directorio tp-final")
    parser.add_argument("scheme", choices=("estatico", "rip", "ospf"))
    parser.add_argument("run_id", help="ID de la corrida de convergencia")
    args = parser.parse_args()

    raw = args.root / "simulacion" / "escenarios" / args.scheme / "resultados" / "raw"
    suspended_at = event_time(raw / f"{args.run_id}-eventos.log")
    r1_previous, r1_backup = transition(raw / f"{args.run_id}-R1-ruta.log", "R1", suspended_at)
    r4_previous, r4_backup = transition(raw / f"{args.run_id}-R4-ruta.log", "R4", suspended_at)
    lower = max(r1_previous, r4_previous) - suspended_at
    upper = max(r1_backup, r4_backup) - suspended_at
    print("id,convergencia_min_s,convergencia_max_s,r1_respaldo_s,r4_respaldo_s")
    print(f"{args.run_id},{lower:.3f},{upper:.3f},{r1_backup - suspended_at:.3f},{r4_backup - suspended_at:.3f}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f"Error al procesar convergencia: {error}")
