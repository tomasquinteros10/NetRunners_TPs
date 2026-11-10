# Contexto de Simulacion TP Final

Leer este archivo al retomar trabajo en `simulacion/`. No reemplaza el
procedimiento completo: para los pasos y checks, leer primero
[`docs/HOJA_DE_RUTA.md`](docs/HOJA_DE_RUTA.md).

## Objetivo

Construir un laboratorio reproducible en GNS3 para el informe
`entrega/monografia.tex`. Debe comparar congestion bajo carga TCP/UDP y la
conmutacion ante falla con rutas estaticas, RIPv2 y OSPF.

Decision experimental clave: RIP y OSPF no deben presentarse como protocolos
que desvien trafico por congestion mientras un enlace sigue activo. La carga
sostenida y la convergencia ante la falla del enlace son ensayos separados.

## Estado Al Pausar

La seccion 1.4 de `HOJA_DE_RUTA.md` esta completada para la instancia de
prueba CHR y los endpoints Docker. No avanzar a la topologia completa ni a la
configuracion de rutas sin que el usuario lo pida.

GNS3 guarda el proyecto actual en:

```text
simulacion/topologia/tp-final-congestion-routing/tp-final-congestion-routing.gns3
```

El proyecto contiene una unica instancia de prueba:

```text
MikroTik-CHR-7.24.6-1
```

Propiedades verificadas de esa instancia:

- QEMU local y consola Telnet.
- Imagen base `chr-7.24.6.img`.
- 1 CPU, 512 MB de RAM y clon enlazado.
- Cuatro interfaces `virtio-net-pci`: RouterOS las expone como `ether1` a
  `ether4`.
- RouterOS `7.24.6 (long-term)` y licencia CHR `free`.

La instancia inicio correctamente despues de reiniciar la sesion grafica para
que GNS3 heredara los permisos de `ubridge`.

Los endpoints usan la imagen local `netrunners-endpoint:1.0`, construida desde
`simulacion/endpoint/Dockerfile`. Incluye `iperf3`, `iputils-ping` e `iproute2`; se
verifico que `iperf3 --version`, `ping -V` e `ip -V` funcionan en contenedores
efimeros.

## Archivos y Secretos

- `docs/HOJA_DE_RUTA.md`: procedimiento, checks y comandos manuales.
- `simulacion/topologia/tp-final-congestion-routing/.env.example`: variables
  de referencia para credenciales locales.
- `simulacion/topologia/tp-final-congestion-routing/.gitignore`: excluye
  `.env` y conserva `.env.example`.
- `simulacion/topologia/tp-final-congestion-routing/.env`: archivo local
  creado por el usuario; no leerlo, mostrarlo, editarlo
  ni agregarlo a Git. RouterOS ya tiene una contrasena de laboratorio definida
  manualmente en la consola.

No versionar la imagen CHR, discos QEMU, snapshots, archivos temporales ni
capturas grandes. No registrar contrasenas, claves, identificadores de licencia
ni datos propios de una instancia. El hash de una imagen publica se documenta
segun `docs/HOJA_DE_RUTA.md` para verificar que todos usen el mismo archivo.

## Reanudacion Segura

1. Leer `docs/HOJA_DE_RUTA.md` y este archivo.
2. Inspeccionar `simulacion/topologia/` antes de editar el `.gns3`; puede haber cambios
   manuales recientes en GNS3.
3. Si se necesita verificar CHR, usar solamente:

   ```routeros
   /system resource print
   /system license print
   /interface ethernet print
   ```

4. Antes de cambios sustanciales, confirmar con el usuario cual es el paso
   actual de la hoja de ruta.
5. Mantener la topologia y configuraciones en el repositorio; la plantilla y
   la imagen base son dependencias locales que cada integrante instala.

## Proximo Hito

