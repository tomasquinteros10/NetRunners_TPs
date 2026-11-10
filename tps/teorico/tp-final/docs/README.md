# Calculo reproducible de indisponibilidad

`indisponibilidad.py` calcula la indisponibilidad de las 15 corridas formales
de convergencia a partir de los logs ya versionados. Solo lee
`resultados/raw/<id>-ping.log` y `<id>-eventos.log`; no modifica simulaciones,
configuraciones, PCAP ni resultados crudos.

## Criterio unico

La indisponibilidad es el intervalo entre dos respuestas ICMP validas:

1. **Inicio:** la ultima respuesta antes de la primera evidencia de perdida
   posterior a la suspension de `R2-R4`. La perdida se identifica por una linea
   `From` de `ping`; si no la hay, por un hueco de al menos 1 s entre respuestas
   alrededor del evento.
2. **Fin:** la primera de cinco respuestas exitosas con `icmp_seq` consecutivos,
   posteriores a la ultima evidencia de perdida.

La regla no cuenta desde la orden de suspender el enlace: si todavia llegan
respuestas por paquetes en transito, el servicio sigue disponible. Tampoco
confunde un unico ping tardio con recuperacion, porque exige cinco respuestas
consecutivas.

Ejecutar desde `tp-final`:

```bash
python3 docs/indisponibilidad.py .
```

## Resultados

| Esquema | r01 | r02 | r03 | r04 | r05 | Mediana | Rango |
|---|---:|---:|---:|---:|---:|---:|---:|
| Estatico | 27,347 s | 23,414 s | 26,334 s | 29,310 s | 27,880 s | 27,347 s | 23,414--29,310 s |
| RIP | 12,963 s | 29,183 s | 14,611 s | 26,481 s | 12,306 s | 14,611 s | 12,306--29,183 s |
| OSPF | 0,177 s | 0,170 s | 2,047 s | 0,198 s | 3,390 s | 0,198 s | 0,170--3,390 s |

Los valores de estatica reproducen la mediana publicada de `27,347 s`. Los
valores anteriores de OSPF, incluida la mediana `2,381 s`, usaban otra metrica:
contaban cinco lineas de salida de `ping` desde el evento de suspension, incluso
cuando esas lineas incluian errores `From` o cuando el servicio todavia
respondia. Los valores generados por este script son comparables entre esquemas
como interrupcion observada por ICMP, pero no miden la convergencia del plano de
control. Esa medicion requiere los logs de rutas R1-R5 agregados para las nuevas
corridas en `RELEVO_REFUERZO_SIMULACIONES.md`.

## Archivos

- `indisponibilidad.py`: lector y calculador sin dependencias externas.
- `../simulacion/escenarios/<esquema>/resultados/raw/*-ping.log`: respuestas
  ICMP con timestamp.
- `../simulacion/escenarios/<esquema>/resultados/raw/*-eventos.log`: instante
  de suspension de `R2-R4`.
