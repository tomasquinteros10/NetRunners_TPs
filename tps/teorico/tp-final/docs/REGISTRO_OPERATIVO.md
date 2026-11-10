# Registro Operativo De La Simulacion

Este archivo preserva procedimientos de consola y validaciones reproducibles.
No incluir credenciales, hashes, licencias ni IDs locales.

## Validacion De Respaldo RIP

Fecha: 2026-11-08.

Objetivo: demostrar que, con `R2-R4` suspendido, un paquete ICMP atraviesa el
enlace de respaldo R5-R4.

Procedimiento temporal en R5:

```routeros
/ip firewall mangle add chain=forward protocol=icmp out-interface=ether3 action=passthrough comment=validacion-icmp-salida-R5-R4
/ip firewall mangle add chain=forward protocol=icmp in-interface=ether3 action=passthrough comment=validacion-icmp-entrada-R5-R4
/ip firewall mangle reset-counters [find comment~"validacion-icmp"]
```

Con `R2-R4` suspendido durante 45 s, se ejecuto un unico ping desde cliente a
servidor. El resultado fue una respuesta con TTL 60. En R5:

```routeros
/ip firewall mangle print stats where comment~"validacion-icmp"
```

La salida registro exactamente un paquete ICMP saliendo por `ether3` y uno
entrando por esa interfaz. Se restauró R2-R4 y se revirtieron las reglas:

```routeros
/ip firewall mangle remove [find comment~"validacion-icmp"]
```

Esto valida `R1-R3-R5-R4` durante la falla. Las reglas no son parte del
escenario RIP persistente.

## Validacion De PCAP

Antes de concluir que falta trafico, ejecutar:

```bash
tshark -r <pcap> -q -z io,phs
```

Resultado ya validado: `rip-falla-r01-R5-R4.pcap` contiene 13.008 tramas,
6.031 ICMP, 6.867 TCP y 23 RIP. No usar un filtro que no devuelva filas como
prueba de ausencia de trafico sin contrastarlo con estas estadisticas.

## Prevalidacion Para OSPF

Fecha: 2026-11-08.

Objetivo: confirmar el protocolo activo antes de reemplazar RIPv2 por OSPF,
sin ejecutar una corrida formal.

En R1-R4 se consultaron los siguientes comandos:

```routeros
/routing rip instance print detail
/routing ospf instance print detail
/ip route print where dst-address=10.10.4.0/24
```

R1, R2 y R3 mostraron la instancia `rip-v2`, OSPF sin instancias y rutas RIP
activas hacia `10.10.4.0/24`. R4 mostró `rip-v2`, OSPF sin instancias y la red
del servidor como conectada. No se modificaron protocolos, rutas, colas ni
enlaces.

La sesion de consola se cerro al terminar la consulta; esto no cambia la
configuracion persistente ni el estado de los enlaces. Antes de aplicar OSPF,
se debe volver a iniciar sesion en las consolas de R1-R5.

## Configuracion Y Validacion Piloto OSPF

Fecha: 2026-11-08.

Objetivo: reemplazar RIPv2 por OSPF en area 0, preferir `R1-R2-R4` mediante
costos explicitos y comprobar una unica conmutacion sin ejecutar una corrida
formal.

En cada router se agregaron la instancia `ospf-v2`, el area `backbone` con
`area-id=0.0.0.0` y las plantillas de interfaz registradas en
`escenarios/ospf/config/R1.rsc` a `R5.rsc`. Los enlaces del primario usan costo
10; los cuatro enlaces del respaldo usan costo 20. Las LAN se anuncian con
`redistribute=connected`. Luego de observar adyacencias OSPF `Full`, se
eliminaron las instancias y plantillas RIP.

Validacion normal: R1 instaló la ruta OSPF a `10.10.4.0/24` por
`10.10.12.2%ether3`, y cliente-servidor respondió 3 de 3 pings.

Validacion temporal: se suspendió por la API de GNS3 el enlace `R2:e2-R4:e1`.
El segundo intento ICMP respondió con TTL 60; R1 instaló la ruta OSPF por
`10.10.13.2%ether4`, que corresponde a `R1-R3-R5-R4`. El enlace se restauró
mediante una rutina de limpieza aun ante error. Después de la reelección OSPF,
R1 volvió a `10.10.12.2%ether3` y mantuvo las dos adyacencias `Full`.

No se generaron capturas, archivos de resultados ni filas de matriz: esta fue
solamente una prueba piloto de configuración y conmutación.

## Piloto Corto De Convergencia OSPF

Fecha: 2026-11-08.