La topologia en diamante asimetrico ya esta creada manualmente con cinco CHR y
los endpoints `cliente` y `servidor`; sus enlaces estan activos. El camino
primario es `R1-R2-R4` y el respaldo `R1-R3-R5-R4`, para que RIPv2 prefiera el
primero por tener menos saltos. Descubrimiento importante: en este proyecto,
los adaptadores GNS3 `e1`, `e2` y `e3` de los CHR son `ether2`, `ether3` y
`ether4` en RouterOS; `ether1` no tiene enlace. Todas las direcciones de los
routers fueron configuradas inicialmente desplazadas una interfaz. R1 ya fue
realineado: `10.10.1.1/24` en `ether2`, `10.10.12.1/30` en `ether3` y
`10.10.13.1/30` en `ether4`. R2 ya fue realineado: `10.10.12.2/30` en
`ether2` y `10.10.24.1/30` en `ether3`. R3 ya fue realineado:
`10.10.13.2/30` en `ether2` y `10.10.35.1/30` en `ether3`. R5 ya fue
realineado: `10.10.35.2/30` en `ether2` y `10.10.45.1/30` en `ether3`.
R4 fue realineado: `10.10.24.2/30` en `ether2`, `10.10.45.2/30` en
`ether3` y `10.10.4.1/24` en `ether4`. El endpoint `cliente` ya tiene
`10.10.1.10/24` en `eth0` y puerta de enlace `10.10.1.1`. Todos los enlaces
entre routers y el enlace cliente-R1 fueron validados por ping directo.
El endpoint `servidor` tiene `10.10.4.10/24` en `eth0` y puerta de enlace
`10.10.4.1` validada. El direccionamiento base completo y todos los enlaces
directamente conectados fueron validados por ping.
El endpoint `cliente` tiene `10.10.1.10/24` en `eth0`, puerta de enlace
`10.10.1.1` verificada y una ruta por defecto correcta. La imagen de endpoints
inicia `/bin/sh` para exponer una consola interactiva de GNS3.

El esquema estático está configurado y su conmutación fue validada: R1 usa una
ruta recursiva con `check-gateway=ping` hacia `10.10.24.2`, y R4 usa
`check-gateway=ping` hacia R2. Ante la falla inducida de R2-R4, el tráfico
conmutó por R1-R3-R5-R4 y luego volvió al primario. El siguiente trabajo,
solo cuando el usuario lo indique, es guardar el estado estático y configurar
RIPv2. La cola de salida de `500 kbit/s` sobre `R2:ether3` fue validada con
`iperf3`: el receptor obtuvo `479 Kbit/s`. Los exports sin secretos de R1-R5
ya estan en `simulacion/escenarios/estatico/config/`.

Organizacion acordada: no duplicar artefactos. Cada esquema usa
`simulacion/escenarios/<esquema>/{config,resultados,capturas}/`; los resultados
derivados comparativos se guardan en `simulacion/resultados-derivados/`.

## Estado Actualizado

La ejecucion formal del esquema estatico sigue antes de cambiar el
encaminamiento. La matriz esta en `simulacion/experimentos/matriz.csv` y
contiene 65 corridas estaticas: 40 de curva UDP (incluido 700K), TCP de
referencia, HTTP/1.1, contencion y convergencia. La curva UDP esta completa:
cinco repeticiones de 60 s para 100K a 800K. Hasta 400K no hubo perdida y el
throughput siguio la carga ofrecida; desde 500K aparecieron saturacion,
perdida y mayor jitter. Las medianas de 500K, 600K, 700K y 800K fueron,
respectivamente: `483.788`, `503.554`, `518.503` y `533.567 Kbit/s`, con
perdidas de `2.944 %`, `15.787 %`, `25.669 %` y `33.080 %`.

