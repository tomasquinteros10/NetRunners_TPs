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