Objetivo: confirmar que los componentes del ensayo formal OSPF funcionan sin
consumir la corrida de 300 s ni modificar la matriz.

Se validaron ICMP y HTTP entre cliente y servidor, se ejecutó ping continuo y
se suspendió `R2:e2-R4:e1` durante 10 s. Durante el corte, R1 instaló la ruta
OSPF por `10.10.13.2%ether4`; tras restaurar el enlace, las dos adyacencias de
R1 volvieron a `Full` y la ruta regresó a `10.10.12.2%ether3`. HTTP respondió
antes y después del corte. La limpieza restauró el enlace incluso ante error.

El log efímero se conservó solo en `/tmp`; no se generaron PCAP, resultados ni
artefactos de la fila `ospf-falla-r01`.

## Corrida Formal OSPF R01

Fecha: 2026-11-09.

Objetivo: primera repetición formal de convergencia OSPF, con la misma
duración y artefactos que las corridas estática y RIP.

`ospf-falla-r01` finalizó con ping, HTTP, eventos y capturas de R2-R4 y R5-R4.
El enlace se suspendió a los 20 s y se restauró 61 s después. `wrk` terminó
sus 5 minutos con 92 solicitudes, `0.31` solicitudes/s y `79.34 KB/s`, sin
líneas de error ni timeout.

La correlación de eventos, ping y PCAP confirmó la conmutación: durante la
ventana de falla R5-R4 registró 1.173 paquetes ICMP, mientras R2-R4 registró
19 paquetes residuales al inicio del corte. El mayor intervalo ICMP en torno a
la falla fue 0,834 s; cinco respuestas consecutivas se completaron 1,753 s
después de la última respuesta previa al evento. La ruta retornó al primario
después de restaurar el enlace.

## Serie Formal OSPF Completa

Fecha: 2026-11-09.

Las cinco repeticiones `ospf-falla-r01` a `ospf-falla-r05` finalizaron con sus
cinco artefactos cada una. Las capturas de respaldo contienen OSPF, ICMP y
TCP/HTTP durante la falla, y todos los resúmenes de `wrk` terminaron sin
errores ni timeouts. La mediana de recuperación de cinco respuestas ICMP fue
2,381 s; las cinco mediciones fueron 1,753, 3,135, 2,448, 2,381 y 1,833 s.
La mediana HTTP fue 0,30 solicitudes/s y 78,47 KB/s. Tras la serie, R1 volvió
a la ruta OSPF primaria por `10.10.12.2%ether3`.

## Cierre De Sesion

Fecha: 2026-11-09.

Se reemplazaron los ZIP de capturas por 102 PCAP individuales y se conservaron
los logs y resultados como archivos planos. El cambio, la configuración OSPF,
las cinco corridas y su evidencia se publicaron en `tp-final` con el commit
`c5d9df0` (`feat: agregar OSPF y capturas directas`).

Al reanudar, verificar primero que R1 conserve la ruta OSPF primaria por
`10.10.12.2%ether3` y leer `AGENT.md` antes de ejecutar cambios. No hay
corridas de convergencia pendientes.

## Pausa Temporal Para Captura De Topologia

Fecha: 2026-11-09.

Objetivo: obtener una captura visual de la topologia con la falla del enlace
primario R2-R4 representada en GNS3. No es una corrida formal ni genera
artefactos de resultados.

Inicialmente se suspendió por error `R1:e2-R2:e1`; se restauró de inmediato
por API y se verificó `suspend=false`. Luego se suspendió el enlace correcto
`R2:e2-R4:e1`, con `suspend=true` confirmado por consulta a la API. También se
inició una captura temporal en `R5:e2-R4:e2`, almacenada por GNS3 bajo
`project-files/captures/topologia-falla-R5-R4.pcap`.

No se modificaron configuraciones RouterOS, colas, rutas, matriz ni resultados
formales. La captura temporal no debe tratarse como evidencia de una corrida.

La reversion exacta, cuando termine la captura, es actualizar ese mismo enlace
por API con el cuerpo JSON `{"suspend":false}` y verificar `suspend=false`.

Al finalizar la captura, se detuvo la escucha en `R5:e2-R4:e2` y se restauró
`R2:e2-R4:e1`. Una consulta posterior confirmó ambos enlaces con
`suspend=false` y sin captura activa.

## Incidentes Conservados Como Diagnostico

Los siguientes intentos no forman parte de las filas formales de la matriz y
sus artefactos se conservaron bajo `simulacion/escenarios/*/{resultados,capturas}/diagnostico/`:

- La primera HTTP estática no tenía cuello inverso; se agregó en R4 el marcado
  `forward` de salida por `ether2` y la cola `cuello-R4-R2` a `500k`.
- Dos intentos HTTP+UDP no generaban competencia real: el UDP circulaba en el
  sentido opuesto y luego se ubicó `-R` en el ejecutor TCP+UDP por error. Se
  corrigió el ejecutor HTTP+UDP para usar UDP inverso, que comparte el cuello
  R4-R2 con las respuestas HTTP.
- Las cinco repeticiones HTTP+UDP con `wrk --timeout 10s` registraron
  timeouts. Se conservaron como diagnostico y se repitieron con `--timeout
  30s`; las filas formales vigentes son las repeticiones sin timeout.
- El primer intento de `estatico-falla-r05` fue interrumpido antes de archivar
  PCAP. Sus logs quedaron como diagnostico y la repetición posterior es la que
  figura en la matriz.
- En RIP, `rip-falla-r01` no produjo el resumen de `wrk` y `rip-falla-r02`
  pertenecía a una serie repetida. Ambos conjuntos se archivaron como
  diagnostico antes de registrar las corridas válidas.
- La mediana OSPF antes informada como `2,381 s` no medía indisponibilidad:
  contaba cinco líneas de salida de `ping` desde la suspensión, incluidas
  respuestas `From` y respuestas que aún indicaban servicio disponible. El
  criterio se corrigió en `docs/indisponibilidad.py`, que exige la primera de
  cinco respuestas ICMP consecutivas posterior a la última evidencia de
  pérdida. `docs/README.md` conserva los resultados recalculados de los tres
  esquemas.

Estos incidentes están resumidos también en `AGENT.md`; no deben reutilizarse
como evidencia cuantitativa.

## Retorno Temporal A Rutas Estaticas Para Refuerzo

Fecha: 2026-11-09.

Objetivo: preparar los tres pilotos de refuerzo estáticos, que agregan RTT,
slow start y observación de rutas sin alterar las corridas formales previas.

En R1-R5 se agregaron las rutas del export versionado en
`simulacion/escenarios/estatico/config/`. En R1 se instalaron `primaria-R2`,
`respaldo-R3-R5` y `monitor-R4-via-R2`; en R4, `primaria-R2`,
`respaldo-R5-R3` y `retorno-monitor-R1`; R2, R3 y R5 recibieron sus rutas
estáticas de tránsito correspondientes. Luego, en cada router se ejecutó:

```routeros
/routing ospf interface-template remove [find]
/routing ospf area remove [find]
/routing ospf instance remove [find]
```

Las rutas primarias activas se verificaron en R1 hacia `10.10.4.0/24` por
`10.10.24.2` (resuelto por R2) y en R4 hacia `10.10.1.0/24` por `10.10.24.1`.
Cliente-servidor respondió 3 de 3 ICMP y HTTP. No se modificaron direcciones,
colas ni reglas mangle: los cuellos existentes de R2 a R4 y de R4 a R2 siguen
limitados a `500k`.

La reversión, si se necesita retomar OSPF, es reaplicar exclusivamente las
instancias, áreas y plantillas de
`simulacion/escenarios/ospf/config/R1.rsc` a `R5.rsc`, y retirar las rutas
estáticas agregadas en esta operación.

## Piloto UDP De Refuerzo Abortado

Fecha: 2026-11-09.

Se inició `estatico-udp-100k-r01-rtt`, pero la ejecución fue cancelada antes
de finalizar. No quedaron JSON, log de ping, PCAP ni temporales para ese ID, y
la fila de matriz permanece pendiente. La rutina de limpieza del ejecutor
detuvo la sonda ICMP y la captura; el ID puede ejecutarse nuevamente sin
sobrescribir evidencia.

## Pilotos Estaticos De Refuerzo

Fecha: 2026-11-09.

Se ejecutaron y aprobaron los tres pilotos requeridos antes de iniciar la
serie de refuerzo:

- `estatico-udp-100k-r01-rtt`: 60 intervalos de `iperf3`, ping con timestamps
  durante 61,023 s y PCAP con datos UDP/iperf3.
- `estatico-tcp-slow-start-r01`: 300 intervalos de 0,2 s sin `-O`, cada uno
  con `snd_cwnd`; ping durante 61,121 s y PCAP con datos TCP/iperf3.
- `estatico-falla-r01-rutas`: ping, HTTP, eventos, dos PCAP y cinco logs de
  rutas. Cada router produjo al menos 1.488 muestras antes, durante y después
  de la suspensión de R2-R4. La API confirmó al final que el enlace quedó con
  `suspend=false`.