`simulacion/scripts/ejecutar_udp.sh`, `ejecutar_tcp.sh` y `ejecutar_http.sh`
ejecutan corridas por ID o todas las pendientes con `--all`. Delegan en
`ejecutar_trafico.sh`, que resuelve los nodos y el enlace por la API de GNS3 y
soporta `estatico`, `rip` y `ospf`. UDP y TCP guardan JSON de `iperf3`; HTTP
guarda la salida cruda de `wrk`; todos guardan PCAP y actualizan la matriz solo
al terminar correctamente. Las cinco corridas TCP de referencia ya estan
completas: mediana de `484.947 Kbit/s`, 39 retransmisiones y RTT medio de
`292.012 ms`; `r05` alcanzo `538.275 Kbit/s` por rafagas de cola y debe
tratarse como variacion, no como capacidad sostenida. `estatico-http-r01`
diagnostico revelo que el cuello de 500K solo limita `cliente -> servidor`: la
respuesta HTTP circula por `R4:ether2` en sentido inverso y alcanzo 118.39
KB/s, cerca del limite CHR de 1 Mbit/s. El cuello inverso ya fue aplicado y
verificado en R4: `mangle` marca `forward` con `out-interface=ether2` como
`cuello-R4-R2`, y la cola `cuello-R4-R2` limita esa marca a `500k`. `R4.rsc`
incluye ambos elementos. La primera HTTP y su PCAP fueron archivados como
diagnostico sin cuello inverso, y se libero `estatico-http-r01` para repetirla
bajo el cuello simetrico. La repeticion corregida ya completo:
13 solicitudes en 60 s, 4.37 s de latencia media y 58.67 KB/s. El siguiente
ensayo pendiente ya no es HTTP: las cinco repeticiones completaron una mediana
de 4.34 s de latencia, 0.22 solicitudes/s y 59.12 KB/s. El siguiente trabajo
era validar y ejecutar las corridas de contencion TCP+UDP. Las cinco se
completaron y validaron: la mediana fue 339.182 Kbit/s UDP recibido, 14.800 %
de perdida UDP, 7.900 ms de jitter, 156.426 Kbit/s TCP recibido, 102
retransmisiones TCP y 495.608 Kbit/s combinados. El ejecutor HTTP+UDP es
`simulacion/scripts/ejecutar_contencion_http_udp.sh`: UDP usa el puerto 5201 a
400K durante 60 s; `wrk` comienza a los 10 s y dura 50 s. Cada corrida genera
`<id>-udp.json`, `<id>-http.txt` y un PCAP comun de `R2-R4`. El ejecutor admite
`estatico`, `rip` y `ospf` segun la matriz. La primera validacion
`estatico-http-udp-r01` uso UDP `cliente -> servidor`, mientras la respuesta
HTTP fue `servidor -> cliente`; UDP recibio 399.932 Kbit/s sin perdida porque
cada flujo uso una cola de cuello opuesta. Sus artefactos se archivaron bajo
`diagnostico/*-sin-competencia-direccional` y se libero `r01`. La solucion
adoptada es `iperf3 -R`: UDP viaja `servidor -> cliente`, comparte la cola
`R4 -> R2` con las respuestas HTTP y permite medir contencion real. Repetir
primero `r01` y, si valida los tres artefactos y muestra competencia, ejecutar
las cuatro restantes. Una primera correccion ubico `-R` por error en el
ejecutor TCP+UDP; la captura evidencio UDP directo, sus artefactos se archivaron
como `diagnostico/*-sin-competencia-udp-directo` y se libero otra vez `r01`.
El ejecutor HTTP+UDP ya contiene `-R`; las corridas TCP+UDP existentes no se
afectaron porque son anteriores a ese cambio. La repeticion final de `r01` se
valido por PCAP: UDP fue `servidor -> cliente` y recibio 332.640 Kbit/s, con
16.553 % de perdida y 6.044 ms de jitter; HTTP alcanzo 20.10 KB/s, 0.06
solicitudes/s y 8.10 s de latencia, con dos timeouts. La suma util aproximada
fue 493.44 Kbit/s, consistente con la contencion sobre el cuello de 500K. Las
cuatro repeticiones HTTP+UDP restantes se completaron. Sus medianas fueron
334.719 Kbit/s UDP recibido, 15.954 % de perdida UDP, 7.254 ms de jitter y
19.76 KB/s de transferencia HTTP. Todas las corridas tuvieron dos o tres
timeouts de `wrk`; en `r03` la latencia figura como `0.00us`, por lo que no se
debe calcular una mediana de latencia HTTP sin tratar esos timeouts como una
categoria separada. Las cinco corridas se archivaron como
`diagnostico/*-timeout-10s` y se liberaron en la matriz. La solucion adoptada
es usar `wrk --timeout 30s` solo en HTTP+UDP: el recurso de 256 KiB necesita
cerca de 13 s con la capacidad residual. No cambian topologia, direcciones,
cuello, tasa UDP, recurso ni duracion; el siguiente hito es repetir las cinco
corridas y verificar que la latencia HTTP sea medible. Las cinco repeticiones
con `wrk --timeout 30s` ya completaron sin timeouts: las medianas fueron
335.200 Kbit/s UDP recibido, 15.874 % de perdida UDP, 8.299 ms de jitter,
12.160 s de latencia HTTP y 19.70 KB/s de transferencia HTTP. El total util
aproximado fue 492.80 Kbit/s, consistente con el cuello de 500K. El siguiente
hito es ejecutar las cinco corridas de convergencia estatica. El ejecutor es
`simulacion/scripts/ejecutar_convergencia.sh`: por API GNS3 suspende
automaticamente `R2:e2-R4:e1` a los 20 s, lo mantiene 60 s suspendido y lo
restaura; registra ping con timestamps, HTTP, eventos y PCAPs simultaneos de
`R2-R4` y `R5-R4` durante los 300 s de la fila. No requiere consola RouterOS,
credenciales ni intervencion manual. La validacion seca de `estatico-falla-r01`
paso. `estatico-falla-r01` completo con los cinco artefactos, suspendio el
enlace a los 20 s, recupero trafico por el respaldo antes de restaurarlo a los
60 s y lo dejo restaurado. La indisponibilidad fue 27.785 s, medida entre la
ultima respuesta previa a la falla y la primera de cinco respuestas ICMP
consecutivas. Las cinco repeticiones estaticas ya completaron. Usando la
primera evidencia de falla para descartar respuestas en transito, la mediana
de indisponibilidad fue 27.347 s, con rango de 23.414 a 29.310 s. El primer
intento de `r05` fue interrumpido por el limite del proceso anfitrion antes de
archivar capturas; sus temporales estan en `diagnostico/` y la repeticion
individual posterior es la registrada en la matriz. El siguiente hito es
configurar RIPv2. El estado estatico ya esta respaldado: los exports sin
secretos de R1-R5 estan en `simulacion/escenarios/estatico/config/` y se
revalidaron en vivo el 2026-11-08; R2 conserva `cuello-R2-R4` y R4 conserva
`cuello-R4-R2`, ambos a 500k. No repetir curvas de congestion para RIP u OSPF:
RIPv2 ya esta configurado, validado y exportado en `escenarios/rip/config/`;
sus cinco corridas de convergencia ya estan registradas. El siguiente ciclo es
OSPF, con costos explicitos y sus cinco corridas de convergencia.

