#!/usr/bin/env python3
"""Valida los artefactos de las corridas de refuerzo ya registradas."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path


PING_TIMESTAMP = re.compile(r"^\[(\d+\.\d+)]", re.MULTILINE)
ROUTE_SAMPLE = re.compile(r"^\S+\tnode=", re.MULTILINE)
SUSPENSION = re.compile(r"^(\S+) enlace-R2-R4-suspendido$", re.MULTILINE)


def timestamp(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def route_before_event(routes: str, event_at: float, gateway: str) -> bool:
    for line in routes.splitlines():
        fields = line.split("\t", 3)
        if len(fields) == 4 and timestamp(fields[0]) < event_at and f"gateway={gateway}" in fields[3]:
            return True
    return False


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_pcap(path: Path) -> None:
    result = subprocess.run(
        ["tshark", "-r", str(path), "-c", "1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    require(result.returncode == 0, f"PCAP invalido: {path}: {result.stderr.strip()}")


def validate_row(root: Path, row: dict[str, str]) -> None:
    run_id = row["id"]
    scheme = row["esquema_ruta"]
    artifacts = row["archivos"].split(";")
    require(all((root / "simulacion" / "escenarios" / scheme / artifact).is_file()
                and (root / "simulacion" / "escenarios" / scheme / artifact).stat().st_size > 0
                for artifact in artifacts), f"Artefacto faltante o vacio: {run_id}")

    raw = root / "simulacion" / "escenarios" / scheme / "resultados" / "raw"
    for artifact in artifacts:
        path = root / "simulacion" / "escenarios" / scheme / artifact
        if path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
        if path.suffix == ".pcap":
            validate_pcap(path)

    ping = (raw / f"{run_id}-ping.log").read_text(encoding="utf-8")
    timestamps = [float(value) for value in PING_TIMESTAMP.findall(ping)]
    # Congestion can legitimately discard replies, so require temporal coverage
    # rather than assuming five successful replies per second.
    require(len(timestamps) >= 100, f"Ping insuficiente: {run_id}")
    duration = float(row["duracion_s"])
    require(timestamps[-1] - timestamps[0] >= duration - 2,
            f"Ventana de ping incompleta: {run_id}")

    if row["tipo_trafico"] == "tcp-iperf3-slow-start":
        data = json.loads((raw / f"{run_id}.json").read_text(encoding="utf-8"))
        intervals = data["intervals"]
        require(intervals and intervals[0]["sum"]["start"] == 0, f"Slow start omitido: {run_id}")
        require(all(entry["streams"] and "snd_cwnd" in entry["streams"][0] for entry in intervals),
                f"snd_cwnd faltante: {run_id}")

    if row["ensayo"] == "convergencia":
        events = (raw / f"{run_id}-eventos.log").read_text(encoding="utf-8")
        require("enlace-R2-R4-suspendido" in events and "enlace-R2-R4-restaurado" in events,
                f"Eventos incompletos: {run_id}")
        match = SUSPENSION.search(events)
        require(match is not None, f"Suspension sin timestamp: {run_id}")
        suspended_at = timestamp(match.group(1))
        r1 = (raw / f"{run_id}-R1-ruta.log").read_text(encoding="utf-8")
        r4 = (raw / f"{run_id}-R4-ruta.log").read_text(encoding="utf-8")
        require(len(ROUTE_SAMPLE.findall(r1)) >= 1_000 and len(ROUTE_SAMPLE.findall(r4)) >= 1_000,
                f"Muestras de rutas insuficientes: {run_id}")
        require("gateway=10.10.13.2" in r1 and "gateway=10.10.45.1" in r4,
                f"Respaldo no observado: {run_id}")
        if scheme in {"rip", "ospf"}:
            require(route_before_event(r1, suspended_at, "10.10.12.2")
                    and route_before_event(r4, suspended_at, "10.10.24.1"),
                    f"Estado primario no observado antes de la falla: {run_id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, help="directorio tp-final")
    parser.add_argument("scheme", choices=("estatico", "rip", "ospf"))
    args = parser.parse_args()

    with (args.root / "simulacion" / "experimentos" / "matriz.csv").open(newline="", encoding="utf-8") as source:
        rows = [row for row in csv.DictReader(source)
                if row["esquema_ruta"] == args.scheme and "-rtt" in row["id"] or
                row["esquema_ruta"] == args.scheme and "-rutas" in row["id"] or
                row["esquema_ruta"] == args.scheme and "slow-start" in row["id"]]
    require(rows, f"No hay filas de refuerzo para {args.scheme}")
    pending = [row["id"] for row in rows if not all(row[field] for field in ("fecha_utc", "ejecutor", "archivos"))]
    require(not pending, f"Filas pendientes: {', '.join(pending)}")
    for row in rows:
        validate_row(args.root, row)
    print(f"Validadas {len(rows)} corridas de refuerzo para {args.scheme}.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"Validacion fallida: {error}")
