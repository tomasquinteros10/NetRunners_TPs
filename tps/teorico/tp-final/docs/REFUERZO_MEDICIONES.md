# Refuerzo De Mediciones

Las corridas originales no se modifican. Las nuevas filas de la matriz usan IDs
distintos y solo se ejecutan si sus artefactos finales y temporales no existen.

## Datos Nuevos

- Las pruebas de carga guardan `resultados/raw/<id>-ping.log` con RTT ICMP
  durante toda la ejecución.
- La serie `tcp-iperf3-slow-start` usa `iperf3` sin `-O`, para conservar los
  intervalos iniciales y `snd_cwnd`.
- Las fallas guardan `resultados/raw/<id>-R1-ruta.log` hasta
  `resultados/raw/<id>-R5-ruta.log`, con muestras de rutas activas cada 200 ms.

## Preparación Y Ejecución

La primera ejecución del metascript agrega 80 filas pendientes a la matriz:
60 repeticiones de carga con RTT, 5 pruebas de arranque lento y 15 fallas con
rutas monitoreadas. No reutiliza IDs ni sobrescribe filas completas.

Ejecutar un esquema activo a la vez:

```bash
simulacion/scripts/ejecutar_refuerzo.sh estatico
simulacion/scripts/ejecutar_refuerzo.sh rip
simulacion/scripts/ejecutar_refuerzo.sh ospf
```

Antes de cada invocación, configurar manualmente el esquema indicado en GNS3,
iniciar los siete nodos y verificar que `R2-R4` esté restaurado. El metascript
solicita confirmación y aborta la ejecución si esta no se proporciona.

Para validar el plan sin modificar la matriz ni ejecutar ensayos:

```bash
simulacion/scripts/ejecutar_refuerzo.sh --dry-run estatico
```

Los monitores de rutas usan las consolas Telnet locales de GNS3 en modo de solo
lectura. No escriben configuraciones RouterOS ni usan o registran credenciales.