Los endpoints actuales usan `netrunners-endpoint:1.0`, que incluye `iperf3`,
Nginx, `curl` y `wrk`, junto con recursos HTTP de 10 MiB y 256 KiB. Tras cada
reinicio de nodos, restaurar `cliente` como `10.10.1.10/24` con gateway
`10.10.1.1`, y `servidor` como `10.10.4.10/24` con gateway `10.10.4.1`; luego
iniciar Nginx en `servidor`. La conectividad y HTTP/1.1 se validaron luego del
ultimo reinicio.

La captura de GNS3 se valido en el enlace cuello `R2:Ethernet2` a
`R4:Ethernet1`. El servidor GNS3 local esta limitado a `localhost` y la API
local quedo disponible sin autenticacion, por lo que las capturas pueden
iniciarse y detenerse por API, sin Wireshark. No registrar ni restaurar
credenciales locales al reanudar. `project-files/` esta excluido de Git. Los
PCAP crudos, resultados, matriz y configuraciones se versionan directamente
en sus escenarios para conservar la evidencia reproducible.

## Nota De Validacion RIP

RIPv2 esta configurado y validado en los cinco routers. R1 usa R2 como
camino primario a `10.10.4.0/24`, R4 usa R2 como camino primario a
`10.10.1.0/24` y, con `R2-R4` suspendido, un ping unico cliente-servidor
recibio respuesta con TTL 60. Dos reglas mangle temporales de solo conteo en
R5 confirmaron exactamente un ICMP saliendo por `ether3` y una respuesta
entrando por la misma interfaz; esas reglas fueron eliminadas al terminar.

