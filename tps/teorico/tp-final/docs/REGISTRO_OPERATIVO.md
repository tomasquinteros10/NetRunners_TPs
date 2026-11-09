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
