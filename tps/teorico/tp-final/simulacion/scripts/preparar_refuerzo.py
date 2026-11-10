#!/usr/bin/env python3
"""Agrega corridas instrumentadas sin modificar ni reutilizar las existentes."""

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / 'simulacion/experimentos/matriz.csv'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()

    with MATRIX.open(newline='', encoding='utf-8') as source:
        reader = csv.DictReader(source)
        fields = reader.fieldnames
        rows = list(reader)
    assert fields is not None
    ids = {row['id'] for row in rows}
    additions = []

    # Repite las pruebas de carga estáticas con RTT continuo como artefacto.
    for row in rows:
        if (row['esquema_ruta'] != 'estatico' or row['ensayo'] not in {'congestion', 'contencion'}
                or row['tipo_trafico'] == 'tcp-iperf3-slow-start'):
            continue
        if row['id'].endswith('-rtt'):
            continue
        new_id = f"{row['id']}-rtt"
        if new_id in ids:
            continue
        copy = row.copy()
        copy.update({
            'id': new_id,
            'parametros': f"{row['parametros']}; ping -D -i 0.2 como instrumentacion RTT",
            'fecha_utc': '',
            'ejecutor': '',
            'archivos': '',
        })
        additions.append(copy)
        ids.add(new_id)

    # Agrega una serie TCP sin periodo omitido para observar el inicio de conexion.
    for repetition in range(1, 6):
        new_id = f'estatico-tcp-slow-start-r{repetition:02d}'
        if new_id in ids:
            continue
        additions.append({
            'id': new_id,
            'esquema_ruta': 'estatico',
            'ensayo': 'congestion',
            'tipo_trafico': 'tcp-iperf3-slow-start',
            'tasa_ofrecida_kbps': 'no_aplica',
            'duracion_s': '60',
            'inicio_flujo_secundario_s': '',
            'repeticion': str(repetition),
            'estado_enlace': 'R2-R4-activo',
            'parametros': 'iperf3 -t 60 -i 0.2 -J sin -O; ping -D -i 0.2 como instrumentacion RTT',
            'fecha_utc': '',
            'ejecutor': '',
            'archivos': '',
        })
        ids.add(new_id)

    # Repite las fallas con muestras de rutas activas en los cinco routers.
    for row in rows:
        if row['ensayo'] != 'convergencia' or row['tipo_trafico'] != 'http-1.1+icmp':
            continue
        if row['id'].endswith('-rutas'):
            continue
        new_id = f"{row['id']}-rutas"
        if new_id in ids:
            continue
        copy = row.copy()
        copy.update({
            'id': new_id,
            'parametros': f"{row['parametros']}; rutas activas R1-R5 cada 200 ms por consola Telnet",
            'fecha_utc': '',
            'ejecutor': '',
            'archivos': '',
        })
        additions.append(copy)
        ids.add(new_id)

    if args.check:
        print(f'{len(additions)} corridas instrumentadas pendientes de agregar.')
        return
    if not additions:
        print('La matriz ya contiene todas las corridas instrumentadas.')
        return
    with MATRIX.open('a', newline='', encoding='utf-8') as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writerows(additions)
    print(f'Agregadas {len(additions)} corridas instrumentadas a {MATRIX}.')


if __name__ == '__main__':
    main()