Las cinco corridas formales `rip-falla-r01` a `rip-falla-r05` completaron y
estan registradas en la matriz. Los intentos previos de r01 y r02 se
archivaron bajo `simulacion/escenarios/rip/{resultados,capturas}/diagnostico/`.

## Nota De Configuracion OSPF

OSPF esta configurado y validado en R1-R5 con area 0, instancia `ospf-v2` y
costos explicitos: 10 para R1-R2-R4 y 20 por enlace del respaldo R1-R3-R5-R4.
RIP fue eliminado de los routers. Las configuraciones sin secretos estan en
`simulacion/escenarios/ospf/config/`. Una prueba piloto suspendió R2-R4,
confirmó un ping por el respaldo con TTL 60 y la ruta de R1 por
`10.10.13.2%ether4`; el enlace se restauró y R1 volvió al primario por R2.
La validación inicial no ejecutó corridas formales. Un piloto corto sin
artefactos validó ICMP, HTTP, conmutación por R3-R5 y retorno al primario. Las
cinco corridas formales `ospf-falla-r01` a `ospf-falla-r05` completaron y se
validaron: cada una tiene cinco artefactos, `wrk` terminó sin errores ni
timeouts, y los PCAP de R5-R4 contienen tráfico de datos durante la falla. La
mediana de recuperación de cinco respuestas ICMP fue 2,381 s. No quedan
corridas de convergencia pendientes.

## Estado De Cierre

El escenario activo en GNS3 es OSPF. R1 usa R2 como primario a
`10.10.4.0/24`; el enlace R2-R4 quedó restaurado, las adyacencias relevantes
están en `Full` y RIP ya no está configurado. No ejecutar más corridas de
convergencia salvo que se solicite explícitamente repetir una medición.

La rama correcta es `tp-final` del repositorio `NetRunners_TPs`. El último
commit publicado es `c5d9df0` (`feat: agregar OSPF y capturas directas`). Los
PCAP se versionan como archivos individuales: se eliminaron los ZIP previos y
no se deben volver a crear salvo instrucción explícita. Los únicos no
rastreables esperados fuera de `tp-final` son el PDF de `tps/practico/tp6` y
un temporal bajo `simulacion/experimentos/`; no modificarlos ni incluirlos.

Los PCAP de respaldo SI contienen trafico de datos. No concluir ausencia de
ICMP o TCP a partir de un filtro rapido de TShark que no devuelve filas.
Primero usar siempre estadisticas completas:

```bash
tshark -r <pcap> -q -z io,phs
```

`rip-falla-r01-R5-R4.pcap` contiene 13.008 tramas, 6.031 ICMP, 6.867 TCP y
23 RIP. El PCAP estatico equivalente contiene 395 ICMP y 5.054 TCP. Antes de
cambiar configuracion, archivar resultados o repetir ensayos, validar el PCAP
con esas estadisticas y cotejarlo contra la matriz y los logs de eventos.

