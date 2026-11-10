# Relevo: Refuerzo De Simulaciones

## Objetivo

Completar los datos que faltaban para respaldar el informe sin modificar ni
sobrescribir los 75 ensayos ya registrados:

- RTT ICMP durante las pruebas de carga.
- Una serie TCP sin periodo omitido para observar el inicio de conexion y
  `snd_cwnd`.
- Estado de las rutas activas durante las fallas, para distinguir recuperacion
  del servicio de convergencia del encaminamiento.

## Estado Actual

Se aprobaron y completaron las series de refuerzo estática, RIP y OSPF.

La matriz `simulacion/experimentos/matriz.csv` contiene 80 filas nuevas:

- 60 repeticiones de carga estatica con sufijo `-rtt`.
- 5 ensayos `estatico-tcp-slow-start-r01` a `r05`.
- 15 ensayos de falla con sufijo `-rutas`: cinco para estatica, RIP y OSPF.

Las 80 filas de refuerzo están completas: 60 de carga estática con RTT,
cinco ensayos TCP de slow-start y 15 ensayos de falla con rutas (cinco por
esquema: estática, RIP y OSPF).

Las filas originales y sus artefactos no fueron modificados.

## Relacion Con La Monografia

La necesidad de este refuerzo sale de lo que la monografia ya promete medir:

- En `entrega/monografia.tex:84`, los objetivos especificos incluyen perdida,
  latencia, retransmisiones y variaciones en el rendimiento.
- La Tabla 4, en `entrega/monografia.tex:397-403`, establece las fuentes de
  medicion para throughput TCP, throughput/jitter/perdida UDP, latencia por
  `ping` (RTT), arranque lento y caida de `cwnd`, y tiempo de convergencia.
- El texto sobre pruebas de carga, en `entrega/monografia.tex:355`, indica que
  se analizaran perdida, retardo, retransmisiones y rendimiento a medida que
  aumenta la carga.

Por lo tanto, las nuevas corridas existen para que las afirmaciones sobre RTT,
`cwnd` y convergencia tengan un artefacto directo, reproducible y asociado a
la misma ventana temporal del ensayo que se presenta en el informe.

## Faltantes De Las Simulaciones Anteriores

Las simulaciones anteriores son validas para throughput, perdida, jitter UDP,
retransmisiones TCP, resultados de `wrk` e indisponibilidad del servicio ante
una falla. Sin embargo, no alcanzan para respaldar tres afirmaciones de forma
directa:

1. **RTT durante congesti\'on.** Los ejecutores anteriores hacian tres `ping`
   previos solo para validar conectividad y redirigian su salida a `/dev/null`.
   La captura PCAP comenzaba despues de esa validacion. Por eso no quedo una
   serie de RTT ICMP que pueda correlacionarse con la carga ofrecida.

2. **Arranque lento y evolucion inicial de `cwnd`.** La serie TCP de referencia
   usa `iperf3 -O 10`, que omite los primeros diez segundos del resumen. Sus
   resultados sirven para capacidad estable, pero no para presentar el inicio
   de la conexion como una medicion dedicada.

3. **Convergencia interna del encaminamiento.** Las fallas anteriores guardan
   eventos, PCAP y `ping` continuo. Eso permite medir indisponibilidad de
   servicio, pero no el instante preciso en que cada router cambia su ruta
   activa. Inferir la convergencia a partir de que vuelve el `ping` confunde el
   plano de datos con el plano de control.

Las nuevas corridas no reemplazan las anteriores: agregan instrumentacion que
debe estar activa durante todo el ensayo. Como el `ping` de RTT introduce una
carga pequena pero no nula y los nuevos artefactos dependen de la ejecucion,
no es riguroso adjuntarlos a las corridas viejas ni mezclar sus mediciones.

## Validacion Para No Repetir El Error

Antes de ejecutar una serie completa, los tres pilotos obligatorios deben
producir todos los artefactos esperados y estos deben revisarse antes de seguir:

- El piloto UDP debe contener un `ping.log` con timestamps que cubran la misma
  ventana temporal que el JSON de `iperf3` y el PCAP. No alcanza con que exista
  un ping previo de conectividad.
- El piloto TCP de arranque lento debe contener intervalos iniciales en el JSON
  y valores de `snd_cwnd`; no debe haber un periodo omitido por `-O`.
