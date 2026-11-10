#!/usr/bin/env python3
"""Registra por consola Telnet la ruta activa de un CHR sin modificarlo."""

import argparse
import datetime as dt
import re
import socket
import sys
import time


IAC = 255
DO = 253
DONT = 254
WILL = 251
WONT = 252
ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def clean_telnet(data: bytes) -> bytes:
    """Responde negociacion Telnet y devuelve solo texto de RouterOS."""
    output = bytearray()
    index = 0
    while index < len(data):
        byte = data[index]
        if byte != IAC:
            output.append(byte)
            index += 1
            continue
        if index + 1 >= len(data):
            break
        command = data[index + 1]
        if command == IAC:
            output.append(IAC)
            index += 2
            continue
        if command in {DO, DONT, WILL, WONT} and index + 2 < len(data):
            index += 3
            continue
        index += 2
    return bytes(output)


def read_available(connection: socket.socket, wait_s: float) -> str:
    deadline = time.monotonic() + wait_s
    chunks = []
    while time.monotonic() < deadline:
        try:
            data = connection.recv(4096)
        except socket.timeout:
            continue
        if not data:
            break
        chunks.append(clean_telnet(data))
        if b'] >' in b''.join(chunks):
            break
    return b''.join(chunks).decode('utf-8', errors='replace')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', required=True, type=int)
    parser.add_argument('--node', required=True)
    parser.add_argument('--destination')
    parser.add_argument('--interval-ms', default=200, type=int)
    parser.add_argument('--duration-s', required=True, type=float)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    selector = 'where active=yes'
    if args.destination:
        selector = f'where dst-address={args.destination} and active=yes'
    command = f'/ip route print detail {selector}\r\n'.encode()
    with socket.create_connection((args.host, args.port), timeout=3) as connection:
        connection.settimeout(0.05)
        # Decline terminal options; RouterOS then emits a normal terminal prompt.
        connection.sendall(bytes((IAC, WONT, 1, IAC, DONT, 3)))
        read_available(connection, 0.5)
        started = time.monotonic()
        with open(args.output, 'x', encoding='utf-8') as target:
            while time.monotonic() - started < args.duration_s:
                observed = dt.datetime.now(dt.timezone.utc).isoformat(timespec='milliseconds')
                connection.sendall(command)
                response = read_available(connection, 0.15)
                # RouterOS emits terminal colors even through the local console.
                # Removing them keeps gateway and route flags directly parseable.
                plain = ANSI_ESCAPE.sub('', response).replace('\x1b', '')
                plain = re.sub(r'\[\d+(?:;\d+)*[A-Za-z]', '', plain)
                compact = ' '.join(line.strip() for line in plain.splitlines() if line.strip())
                destination = args.destination or 'todas-las-rutas-activas'
                target.write(f'{observed}\tnode={args.node}\tdestination={destination}\t{compact}\n')
                target.flush()
                time.sleep(args.interval_ms / 1000)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        print(f'Error al monitorear rutas: {error}', file=sys.stderr)
        raise SystemExit(1)