## Estado De Refuerzo

El 2026-11-09 se retornó temporalmente de OSPF al esquema estático para
ejecutar los pilotos definidos en `docs/RELEVO_REFUERZO_SIMULACIONES.md`.
Se agregaron las rutas estáticas exportadas y se removieron las instancias,
áreas y plantillas OSPF en R1-R5. R1 volvió a seleccionar la primaria hacia el
servidor por R2 y R4 la primaria hacia cliente por R2; ICMP y HTTP fueron
validados. Se conservan los dos cuellos simétricos de `500k` mediante mangle y
queue tree en R2 y R4.

El primer inicio de `estatico-udp-100k-r01-rtt` fue abortado por el operador
antes de terminar y no dejó artefactos ni modificó la matriz. Posteriormente se
repitió como piloto junto con `estatico-tcp-slow-start-r01` y
`estatico-falla-r01-rutas`; los tres se aprobaron antes de iniciar la serie.
La reversión a OSPF requiere reaplicar los exports de
`simulacion/escenarios/ospf/config/` y retirar las rutas estáticas agregadas.

Actualización: los tres pilotos estáticos y las 70 corridas estáticas de
refuerzo ya completaron y fueron validados por
`simulacion/scripts/validar_refuerzo.py . estatico`. La única cancelación
parcial, `estatico-udp-100k-r02-rtt`, quedó preservada como diagnóstico y se
repitió correctamente. Las cinco fallas instrumentadas RIP y las cinco OSPF
también completaron y fueron validadas. El escenario activo queda en OSPF, con
R2-R4 restaurado. No repetir corridas de convergencia sin una indicación
explícita del usuario.

## Relevo De Resultados Derivados

El usuario prioriza primero obtener simulaciones y evidencia cruda correcta;
no modificar la monografía hasta que lo solicite. La serie estática de
refuerzo está completa y validada. Incluye 60 corridas de carga con RTT, cinco
de slow-start y quince fallas con rutas activas R1-R5. El esquema activo es
OSPF y R2-R4 está restaurado.

Para regenerar las métricas derivadas, sin modificar artefactos crudos:

```bash
python3 simulacion/scripts/procesar_resultados.py .
python3 simulacion/scripts/validar_refuerzo.py . estatico
```

El primer comando genera en `simulacion/resultados-derivados/`:

- `corridas.csv`: métricas por ID, con campaña `original` o `refuerzo`.
- `agregados.csv`: media, mediana, mínimo, máximo, desvío y `n` por campaña,
  esquema, ensayo, tráfico, tasa y estado de enlace.
- `tcp_cwnd_series.csv`: `cwnd`, RTT, retransmisiones y throughput por
  intervalo de los ensayos TCP, incluido slow-start y TCP+UDP.

No mezclar las campañas `original` y `refuerzo`: la segunda incorpora ping
continuo y debe ser la fuente de RTT. Para convergencia de reenvío, usar además
por cada ID instrumentado:

```bash
python3 simulacion/scripts/procesar_convergencia.py . <estatico|rip|ospf> <id>
```

Esto informa una cota temporal entre la última ruta primaria y la primera ruta
de respaldo observada en R1 y R4. Ping/HTTP son métricas de servicio; no usar
ping solo como sustituto del cambio de ruta.

Para revalidar un esquema o regenerar resultados derivados sin tocar evidencia
cruda, ejecutar:

```bash
python3 simulacion/scripts/validar_refuerzo.py . <rip|ospf>
python3 simulacion/scripts/procesar_resultados.py .
```

Antes de cualquier nueva corrida, comprobar nodos iniciados, conectividad,
Nginx, `R2-R4 suspend=false`, ausencia de capturas y de sondas `ping -D`
huérfanas en el contenedor cliente. Si una corrida se interrumpe, no borrar sus
temporales: archivarlos en `resultados/diagnostico/`, liberar el ID sólo si la
matriz no fue completada y documentar la incidencia en
`docs/REGISTRO_OPERATIVO.md`.