- El piloto de falla debe contener cinco logs de rutas no vacios, uno por R1 a
  R5, con muestras anteriores, durante y posteriores a la suspension de
  `R2-R4`. Tambien se debe comprobar que el enlace termine restaurado.

Si cualquiera de esas condiciones falla, detenerse, conservar los temporales
para diagnostico sin sobrescribir nada y corregir el ejecutor antes de iniciar
la serie restante.

## Metricas De Convergencia

No usar solo el ping para afirmar cuanto tarda en converger el encaminamiento.
El ping mide el plano de datos desde el cliente y queda limitado por su periodo
de sondeo; el cambio de ruta debe salir de los cinco logs de rutas.

- **Convergencia de reenvio observada:** para cada repeticion, medir desde el
  evento `enlace-R2-R4-suspendido` hasta la ultima de estas dos primeras
  muestras de respaldo: R1 hacia `10.10.4.0/24` por gateway `10.10.13.2` y R4
  hacia `10.10.1.0/24` por gateway `10.10.45.1`. Es una medicion directa del
  instante en que ambos extremos instalan el camino alternativo.
- **Recuperacion de servicio observada:** conservar por separado el intervalo
  ICMP entre la ultima respuesta previa a la perdida y la primera de cinco
  respuestas consecutivas posteriores. No llamarlo tiempo de convergencia.

Las muestras de rutas tienen una resolucion de 200 ms mas el tiempo de consulta
de consola; informar el valor como observacion con esa resolucion, no como un
instante exacto. R2, R3 y R5 se conservan para explicar la propagacion del
cambio y diagnosticar asimetrias, pero la metrica de reenvio extremo a extremo
queda definida por R1 y R4.

`simulacion/scripts/procesar_convergencia.py` informa la cota inferior y
superior observadas: para cada extremo, el cambio real cae entre la ultima
muestra que no era de respaldo y la primera que ya lo es. La cota conjunta usa
el maximo de ambas, porque el servicio bidireccional requiere que R1 y R4 hayan
instalado el respaldo.

## Scripts Agregados O Modificados

- `simulacion/scripts/ejecutar_trafico.sh`
  - Guarda `resultados/raw/<id>-ping.log` con `ping -D -i 0.2` durante cada
    nueva prueba de carga.
  - Mantiene la captura PCAP y los resultados habituales.
  - Soporta el tipo interno `tcp-iperf3-slow-start`, ejecutado sin `-O 10` y
    con intervalos de 0.2 s.

- `simulacion/scripts/ejecutar_tcp_slow_start.sh`
  - Invoca el ejecutor de trafico con el tipo TCP de arranque lento.

- `simulacion/scripts/monitor_rutas.py`
  - Consulta por Telnet, en modo de solo lectura, la ruta activa relevante de
    cada CHR cada 200 ms y elimina los codigos de color de la consola para que
    los gateways y flags queden parseables.
  - No usa ni guarda credenciales. Las consolas locales de este proyecto ya
    exponen un prompt RouterOS autenticado.

- `simulacion/scripts/ejecutar_convergencia.sh`
  - Durante cada falla nueva inicia cinco monitores: R1, R2, R3, R4 y R5.
  - R1, R2 y R3 registran la ruta hacia `10.10.4.0/24`; R4 y R5, la ruta hacia
    `10.10.1.0/24`. Asi se observa el reenvio relevante en ambos sentidos.
  - Guarda `resultados/raw/<id>-R1-ruta.log` hasta
    `resultados/raw/<id>-R5-ruta.log`, ademas de ping, HTTP, eventos y los dos
    PCAP existentes.

- `simulacion/scripts/procesar_convergencia.py`
  - Calcula las cotas de convergencia de reenvio a partir de evento y logs de
    R1/R4, sin modificar resultados crudos.

- `simulacion/scripts/preparar_refuerzo.py`
  - Genera las 80 filas de manera idempotente; ya fue ejecutado.
  - No reutiliza IDs ni modifica filas ya completas.

- `simulacion/scripts/ejecutar_refuerzo.sh`
  - Metascript por esquema. Ejecuta solo filas pendientes, agrupa por tipo y
    solicita confirmacion de que GNS3 tiene el esquema correcto activo.
  - No cambia configuraciones RouterOS ni cambia automaticamente entre
    estatica, RIP u OSPF.

