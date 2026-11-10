#!/usr/bin/env bash
# Ejecuta únicamente corridas instrumentadas pendientes para un esquema activo.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
MATRIX="$ROOT_DIR/simulacion/experimentos/matriz.csv"
DRY_RUN=false

usage() {
    printf 'Uso: %s [--dry-run] <estatico|rip|ospf|--all-esquemas>\n' "${0##*/}"
}

pending_ids() {
    local scheme=$1 traffic_type=$2
    python3 - "$MATRIX" "$scheme" "$traffic_type" <<'PY'
import csv
import sys

matrix, scheme, traffic_type = sys.argv[1:]
with open(matrix, newline='', encoding='utf-8') as source:
    for row in csv.DictReader(source):
        if (row['esquema_ruta'] == scheme and row['tipo_trafico'] == traffic_type
                and not any(row[field] for field in ('fecha_utc', 'ejecutor', 'archivos'))):
            print(row['id'])
PY
}

run_type() {
    local scheme=$1 traffic_type=$2 executable=$3
    local ids=()
    mapfile -t ids < <(pending_ids "$scheme" "$traffic_type")
    [[ ${#ids[@]} -eq 0 ]] && return
    printf 'Ejecutando %s para %s: %s\n' "$traffic_type" "$scheme" "${ids[*]}"
    if [[ $DRY_RUN == true ]]; then
        "$SCRIPT_DIR/$executable" --dry-run "${ids[@]}"
    else
        "$SCRIPT_DIR/$executable" "${ids[@]}"
    fi
}

run_scheme() {
    local scheme=$1
    printf 'Confirma que GNS3 tiene activo el esquema %s, los siete nodos iniciados y R2-R4 restaurado.\n' "$scheme"
    if [[ $DRY_RUN == false ]]; then
        read -r -p 'Escribi SI para continuar: ' confirmation
        [[ $confirmation == SI ]] || { printf 'Cancelado.\n'; return 1; }
    fi
    run_type "$scheme" udp ejecutar_udp.sh
    run_type "$scheme" tcp-iperf3 ejecutar_tcp.sh
    run_type "$scheme" tcp-iperf3-slow-start ejecutar_tcp_slow_start.sh
    run_type "$scheme" http-1.1 ejecutar_http.sh
    run_type "$scheme" tcp-iperf3+udp ejecutar_contencion_tcp_udp.sh
    run_type "$scheme" http-1.1+udp ejecutar_contencion_http_udp.sh
    run_type "$scheme" http-1.1+icmp ejecutar_convergencia.sh
}

if [[ ${1:-} == --dry-run ]]; then
    DRY_RUN=true
    shift
fi
[[ $# -eq 1 ]] || { usage >&2; exit 1; }
case $1 in
    estatico|rip|ospf)
        [[ $DRY_RUN == true ]] && python3 "$SCRIPT_DIR/preparar_refuerzo.py" --check || python3 "$SCRIPT_DIR/preparar_refuerzo.py"
        run_scheme "$1"
        ;;
    --all-esquemas)
        [[ $DRY_RUN == true ]] && python3 "$SCRIPT_DIR/preparar_refuerzo.py" --check || python3 "$SCRIPT_DIR/preparar_refuerzo.py"
        for scheme in estatico rip ospf; do
            run_scheme "$scheme"
        done
        ;;
    *) usage >&2; exit 1 ;;
esac
