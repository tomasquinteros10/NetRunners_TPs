#!/usr/bin/env bash
# Run reproducible routing-failover measurements without RouterOS credentials.
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
API_URL=${GNS3_API_URL:-http://127.0.0.1:3080/v2}
PROJECT_ID=${GNS3_PROJECT_ID:-11c8a820-70c4-4271-b727-71dcb424c2e5}
MATRIX="$ROOT_DIR/simulacion/experimentos/matriz.csv"
SERVER_IP=10.10.4.10
FALLA_DESDE_S=${FALLA_DESDE_S:-20}
FALLA_DURACION_S=${FALLA_DURACION_S:-60}
DRY_RUN=false
FAULT_SUSPENDED=false
CAPTURE_R2_R4=false
CAPTURE_R5_R4=false
PING_PID=
HTTP_PID=

usage() {
    printf 'Uso: %s [--dry-run] <id> [<id> ...]\n' "${0##*/}"
    printf '     %s [--dry-run] --all\n' "${0##*/}"
}

require_command() {
    command -v "$1" >/dev/null || {
        printf 'Falta el comando requerido: %s\n' "$1" >&2
        exit 1
    }
}

api_get() {
    curl --fail --silent --show-error "$API_URL$1"
}

api_post() {
    local path=$1
    shift
    curl --fail --silent --show-error --request POST "$API_URL$path" "$@"
}

api_put() {
    local path=$1
    shift
    curl --fail --silent --show-error --request PUT "$API_URL$path" "$@"
}

stop_captures() {
    if [[ $CAPTURE_R2_R4 == true ]]; then
        api_post "/projects/$PROJECT_ID/links/$R2_R4_LINK_ID/stop_capture" >/dev/null || true
        CAPTURE_R2_R4=false
    fi
    if [[ $CAPTURE_R5_R4 == true ]]; then
        api_post "/projects/$PROJECT_ID/links/$R5_R4_LINK_ID/stop_capture" >/dev/null || true
        CAPTURE_R5_R4=false
    fi
}

restore_fault_link() {
    if [[ $FAULT_SUSPENDED == true ]]; then
        api_put "/projects/$PROJECT_ID/links/$R2_R4_LINK_ID" \
            --header 'Content-Type: application/json' --data '{"suspend":false}' >/dev/null || true
        FAULT_SUSPENDED=false
    fi
}

stop_processes() {
    [[ -z ${PING_PID:-} ]] || kill "$PING_PID" 2>/dev/null || true
    [[ -z ${HTTP_PID:-} ]] || kill "$HTTP_PID" 2>/dev/null || true
    [[ -z ${PING_PID:-} ]] || wait "$PING_PID" 2>/dev/null || true
    [[ -z ${HTTP_PID:-} ]] || wait "$HTTP_PID" 2>/dev/null || true
    PING_PID=
    HTTP_PID=
}

cleanup() {
    restore_fault_link
    stop_captures
    stop_processes
}
trap cleanup EXIT

node_field() {
    local nodes_json=$1 name=$2 field=$3
    printf '%s' "$nodes_json" | python3 -c '
import json
import sys

name, field = sys.argv[1:]
for node in json.load(sys.stdin):
    if node["name"] == name:
        value = node
        for key in field.split("."):
            value = value[key]
        print(value)
        break
else:
    raise SystemExit(f"Nodo no encontrado: {name}")
' "$name" "$field"
}

resolve_link() {
    local links_json=$1 left_name=$2 left_adapter=$3 right_name=$4 right_adapter=$5
    python3 -c '
import json
import sys

nodes = json.loads(sys.argv[1])
links = json.loads(sys.argv[2])
left_name, left_adapter, right_name, right_adapter = sys.argv[3:]
by_id = {node["node_id"]: node["name"] for node in nodes}
expected = {(left_name, int(left_adapter)), (right_name, int(right_adapter))}
for link in links:
    endpoints = {(by_id[endpoint["node_id"]], endpoint["adapter_number"])
                 for endpoint in link["nodes"]}
    if endpoints == expected:
        if link["suspend"]:
            raise SystemExit(f"El enlace ya esta suspendido: {left_name} - {right_name}")
        print(link["link_id"])
        break
else:
    raise SystemExit(f"Enlace no encontrado: {left_name}:e{left_adapter} - {right_name}:e{right_adapter}")
' "$NODES_JSON" "$links_json" "$left_name" "$left_adapter" "$right_name" "$right_adapter"
}

resolve_lab() {
    local links_json
    NODES_JSON=$(api_get "/projects/$PROJECT_ID/nodes")
    CLIENT_ID=$(node_field "$NODES_JSON" cliente 'properties.container_id')
    SERVER_ID=$(node_field "$NODES_JSON" servidor 'properties.container_id')
    printf '%s' "$NODES_JSON" | python3 -c '
import json
import sys

required = {"cliente", "servidor", "R1", "R2", "R3", "R4", "R5"}
nodes = {node["name"]: node["status"] for node in json.load(sys.stdin)}
missing = required - nodes.keys()
stopped = sorted(name for name in required if nodes.get(name) != "started")
if missing:
    raise SystemExit("Faltan nodos: " + ", ".join(sorted(missing)))
if stopped:
    raise SystemExit("Nodos no iniciados: " + ", ".join(stopped))
' >/dev/null
    links_json=$(api_get "/projects/$PROJECT_ID/links")
    R2_R4_LINK_ID=$(resolve_link "$links_json" R2 2 R4 1)
    R5_R4_LINK_ID=$(resolve_link "$links_json" R5 2 R4 2)
}

matrix_run_data() {
    python3 - "$MATRIX" "$1" <<'PY'
import csv
import sys

matrix, run_id = sys.argv[1:]
with open(matrix, newline='', encoding='utf-8') as source:
    rows = list(csv.DictReader(source))
matches = [row for row in rows if row['id'] == run_id]
if len(matches) != 1:
    raise SystemExit(f'ID inexistente o duplicado en la matriz: {run_id}')
row = matches[0]
if row['esquema_ruta'] not in {'estatico', 'rip', 'ospf'} or row['ensayo'] != 'convergencia' or row['tipo_trafico'] != 'http-1.1+icmp':
    raise SystemExit(f'El ID no corresponde a una corrida de convergencia: {run_id}')
if any(row[field] for field in ('fecha_utc', 'ejecutor', 'archivos')):
    raise SystemExit(f'La corrida ya esta registrada: {run_id}')
print(row['esquema_ruta'], row['duracion_s'])
PY
}

pending_runs() {
    python3 - "$MATRIX" <<'PY'
import csv
import sys

with open(sys.argv[1], newline='', encoding='utf-8') as source:
    for row in csv.DictReader(source):
        if (row['esquema_ruta'] in {'estatico', 'rip', 'ospf'} and row['ensayo'] == 'convergencia'
                and row['tipo_trafico'] == 'http-1.1+icmp'
                and not any(row[field] for field in ('fecha_utc', 'ejecutor', 'archivos'))):
            print(row['id'])
PY
}

mark_complete() {
    python3 - "$MATRIX" "$1" "$2" "${USER:-unknown}" "$3" <<'PY'
import csv
import os
import sys
import tempfile

matrix, run_id, timestamp, executor, artifacts = sys.argv[1:]
with open(matrix, newline='', encoding='utf-8') as source:
    reader = csv.DictReader(source)
    fields = reader.fieldnames
    rows = list(reader)
for row in rows:
    if row['id'] == run_id:
        row['fecha_utc'] = timestamp
        row['ejecutor'] = executor
        row['archivos'] = artifacts
        break
else:
    raise SystemExit(f'ID inexistente en la matriz: {run_id}')
directory = os.path.dirname(matrix)
with tempfile.NamedTemporaryFile('w', newline='', encoding='utf-8', dir=directory, delete=False) as target:
    writer = csv.DictWriter(target, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    temporary = target.name
os.replace(temporary, matrix)
PY
}

event() {
    printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" >> "$EVENTS_TMP"
}

run_one() {
    local run_id=$1 scheme duration raw_dir capture_dir ping_path http_path events_path r2_r4_path r5_r4_path ping_tmp http_tmp events_tmp r2_r4_response r5_r4_response r2_r4_source r5_r4_source remaining timestamp
    read -r scheme duration < <(matrix_run_data "$run_id")
    (( duration > FALLA_DESDE_S + FALLA_DURACION_S )) || {
        printf 'Duracion insuficiente para la falla de %s.\n' "$run_id" >&2
        return 1
    }
    raw_dir="$ROOT_DIR/simulacion/escenarios/$scheme/resultados/raw"
    capture_dir="$ROOT_DIR/simulacion/escenarios/$scheme/capturas"
    ping_path="$raw_dir/$run_id-ping.log"
    http_path="$raw_dir/$run_id-http.txt"
    events_path="$raw_dir/$run_id-eventos.log"
    r2_r4_path="$capture_dir/$run_id-R2-R4.pcap"
    r5_r4_path="$capture_dir/$run_id-R5-R4.pcap"
    ping_tmp="$ping_path.tmp"
    http_tmp="$http_path.tmp"
    events_tmp="$events_path.tmp"
    [[ ! -e $ping_path && ! -e $http_path && ! -e $events_path && ! -e $ping_tmp && ! -e $http_tmp && ! -e $events_tmp && ! -e $r2_r4_path && ! -e $r5_r4_path ]] || {
        printf 'Ya existe un artefacto para %s; no se sobrescribe.\n' "$run_id" >&2
        return 1
    }

    resolve_lab
    if [[ $DRY_RUN == true ]]; then
        printf 'Validada %s (%s, convergencia); no se ejecuto por --dry-run.\n' "$run_id" "$scheme"
        return
    fi
    mkdir -p "$raw_dir" "$capture_dir"
    docker exec "$CLIENT_ID" ping -c 3 -W 2 "$SERVER_IP" >/dev/null
    docker exec "$CLIENT_ID" curl --fail --silent --output /dev/null "http://$SERVER_IP:80/archivo-256k.bin"

    r2_r4_response=$(api_post "/projects/$PROJECT_ID/links/$R2_R4_LINK_ID/start_capture" --header 'Content-Type: application/json' --data "{\"capture_file_name\":\"$run_id-R2-R4.pcap\",\"data_link_type\":\"DLT_EN10MB\"}")
    CAPTURE_R2_R4=true
    r2_r4_source=$(printf '%s' "$r2_r4_response" | python3 -c 'import json, sys; print(json.load(sys.stdin)["capture_file_path"])')
    r5_r4_response=$(api_post "/projects/$PROJECT_ID/links/$R5_R4_LINK_ID/start_capture" --header 'Content-Type: application/json' --data "{\"capture_file_name\":\"$run_id-R5-R4.pcap\",\"data_link_type\":\"DLT_EN10MB\"}")
    CAPTURE_R5_R4=true
    r5_r4_source=$(printf '%s' "$r5_r4_response" | python3 -c 'import json, sys; print(json.load(sys.stdin)["capture_file_path"])')

    EVENTS_TMP=$events_tmp
    event normal-inicio
    docker exec "$CLIENT_ID" ping -D -i 0.2 "$SERVER_IP" > "$ping_tmp" &
    PING_PID=$!
    docker exec "$CLIENT_ID" wrk -t1 -c1 -d"${duration}s" --timeout 30s "http://$SERVER_IP:80/archivo-256k.bin" > "$http_tmp" &
    HTTP_PID=$!
    sleep "$FALLA_DESDE_S"
    event enlace-R2-R4-suspendido
    api_put "/projects/$PROJECT_ID/links/$R2_R4_LINK_ID" --header 'Content-Type: application/json' --data '{"suspend":true}' >/dev/null
    FAULT_SUSPENDED=true
    sleep "$FALLA_DURACION_S"
    event enlace-R2-R4-restaurado
    restore_fault_link
    remaining=$((duration - FALLA_DESDE_S - FALLA_DURACION_S))
    sleep "$remaining"
    event observacion-finalizada
    # Let wrk flush its summary instead of killing it at the nominal duration.
    [[ -z ${HTTP_PID:-} ]] || wait "$HTTP_PID"
    HTTP_PID=
    stop_processes
    stop_captures

    [[ -s $ping_tmp && -s $http_tmp && -s $events_tmp && -s $r2_r4_source && -s $r5_r4_source ]] || {
        printf 'Faltan artefactos validos para %s.\n' "$run_id" >&2
        return 1
    }
    grep -q '^Requests/sec:' "$http_tmp"
    grep -q '^Transfer/sec:' "$http_tmp"
    mv "$r2_r4_source" "$r2_r4_path"
    mv "$r5_r4_source" "$r5_r4_path"
    mv "$ping_tmp" "$ping_path"
    mv "$http_tmp" "$http_path"
    mv "$events_tmp" "$events_path"
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    mark_complete "$run_id" "$timestamp" "resultados/raw/$run_id-ping.log;resultados/raw/$run_id-http.txt;resultados/raw/$run_id-eventos.log;capturas/$run_id-R2-R4.pcap;capturas/$run_id-R5-R4.pcap"
    printf 'Completada %s (%s, convergencia automatizada).\n' "$run_id" "$scheme"
}

for command in curl docker python3 date; do
    require_command "$command"
done
[[ -f $MATRIX ]] || { printf 'No existe la matriz: %s\n' "$MATRIX" >&2; exit 1; }

if [[ ${1:-} == --dry-run ]]; then
    DRY_RUN=true
    shift
fi
if [[ $# -eq 1 && $1 == --all ]]; then
    mapfile -t RUNS < <(pending_runs)
elif [[ $# -gt 0 ]]; then
    RUNS=("$@")
else
    usage >&2
    exit 1
fi
[[ ${#RUNS[@]} -gt 0 ]] || { printf 'No hay corridas de convergencia pendientes.\n'; exit 0; }
for run_id in "${RUNS[@]}"; do
    run_one "$run_id"
done