## Validaciones Ya Realizadas

- `bash -n` paso para todos los scripts Bash nuevos o modificados.
- `python3 -m py_compile` paso para `monitor_rutas.py` y
  `preparar_refuerzo.py`.
- El monitor Telnet se probó con R1, R2, R3, R4 y R5, generando archivos no
  vacios de prueba fuera del repositorio.
- El metascript pasó `--dry-run` para estatica, RIP y OSPF.
- Las consultas manuales confirmaron, bajo OSPF, que R1 tiene como ruta activa
  hacia `10.10.4.0/24` a `10.10.12.2%ether3`, y R4 hacia `10.10.1.0/24` a
  `10.10.24.1%ether2`.
- El piloto UDP produjo 60 intervalos de `iperf3`, un ping de 61,023 s que
  cubre su ventana de 60 s y un PCAP con 625 tramas de datos `iperf3`.
- El piloto TCP produjo 300 intervalos de 0,2 s desde el inicio, con
  `snd_cwnd` en todos ellos, ping de 61,121 s y PCAP con tráfico TCP/iperf3.
- El piloto de falla produjo 1.488 o 1.489 muestras de ruta por router,
  anteriores, durante y posteriores a la falla. Las capturas R2-R4 y R5-R4
  contienen ICMP, TCP y HTTP, y la API confirmó `R2-R4 suspend=false` al
  finalizar. La convergencia de reenvío estática se acotó entre 24,928 y
  25,131 s; R1 fue el último extremo en observar el respaldo.
- La validación agregada `simulacion/scripts/validar_refuerzo.py . estatico`
  aprobó las 70 filas estáticas: matriz completa, artefactos no vacíos, JSON
  parseables, PCAP legibles, ventanas de ping cubiertas, `snd_cwnd` en
  slow-start y rutas/eventos de las cinco fallas.

## Pilotos Obligatorios

No ejecutar la serie completa sin validar primero, con el esquema estatico
activo, los siguientes tres ensayos:

```bash
simulacion/scripts/ejecutar_udp.sh estatico-udp-100k-r01-rtt
simulacion/scripts/ejecutar_tcp_slow_start.sh estatico-tcp-slow-start-r01
simulacion/scripts/ejecutar_convergencia.sh estatico-falla-r01-rutas
```

Antes de cada piloto confirmar que:

- Los siete nodos estan iniciados.
- Cliente y servidor tienen conectividad.
- Nginx responde.
- El enlace `R2-R4` esta restaurado.

Despues del piloto UDP deben existir y no estar vacios:

```text
resultados/raw/estatico-udp-100k-r01-rtt.json
resultados/raw/estatico-udp-100k-r01-rtt-ping.log
capturas/estatico-udp-100k-r01-rtt-R2-R4.pcap
```

Despues del piloto TCP deben existir JSON, log de ping y PCAP con el ID
`estatico-tcp-slow-start-r01`. Verificar que el JSON incluya intervalos
iniciales y `snd_cwnd`, sin periodo `-O`.

Despues del piloto de falla deben existir los artefactos habituales y cinco
logs de rutas no vacios, uno por router. Verificar muestras antes, durante y
despues de la falla, y que `R2-R4` haya quedado restaurado.

## Ejecucion Completa

Solo despues de aprobar los pilotos:

```bash
simulacion/scripts/ejecutar_refuerzo.sh estatico
simulacion/scripts/ejecutar_refuerzo.sh rip
simulacion/scripts/ejecutar_refuerzo.sh ospf
```

Entre comandos, reconfigurar manualmente el esquema en GNS3 y validar el
estado base. El metascript omite pilotos ya completados y aborta si encuentra
artefactos existentes para una fila pendiente; nunca debe borrar ni reemplazar
artefactos.

## Restricciones

- No leer, mostrar ni modificar `.env` ni credenciales.
- No sobrescribir ni borrar resultados, PCAP ni filas existentes.
- Mantener separadas las pruebas de congestión (estatica) y las de
  convergencia (estatica, RIP, OSPF).
- Registrar cualquier operacion RouterOS nueva en `docs/REGISTRO_OPERATIVO.md`.
