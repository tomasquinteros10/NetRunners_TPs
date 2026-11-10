#!/usr/bin/env python3
"""Deriva metricas comparables desde los artefactos crudos de la matriz.

No modifica resultados/raw, capturas ni matriz. Solo usa la biblioteca estandar.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


PING_REPLY = re.compile(
    r"\[(?P<time>[0-9.]+)] .*icmp_seq=(?P<seq>\d+).*time[=<](?P<rtt>[0-9.]+) ?(?P<unit>ms|s|us)"
)
PING_UNREACHABLE = re.compile(r"\[(?P<time>[0-9.]+)] .*Destination .*Unreachable")
EVENT = re.compile(r"^(?P<time>\S+) (?P<event>.+)$")
ROUTE = re.compile(r"^(?P<time>\S+)\tnode=(?P<node>\S+)\t.*?gateway=(?P<gateway>[^\s]+)")
WRK_LATENCY = re.compile(r"^\s*Latency\s+(?P<value>[0-9.]+)(?P<unit>us|ms|s)", re.MULTILINE)
WRK_REQUESTS = re.compile(r"^Requests/sec:\s+(?P<value>[0-9.]+)", re.MULTILINE)
WRK_TRANSFER = re.compile(r"^Transfer/sec:\s+(?P<value>[0-9.]+)(?P<unit>[KMG]?B)", re.MULTILINE)
WRK_REQUEST_COUNT = re.compile(r"^\s*(?P<value>\d+) requests in", re.MULTILINE)
WRK_ERRORS = re.compile(r"Socket errors:.*?timeout (?P<timeouts>\d+)")

RUN_FIELDS = [
    "id", "campana", "esquema_ruta", "ensayo", "tipo_trafico", "tasa_ofrecida_kbps", "duracion_s",
    "repeticion", "estado_enlace", "archivos_encontrados", "artefactos_faltantes",
    "udp_throughput_kbps", "udp_loss_pct", "udp_jitter_ms", "udp_lost_packets",
    "tcp_throughput_kbps", "tcp_retransmits", "tcp_rtt_mean_ms",
    "ping_replies", "ping_sequence_loss_pct", "ping_rtt_min_ms", "ping_rtt_mean_ms",
    "ping_rtt_median_ms", "ping_rtt_max_ms", "ping_rtt_stdev_ms",
    "http_requests", "http_requests_per_sec", "http_transfer_kib_per_sec",
    "http_latency_mean_ms", "http_timeouts",
    "service_outage_s", "service_recovery_s", "route_switch_max_s", "route_switch_nodes",
]
CWND_FIELDS = ["id", "esquema_ruta", "interval_start_s", "interval_end_s", "cwnd_bytes", "rtt_ms", "retransmits", "throughput_kbps"]


def number(value: object) -> float | None:
    return float(value) if value is not None else None


def median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def parse_time(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def rtt_ms(value: float, unit: str) -> float:
    return value * {"s": 1000, "ms": 1, "us": 0.001}[unit]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_iperf(path: Path, row: dict[str, object], cwnd_rows: list[dict[str, object]]) -> None:
    try:
        data = json.loads(read_text(path))
    except (OSError, json.JSONDecodeError):
        return
    protocol = data.get("start", {}).get("test_start", {}).get("protocol")
    end = data.get("end", {})
    received = end.get("sum_received", {})
    sent = end.get("sum_sent", {})
    throughput = number(received.get("bits_per_second"))
    if protocol == "UDP":
        row["udp_throughput_kbps"] = throughput / 1000 if throughput is not None else None
        for source, target in (("lost_percent", "udp_loss_pct"), ("jitter_ms", "udp_jitter_ms"), ("lost_packets", "udp_lost_packets")):
            row[target] = received.get(source)
        return
    row["tcp_throughput_kbps"] = throughput / 1000 if throughput is not None else None
    row["tcp_retransmits"] = sent.get("retransmits")
    intervals = data.get("intervals", [])
    interval_rtts = []
    for interval in intervals:
        stream = next((item for item in interval.get("streams", []) if item.get("sender")), None)
        if not stream:
            continue
        rtt = number(stream.get("rtt"))
        if rtt is not None:
            interval_rtts.append(rtt / 1000)
        if "snd_cwnd" in stream:
            cwnd_rows.append({
                "id": row["id"], "esquema_ruta": row["esquema_ruta"],
                "interval_start_s": stream.get("start"), "interval_end_s": stream.get("end"),
                "cwnd_bytes": stream.get("snd_cwnd"), "rtt_ms": rtt / 1000 if rtt is not None else None,
                "retransmits": stream.get("retransmits"),
                "throughput_kbps": number(stream.get("bits_per_second")) / 1000 if number(stream.get("bits_per_second")) is not None else None,
            })
    row["tcp_rtt_mean_ms"] = mean(interval_rtts)


def parse_ping(path: Path, row: dict[str, object]) -> list[tuple[float, int]]:
    replies: list[tuple[float, int]] = []
    rtts: list[float] = []
    for line in read_text(path).splitlines():
        match = PING_REPLY.search(line)
        if match:
            replies.append((float(match["time"]), int(match["seq"])))
            rtts.append(rtt_ms(float(match["rtt"]), match["unit"]))
    if not replies:
        return replies
    row["ping_replies"] = len(replies)
    span = replies[-1][1] - replies[0][1] + 1
    row["ping_sequence_loss_pct"] = (span - len(replies)) * 100 / span if span else 0
    row["ping_rtt_min_ms"] = min(rtts)
    row["ping_rtt_mean_ms"] = mean(rtts)
    row["ping_rtt_median_ms"] = median(rtts)
    row["ping_rtt_max_ms"] = max(rtts)
    row["ping_rtt_stdev_ms"] = statistics.stdev(rtts) if len(rtts) > 1 else 0
    return replies


def parse_wrk(path: Path, row: dict[str, object]) -> None:
    text = read_text(path)
    latency = WRK_LATENCY.search(text)
    if latency:
        row["http_latency_mean_ms"] = rtt_ms(float(latency["value"]), latency["unit"])
    for pattern, field in ((WRK_REQUESTS, "http_requests_per_sec"), (WRK_REQUEST_COUNT, "http_requests")):
        match = pattern.search(text)
        if match:
            row[field] = float(match["value"])
    transfer = WRK_TRANSFER.search(text)
    if transfer:
        factor = {"B": 1 / 1024, "KB": 1, "MB": 1024, "GB": 1024 * 1024}[transfer["unit"]]
        row["http_transfer_kib_per_sec"] = float(transfer["value"]) * factor
    errors = WRK_ERRORS.search(text)
    if errors:
        row["http_timeouts"] = int(errors["timeouts"])


def event_times(path: Path) -> dict[str, float]:
    events = {}
    for line in read_text(path).splitlines():
        match = EVENT.match(line)
        if match:
            events[match["event"]] = parse_time(match["time"])
    return events


def route_switches(route_logs: list[Path], suspended_at: float) -> tuple[float | None, str | None]:
    switched = []
    nodes = []
    for path in route_logs:
        samples = []
        for line in read_text(path).splitlines():
            match = ROUTE.match(line)
            if match:
                samples.append((parse_time(match["time"]), match["node"], match["gateway"]))
        before = [sample[2] for sample in samples if sample[0] < suspended_at]
        if not before:
            continue
        primary = Counter(before).most_common(1)[0][0]
        change = next((sample for sample in samples if sample[0] >= suspended_at and sample[2] != primary), None)
        if change:
            switched.append(change[0] - suspended_at)
            nodes.append(change[1])
    return (max(switched), ";".join(sorted(set(nodes)))) if switched else (None, None)


def service_metrics(ping_path: Path, events_path: Path, route_logs: list[Path], row: dict[str, object]) -> None:
    events = event_times(events_path)
    suspended_at = events.get("enlace-R2-R4-suspendido")
    if suspended_at is None:
        return
    replies = parse_ping(ping_path, row)
    before = [reply for reply in replies if reply[0] < suspended_at]
    after = [reply for reply in replies if reply[0] >= suspended_at]
    if before and after:
        # Five consecutive ICMP sequence numbers avoid counting transit replies as recovery.
        recovery = next((item[0] for index, item in enumerate(after) if index + 4 < len(after) and [x[1] for x in after[index:index + 5]] == list(range(item[1], item[1] + 5))), None)
        if recovery is not None:
            row["service_recovery_s"] = recovery - suspended_at
            row["service_outage_s"] = recovery - before[-1][0]
    row["route_switch_max_s"], row["route_switch_nodes"] = route_switches(route_logs, suspended_at)


def artifact_paths(root: Path, matrix_row: dict[str, str]) -> list[Path]:
    scheme = matrix_row["esquema_ruta"]
    raw = root / "simulacion" / "escenarios" / scheme / "resultados" / "raw"
    return [raw / Path(item).name for item in matrix_row["archivos"].split(";") if "/raw/" in item]


def aggregate(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    keys = ("campana", "esquema_ruta", "ensayo", "tipo_trafico", "tasa_ofrecida_kbps", "estado_enlace")
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    result = []
    for group, members in groups.items():
        for field in RUN_FIELDS:
            if field in {"archivos_encontrados"}:
                continue
            values = [float(row[field]) for row in members if isinstance(row.get(field), (int, float)) and not isinstance(row[field], bool) and math.isfinite(float(row[field]))]
            if not values:
                continue
            result.append(dict(zip(keys, group)) | {
                "metrica": field, "n": len(values), "media": mean(values), "mediana": median(values),
                "minimo": min(values), "maximo": max(values), "desvio_estandar": statistics.stdev(values) if len(values) > 1 else 0,
            })
    return result


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?", default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, help="directorio de salida (predeterminado: simulacion/resultados-derivados)")
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output or root / "simulacion" / "resultados-derivados"
    output.mkdir(parents=True, exist_ok=True)
    matrix = root / "simulacion" / "experimentos" / "matriz.csv"
    with matrix.open(newline="", encoding="utf-8") as source:
        matrix_rows = list(csv.DictReader(source))
    runs: list[dict[str, object]] = []
    cwnd_rows: list[dict[str, object]] = []
    for item in matrix_rows:
        row = {field: item.get(field, "") for field in RUN_FIELDS}
        row["campana"] = "refuerzo" if any(token in item["id"] for token in ("-rtt", "-rutas", "slow-start")) else "original"
        paths = artifact_paths(root, item)
        existing = [path for path in paths if path.exists()]
        row["archivos_encontrados"] = len(existing)
        row["artefactos_faltantes"] = ";".join(path.name for path in paths if not path.exists())
        for path in existing:
            if path.suffix == ".json":
                parse_iperf(path, row, cwnd_rows)
            elif path.name.endswith("-ping.log"):
                parse_ping(path, row)
            elif path.suffix == ".txt":
                parse_wrk(path, row)
        event_path = next((path for path in existing if path.name.endswith("-eventos.log")), None)
        ping_path = next((path for path in existing if path.name.endswith("-ping.log")), None)
        route_logs = [path for path in existing if path.name.endswith("-ruta.log")]
        if event_path and ping_path:
            service_metrics(ping_path, event_path, route_logs, row)
        runs.append(row)
    write_csv(output / "corridas.csv", RUN_FIELDS, runs)
    write_csv(output / "agregados.csv", ["campana", "esquema_ruta", "ensayo", "tipo_trafico", "tasa_ofrecida_kbps", "estado_enlace", "metrica", "n", "media", "mediana", "minimo", "maximo", "desvio_estandar"], aggregate(runs))
    write_csv(output / "tcp_cwnd_series.csv", CWND_FIELDS, cwnd_rows)
    print(f"{len(runs)} corridas, {len(cwnd_rows)} muestras cwnd: {output}")


if __name__ == "__main__":
    main()