Los logs de rutas permitieron medir el plano de control sin inferirlo desde
ping: R4 observó el respaldo a los 1,045 s y R1 a los 25,131 s luego de la
suspensión. Por el intervalo de muestreo, la convergencia bidireccional de
reenvío quedó acotada entre 24,928 y 25,131 s. Esta métrica es independiente
de la recuperación de servicio observada por ICMP.

## Serie Estatica De Refuerzo

Fecha: 2026-11-09.

Después de aprobar los pilotos, finalizaron las 70 corridas estáticas de
refuerzo: 60 ensayos de carga con RTT, cinco TCP de slow-start y cinco fallas
con logs de rutas. Una cancelación inicial dejó un JSON vacío y un log de ping
parcial para `estatico-udp-100k-r02-rtt`; ambos se preservaron bajo
`resultados/diagnostico/` y el ID se ejecutó posteriormente como una corrida
nueva y completa. Las sondas ICMP huérfanas de esa cancelación se terminaron
antes de iniciar la serie, para no contaminar mediciones posteriores.

`simulacion/scripts/validar_refuerzo.py . estatico` aprobó las 70 filas. El
validador comprueba artefactos listados por matriz, JSON, legibilidad de PCAP,
cobertura temporal del ping, `snd_cwnd` de slow-start, eventos y rutas de
respaldo de las fallas. La cobertura de ping se valida por duración observada,
no por una cantidad fija de respuestas: bajo congestión, la pérdida es un
resultado válido y no una razón para descartar una sonda que cubrió la ventana
del ensayo.

## Refuerzo RIP Y OSPF

Fecha: 2026-11-09.

Objetivo: completar las diez fallas instrumentadas pendientes y observar el
cambio de las rutas activas de R1 a R5, sin modificar direccionamiento ni los
dos cuellos de 500 kbit/s.

Para pasar de estáticas a RIP se ejecutó en R1-R5:

```routeros
/ip route remove [find where comment~"primaria|respaldo|monitor|hacia|retorno"]
/routing rip instance add name=rip-v2 redistribute=connected
/routing rip interface-template add instance=rip-v2 interfaces=<interfaces-del-router>
```

R2, R3 y R5 incluyeron `redistribute=connected,rip`; R1 y R4 mantuvieron
`redistribute=connected`. Se validó R1 por `10.10.12.2%ether3`, R4 por
`10.10.24.1%ether2`, ICMP/HTTP extremo a extremo y, en un piloto de 45 s con
R2-R4 suspendido, R1 por `10.10.13.2%ether4`, con ping TTL 60. El enlace fue
restaurado antes de la serie. Las cinco filas `rip-falla-r01-rutas` a `r05-rutas`
se validaron; los PCAP de respaldo contienen RIP, ICMP y TCP/HTTP.

Para pasar de RIP a OSPF se ejecutó en R1-R5:

```routeros
/routing rip interface-template remove [find]
/routing rip instance remove [find]
/routing ospf instance add name=ospf-v2 redistribute=connected router-id=<id-del-router>
/routing ospf area add area-id=0.0.0.0 instance=ospf-v2 name=backbone
/routing ospf interface-template add area=backbone cost=<10-o-20> interfaces=<interfaz>
```

Los costos aplicados son los exports de `escenarios/ospf/config/`: 10 en el
primario R1-R2-R4 y 20 por enlace del respaldo. Las adyacencias relevantes de
R1 llegaron a `Full`; R1 y R4 se validaron por el primario antes de un piloto
de 15 s, que confirmó el respaldo y TTL 60. Un primer conjunto de cinco
corridas arrancó todavía por respaldo tras ese piloto; se archivó como
diagnóstico bajo `ospf-rutas-inicio-en-respaldo`, se liberaron sus filas y se
repitió la serie solamente después de confirmar ambos gateways primarios.

Las cinco corridas OSPF repetidas fueron aprobadas por
`python3 simulacion/scripts/validar_refuerzo.py . ospf`. La validación ahora
exige una muestra primaria anterior a la suspensión para RIP y OSPF. También
se corrigió `procesar_convergencia.py` para comparar el gateway sin el sufijo
`%interfaz` de RouterOS. Las diez mediciones instrumentadas se procesaron y
los derivados se regeneraron con:

```bash
python3 simulacion/scripts/procesar_resultados.py .
```

El estado persistente final es OSPF, sin RIP ni rutas estáticas de tránsito,
R2-R4 restaurado y sin capturas activas. Los exports sin secretos de ambos
escenarios ya corresponden a las configuraciones aplicadas.