## Protocolo Operativo Obligatorio

Esta seccion prevalece sobre cualquier inferencia del agente. No asumir que
una captura, una ruta, una cola, un filtro o un ensayo fallo sin evidencia
directa. No cambiar configuracion, liberar una fila, archivar resultados ni
repetir una corrida sobre la base de una hipotesis.

### Antes De Tocar La Red

1. Leer `AGENT.md`, `docs/HOJA_DE_RUTA.md`, la fila de `matriz.csv`, el
   export del escenario y los artefactos existentes del ID involucrado.
2. Formular que condicion exacta se quiere probar y cual es la evidencia que
   la confirma. Usar un ensayo piloto corto y aislado si esa evidencia no fue
   validada antes.
3. Para PCAP, ejecutar primero `tshark -r <pcap> -q -z io,phs`. Un filtro
   rapido sin filas NO prueba ausencia de trafico. Si el filtro contradice las
   estadisticas, detenerse e investigar el filtro antes de hacer cambios.
4. Si se suspende un enlace, preparar antes la restauracion. Restaurar el
   enlace y quitar toda regla temporal aun cuando el ensayo sea cancelado.

### Operaciones De Consola RouterOS

Cada operacion nueva hecha en una consola debe quedar registrada en el mismo
turno de trabajo. No registrar contrasenas, hashes, licencias ni IDs locales.
El registro debe incluir:

1. Objetivo y nodo o nodos afectados.
2. Comandos exactos sin secretos, en el orden ejecutado.
3. Salida relevante o condicion de exito observada.
4. Efectos persistentes esperados y como fueron revalidados.
5. Export `.rsc` sin secretos actualizado en
   `simulacion/escenarios/<esquema>/config/`.
6. Reversion exacta de reglas temporales, contadores, sniffers o cambios de
   prueba.

Guardar el procedimiento reproducible en `docs/REGISTRO_OPERATIVO.md` y
actualizar aqui el estado resumido. Si falta alguno de esos elementos, el
siguiente agente debe tratar la operacion como no documentada y no asumir que
puede reproducirla.

### Regla Para Ensayos Formales

No ejecutar una serie de cinco corridas ni una corrida de 300 s hasta que un
piloto demuestre todos los artefactos y criterios de aceptacion de la hoja de
ruta. Si una corrida formal produce un resultado inesperado, conservarla como
diagnostico y validar primero el artefacto con fuentes independientes:
matriz, eventos, logs de endpoint, tabla de rutas y estadisticas completas del
PCAP. Solo despues decidir si se archiva, corrige o repite.

## Cierre Del Refuerzo

Las cinco corridas `rip-falla-r01-rutas` a `r05-rutas` y las cinco
`ospf-falla-r01-rutas` a `r05-rutas` están completas y aprobadas por
`simulacion/scripts/validar_refuerzo.py`. `procesar_convergencia.py` normaliza
el sufijo `%interfaz` que RouterOS añade al gateway. Las cotas máximas de
convergencia de reenvío observada fueron `6.415`, `24.395`, `20.802`, `19.154`
y `23.268 s` para RIP, y `1.891`, `2.054`, `1.343`, `2.214` y `2.095 s` para
OSPF. No confundir estas cotas de plano de control con la recuperación de
servicio de ping/HTTP.

La primera serie OSPF instrumentada se conservó bajo
`simulacion/escenarios/ospf/{resultados,capturas}/diagnostico/ospf-rutas-inicio-en-respaldo/`:
comenzó antes de que OSPF regresara al primario tras el piloto y no es evidencia
formal. El validador ahora exige en R1 y R4 una muestra primaria anterior al
evento de suspensión para RIP y OSPF. El escenario vivo quedó en OSPF, con R1
por `10.10.12.2%ether3`, R4 por `10.10.24.1%ether2` y R2-R4 restaurado.
