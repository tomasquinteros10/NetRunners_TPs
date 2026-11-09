#!/usr/bin/env bash
# Execute formal traffic runs on the active GNS3 routing scenario.
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
API_URL=${GNS3_API_URL:-http://127.0.0.1:3080/v2}
PROJECT_ID=${GNS3_PROJECT_ID:-11c8a820-70c4-4271-b727-71dcb424c2e5}
MATRIX="$ROOT_DIR/simulacion/experimentos/matriz.csv"
CLIENT_NAME=cliente
SERVER_NAME=servidor
SERVER_IP=10.10.4.10
CAPTURE_LEFT=R2
CAPTURE_LEFT_ADAPTER=2
CAPTURE_RIGHT=R4
CAPTURE_RIGHT_ADAPTER=1
CAPTURE_LINK_ID=
CAPTURE_ACTIVE=false
DRY_RUN=false
TRAFFIC_TYPE=

usage() {
    printf 'Uso: %s --tipo <udp|tcp|http|contencion-tcp-udp|contencion-http-udp> [--dry-run] <id> [<id> ...]\n' "${0##*/}"
    printf '     %s --tipo <udp|tcp|http|contencion-tcp-udp|contencion-http-udp> [--dry-run] --all\n' "${0##*/}"
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

stop_capture() {
    if [[ $CAPTURE_ACTIVE == true ]]; then
        api_post "/projects/$PROJECT_ID/links/$CAPTURE_LINK_ID/stop_capture" >/dev/null || true
        CAPTURE_ACTIVE=false
    fi
}

cleanup() {
    stop_capture
}
trap cleanup EXIT

node_field() {
    local nodes_json=$1
    local name=$2
    local field=$3
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

resolve_lab() {
    local nodes_json links_json
    nodes_json=$(api_get "/projects/$PROJECT_ID/nodes")
    CLIENT_ID=$(node_field "$nodes_json" "$CLIENT_NAME" 'properties.container_id')
    SERVER_ID=$(node_field "$nodes_json" "$SERVER_NAME" 'properties.container_id')

    printf '%s' "$nodes_json" | python3 -c '
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
    CAPTURE_LINK_ID=$(python3 -c '
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
        print(link["link_id"])
        break
else:
    raise SystemExit(f"Enlace no encontrado: {left_name}:e{left_adapter} - {right_name}:e{right_adapter}")
' "$nodes_json" "$links_json" "$CAPTURE_LEFT" "$CAPTURE_LEFT_ADAPTER" "$CAPTURE_RIGHT" "$CAPTURE_RIGHT_ADAPTER")
}

matrix_run_data() {
    python3 - "$MATRIX" "$1" "$2" <<'PY'
import csv
import sys

matrix, run_id, expected_type = sys.argv[1:]
with open(matrix, newline='', encoding='utf-8') as source:
    rows = list(csv.DictReader(source))
matches = [row for row in rows if row['id'] == run_id]
if len(matches) != 1:
    raise SystemExit(f'ID inexistente o duplicado en la matriz: {run_id}')
row = matches[0]
if row['esquema_ruta'] not in {'estatico', 'rip', 'ospf'} or row['tipo_trafico'] != expected_type:
    raise SystemExit(f'El ID no corresponde al tipo de trafico solicitado: {run_id}')
if any(row[field] for field in ('fecha_utc', 'ejecutor', 'archivos')):
    raise SystemExit(f'La corrida ya esta registrada: {run_id}')
print(row['esquema_ruta'], row['tipo_trafico'], row['tasa_ofrecida_kbps'], row['duracion_s'], row['inicio_flujo_secundario_s'] or 0)
PY
}

pending_runs() {
    python3 - "$MATRIX" "$1" <<'PY'
import csv
import sys

with open(sys.argv[1], newline='', encoding='utf-8') as source:
    for row in csv.DictReader(source):
        if (row['esquema_ruta'] in {'estatico', 'rip', 'ospf'} and row['tipo_trafico'] == sys.argv[2]
                and not any(row[field] for field in ('fecha_utc', 'ejecutor', 'archivos'))):
            print(row['id'])
PY
}

mark_complete() {
    local run_id=$1
    local timestamp=$2
    local artifacts=$3
    python3 - "$MATRIX" "$run_id" "$timestamp" "${USER:-unknown}" "$artifacts" <<'PY'
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

run_tcp_udp_contention() {
    local run_id=$1 scheme=$2 rate=$3 duration=$4 delay=$5 raw_dir capture_dir capture_name capture_response capture_path udp_tmp tcp_tmp udp_path tcp_path pcap_path timestamp secondary_duration udp_pid
    raw_dir="$ROOT_DIR/simulacion/escenarios/$scheme/resultados/raw"
    capture_dir="$ROOT_DIR/simulacion/escenarios/$scheme/capturas"
    udp_path="$raw_dir/$run_id-udp.json"
    tcp_path="$raw_dir/$run_id-tcp.json"
    udp_tmp="$udp_path.tmp"
    tcp_tmp="$tcp_path.tmp"
    pcap_path="$capture_dir/$run_id-R2-R4.pcap"
    capture_name="$run_id-R2-R4.pcap"
    secondary_duration=$((duration - delay))

    (( delay > 0 && secondary_duration > 0 )) || {
        printf 'Duraciones invalidas para %s.\n' "$run_id" >&2
        return 1
    }
    [[ ! -e $udp_path && ! -e $tcp_path && ! -e $udp_tmp && ! -e $tcp_tmp && ! -e $pcap_path ]] || {
        printf 'Ya existe un artefacto para %s; no se sobrescribe.\n' "$run_id" >&2
        return 1
    }

    resolve_lab
    if [[ $DRY_RUN == true ]]; then
        printf 'Validada %s (%s, TCP+UDP); no se ejecuto por --dry-run.\n' "$run_id" "$scheme"
        return 0
    fi
    mkdir -p "$raw_dir" "$capture_dir"
    docker exec "$CLIENT_ID" ping -c 3 -W 2 "$SERVER_IP" >/dev/null

    capture_response=$(api_post "/projects/$PROJECT_ID/links/$CAPTURE_LINK_ID/start_capture" \
        --header 'Content-Type: application/json' \
        --data "{\"capture_file_name\":\"$capture_name\",\"data_link_type\":\"DLT_EN10MB\"}")
    CAPTURE_ACTIVE=true
    capture_path=$(printf '%s' "$capture_response" | python3 -c 'import json, sys; print(json.load(sys.stdin)["capture_file_path"])')

    docker exec --detach "$SERVER_ID" iperf3 -s -1 -p 5201 >/dev/null
    docker exec --detach "$SERVER_ID" iperf3 -s -1 -p 5202 >/dev/null
    sleep 1
    docker exec "$CLIENT_ID" iperf3 -c "$SERVER_IP" -u -p 5201 -b "${rate}K" -l 1200 -t "$duration" -i 1 -J > "$udp_tmp" &
    udp_pid=$!
    sleep "$delay"
    docker exec "$CLIENT_ID" iperf3 -c "$SERVER_IP" -p 5202 -t "$secondary_duration" -i 1 -J > "$tcp_tmp"
    wait "$udp_pid"
    stop_capture

    python3 -m json.tool "$udp_tmp" >/dev/null
    python3 -m json.tool "$tcp_tmp" >/dev/null
    [[ -s $capture_path ]] || {
        printf 'La captura de %s no se genero correctamente.\n' "$run_id" >&2
        return 1
    }
    mv "$capture_path" "$pcap_path"
    mv "$udp_tmp" "$udp_path"
    mv "$tcp_tmp" "$tcp_path"
    timestamp=$(python3 - "$udp_path" <<'PY'
import datetime
import json
import sys

with open(sys.argv[1], encoding='utf-8') as source:
    seconds = json.load(source)['start']['timestamp']['timesecs']
print(datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
PY
)
    mark_complete "$run_id" "$timestamp" "resultados/raw/$run_id-udp.json;resultados/raw/$run_id-tcp.json;capturas/$run_id-R2-R4.pcap"
    printf 'Completada %s (%s, TCP+UDP, UDP %s Kbit/s, TCP desde %s s).\n' "$run_id" "$scheme" "$rate" "$delay"
}

run_http_udp_contention() {
    local run_id=$1 scheme=$2 rate=$3 duration=$4 delay=$5 raw_dir capture_dir capture_name capture_response capture_path udp_tmp http_tmp udp_path http_path pcap_path timestamp secondary_duration udp_pid
    raw_dir="$ROOT_DIR/simulacion/escenarios/$scheme/resultados/raw"
    capture_dir="$ROOT_DIR/simulacion/escenarios/$scheme/capturas"
    udp_path="$raw_dir/$run_id-udp.json"
    http_path="$raw_dir/$run_id-http.txt"
    udp_tmp="$udp_path.tmp"
    http_tmp="$http_path.tmp"
    pcap_path="$capture_dir/$run_id-R2-R4.pcap"
    capture_name="$run_id-R2-R4.pcap"
    secondary_duration=$((duration - delay))

    (( delay > 0 && secondary_duration > 0 )) || {
        printf 'Duraciones invalidas para %s.\n' "$run_id" >&2
        return 1
    }
    [[ ! -e $udp_path && ! -e $http_path && ! -e $udp_tmp && ! -e $http_tmp && ! -e $pcap_path ]] || {
        printf 'Ya existe un artefacto para %s; no se sobrescribe.\n' "$run_id" >&2
        return 1
    }

    resolve_lab
    if [[ $DRY_RUN == true ]]; then
        printf 'Validada %s (%s, HTTP+UDP); no se ejecuto por --dry-run.\n' "$run_id" "$scheme"
        return 0
    fi
    mkdir -p "$raw_dir" "$capture_dir"
    docker exec "$CLIENT_ID" ping -c 3 -W 2 "$SERVER_IP" >/dev/null
    docker exec "$CLIENT_ID" curl --fail --silent --output /dev/null "http://$SERVER_IP:80/archivo-256k.bin"

    capture_response=$(api_post "/projects/$PROJECT_ID/links/$CAPTURE_LINK_ID/start_capture" \
        --header 'Content-Type: application/json' \
        --data "{\"capture_file_name\":\"$capture_name\",\"data_link_type\":\"DLT_EN10MB\"}")
    CAPTURE_ACTIVE=true
    capture_path=$(printf '%s' "$capture_response" | python3 -c 'import json, sys; print(json.load(sys.stdin)["capture_file_path"])')

    docker exec --detach "$SERVER_ID" iperf3 -s -1 -p 5201 >/dev/null
    sleep 1
    # HTTP responses and reverse UDP share the R4-to-R2 bottleneck queue.
    docker exec "$CLIENT_ID" iperf3 -c "$SERVER_IP" -u -R -p 5201 -b "${rate}K" -l 1200 -t "$duration" -i 1 -J > "$udp_tmp" &
    udp_pid=$!
    sleep "$delay"
    docker exec "$CLIENT_ID" wrk -t1 -c1 -d"${secondary_duration}s" --timeout 30s "http://$SERVER_IP:80/archivo-256k.bin" > "$http_tmp"
    wait "$udp_pid"
    stop_capture

    python3 -m json.tool "$udp_tmp" >/dev/null
    grep -q '^Requests/sec:' "$http_tmp"
    grep -q '^Transfer/sec:' "$http_tmp"
    [[ -s $capture_path ]] || {
        printf 'La captura de %s no se genero correctamente.\n' "$run_id" >&2
        return 1
    }
    mv "$capture_path" "$pcap_path"
    mv "$udp_tmp" "$udp_path"
    mv "$http_tmp" "$http_path"
    timestamp=$(python3 - "$udp_path" <<'PY'
import datetime
import json
import sys

with open(sys.argv[1], encoding='utf-8') as source:
    seconds = json.load(source)['start']['timestamp']['timesecs']
print(datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
PY
)
    mark_complete "$run_id" "$timestamp" "resultados/raw/$run_id-udp.json;resultados/raw/$run_id-http.txt;capturas/$run_id-R2-R4.pcap"
    printf 'Completada %s (%s, HTTP+UDP, UDP %s Kbit/s, HTTP desde %s s).\n' "$run_id" "$scheme" "$rate" "$delay"
}

run_one() {
    local run_id=$1 scheme traffic_type rate duration delay raw_dir capture_dir capture_name capture_response capture_path raw_extension raw_tmp raw_path pcap_path timestamp
    read -r scheme traffic_type rate duration delay < <(matrix_run_data "$run_id" "$TRAFFIC_TYPE")
    if [[ $traffic_type == tcp-iperf3+udp ]]; then
        run_tcp_udp_contention "$run_id" "$scheme" "$rate" "$duration" "$delay"
        return
    fi
    if [[ $traffic_type == http-1.1+udp ]]; then
        run_http_udp_contention "$run_id" "$scheme" "$rate" "$duration" "$delay"
        return
    fi
    raw_dir="$ROOT_DIR/simulacion/escenarios/$scheme/resultados/raw"
    capture_dir="$ROOT_DIR/simulacion/escenarios/$scheme/capturas"
    raw_extension=json
    [[ $traffic_type == http-1.1 ]] && raw_extension=txt
    raw_path="$raw_dir/$run_id.$raw_extension"
    raw_tmp="$raw_path.tmp"
    pcap_path="$capture_dir/$run_id-R2-R4.pcap"
    capture_name="$run_id-R2-R4.pcap"

    [[ ! -e $raw_path && ! -e $raw_tmp && ! -e $pcap_path ]] || {
        printf 'Ya existe un artefacto para %s; no se sobrescribe.\n' "$run_id" >&2
        return 1
    }

    resolve_lab
    if [[ $DRY_RUN == true ]]; then
        printf 'Validada %s (%s, %s); no se ejecuto por --dry-run.\n' "$run_id" "$scheme" "$traffic_type"
        return 0
    fi
    mkdir -p "$raw_dir" "$capture_dir"
    docker exec "$CLIENT_ID" ping -c 3 -W 2 "$SERVER_IP" >/dev/null
    if [[ $traffic_type == http-1.1 ]]; then
        docker exec "$CLIENT_ID" curl --fail --silent --output /dev/null "http://$SERVER_IP:80/archivo-256k.bin"
    fi

    capture_response=$(api_post "/projects/$PROJECT_ID/links/$CAPTURE_LINK_ID/start_capture" \
        --header 'Content-Type: application/json' \
        --data "{\"capture_file_name\":\"$capture_name\",\"data_link_type\":\"DLT_EN10MB\"}")
    CAPTURE_ACTIVE=true
    capture_path=$(printf '%s' "$capture_response" | python3 -c 'import json, sys; print(json.load(sys.stdin)["capture_file_path"])')

    if [[ $traffic_type == udp ]]; then
        docker exec --detach "$SERVER_ID" iperf3 -s -1 >/dev/null
        sleep 1
        docker exec "$CLIENT_ID" iperf3 -c "$SERVER_IP" -u -b "${rate}K" -l 1200 -t "$duration" -i 1 -J > "$raw_tmp"
    elif [[ $traffic_type == tcp-iperf3 ]]; then
        docker exec --detach "$SERVER_ID" iperf3 -s -1 >/dev/null
        sleep 1
        docker exec "$CLIENT_ID" iperf3 -c "$SERVER_IP" -t "$duration" -O 10 -i 1 -J > "$raw_tmp"
    else
        docker exec "$CLIENT_ID" wrk -t1 -c1 -d"${duration}s" --timeout 10s "http://$SERVER_IP:80/archivo-256k.bin" > "$raw_tmp"
    fi
    stop_capture

    if [[ $raw_extension == json ]]; then
        python3 -m json.tool "$raw_tmp" >/dev/null
    else
        grep -q '^Requests/sec:' "$raw_tmp"
        grep -q '^Transfer/sec:' "$raw_tmp"
    fi
    [[ -s $capture_path ]] || {
        printf 'La captura de %s no se genero correctamente.\n' "$run_id" >&2
        return 1
    }
    mv "$capture_path" "$pcap_path"
    mv "$raw_tmp" "$raw_path"
    timestamp=$(python3 - "$raw_path" "$raw_extension" <<'PY'
import datetime
import json
import sys

if sys.argv[2] == 'json':
    with open(sys.argv[1], encoding='utf-8') as source:
        seconds = json.load(source)['start']['timestamp']['timesecs']
    print(datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
else:
    print(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
PY
)
    mark_complete "$run_id" "$timestamp" "resultados/raw/$run_id.$raw_extension;capturas/$run_id-R2-R4.pcap"
    printf 'Completada %s (%s, %s, %s s).\n' "$run_id" "$scheme" "$traffic_type" "$duration"
}

for command in curl docker python3; do
    require_command "$command"
done
[[ -f $MATRIX ]] || { printf 'No existe la matriz: %s\n' "$MATRIX" >&2; exit 1; }

if [[ ${1:-} != --tipo || $# -lt 2 ]]; then
    usage >&2
    exit 1
fi
case $2 in
    udp) TRAFFIC_TYPE=udp ;;
    tcp) TRAFFIC_TYPE=tcp-iperf3 ;;
    http) TRAFFIC_TYPE=http-1.1 ;;
    contencion-tcp-udp) TRAFFIC_TYPE=tcp-iperf3+udp ;;
    contencion-http-udp) TRAFFIC_TYPE=http-1.1+udp ;;
    *) usage >&2; exit 1 ;;
esac
shift 2

if [[ ${1:-} == --dry-run ]]; then
    DRY_RUN=true
    shift
fi

if [[ $# -eq 1 && $1 == --all ]]; then
    mapfile -t RUNS < <(pending_runs "$TRAFFIC_TYPE")
elif [[ $# -gt 0 ]]; then
    RUNS=("$@")
else
    usage >&2
    exit 1
fi

[[ ${#RUNS[@]} -gt 0 ]] || { printf 'No hay corridas %s pendientes.\n' "$TRAFFIC_TYPE"; exit 0; }
for run_id in "${RUNS[@]}"; do
    run_one "$run_id"
done
