# Simulacion del TP Final

## Endpoint Docker

Construir la misma imagen para los nodos `cliente` y `servidor`:

```bash
docker build --tag netrunners-endpoint:1.0 simulacion/endpoint/
```

Verificar los programas requeridos:

```bash
docker run --rm netrunners-endpoint:1.0 iperf3 --version
docker run --rm netrunners-endpoint:1.0 ping -V
docker run --rm netrunners-endpoint:1.0 ip -V
```

La imagen inicia `/bin/sh` por defecto para que la consola de GNS3 sea
interactiva y permita configurar cada endpoint. En la plantilla Docker de
GNS3, dejar vacio `Start command` para usar este valor predeterminado.

## Topologia

La topologia manual en GNS3 usa cinco CHR y dos endpoints:

```text
cliente -- R1 -- R2 -- R4 -- servidor
               \          /
                R3 -- R5
```

| Enlace | Puertos |
|---|---|
| cliente-R1 | `cliente:eth0` - `R1:ether2` |
| R1-R2 (primario) | `R1:ether3` - `R2:ether2` |
| R2-R4 (cuello) | `R2:ether3` - `R4:ether2` |
| R1-R3 (respaldo) | `R1:ether4` - `R3:ether2` |
| R3-R5 (respaldo) | `R3:ether3` - `R5:ether2` |
| R5-R4 (respaldo) | `R5:ether3` - `R4:ether3` |
| R4-servidor | `R4:ether4` - `servidor:eth0` |

El camino primario es `R1-R2-R4`. El respaldo `R1-R3-R5-R4` tiene un salto
RIP adicional, por lo que RIPv2 prefiere el primario sin depender de metricas
artificiales.

## Direccionamiento

| Enlace | Red | Extremo A | Extremo B |
|---|---|---|---|
| cliente-R1 | `10.10.1.0/24` | cliente `10.10.1.10` | R1 `10.10.1.1` |
| R1-R2 | `10.10.12.0/30` | R1 `10.10.12.1` | R2 `10.10.12.2` |
| R2-R4 | `10.10.24.0/30` | R2 `10.10.24.1` | R4 `10.10.24.2` |
| R1-R3 | `10.10.13.0/30` | R1 `10.10.13.1` | R3 `10.10.13.2` |
| R3-R5 | `10.10.35.0/30` | R3 `10.10.35.1` | R5 `10.10.35.2` |
| R5-R4 | `10.10.45.0/30` | R5 `10.10.45.1` | R4 `10.10.45.2` |
| R4-servidor | `10.10.4.0/24` | R4 `10.10.4.1` | servidor `10.10.4.10` |

## Corridas UDP Automatizadas

Con el proyecto GNS3 abierto, todos los nodos iniciados y el esquema estatico
activo, ejecutar una corrida pendiente con:

```bash
simulacion/scripts/ejecutar_udp.sh estatico-udp-100k-r03
```

El script toma el esquema de la fila (`estatico`, `rip` u `ospf`), valida los
nodos y la conectividad, inicia la captura del cuello `R2-R4`, ejecuta el
servidor y cliente de `iperf3`, guarda el JSON y el PCAP en el escenario
correspondiente, y completa la fila de la matriz solo si todos esos pasos
terminan correctamente. Para procesar todas las corridas UDP pendientes en
orden de matriz:

```bash
simulacion/scripts/ejecutar_udp.sh --all
```

`--all` tarda al menos 60 segundos por corrida y no sobrescribe corridas ni
artefactos ya registrados. Los PCAP individuales permanecen excluidos de Git,
pero los datos crudos se distribuyen comprimidos en
`simulacion/escenarios/estatico/capturas-raw.zip` y
`simulacion/escenarios/rip/capturas-raw.zip`. Al extraerlos desde la raiz del
TP, conservan las rutas `capturas/<id>.pcap` referidas por la matriz.

Antes de ejecutar una corrida se puede verificar la topologia, los nodos y el
enlace de captura sin generar trafico ni archivos:

```bash
simulacion/scripts/ejecutar_udp.sh --dry-run estatico-udp-100k-r03
```

Las corridas TCP de referencia usan el mismo mecanismo y los parametros
`-t 60 -O 10` definidos en la matriz:

```bash
simulacion/scripts/ejecutar_tcp.sh estatico-tcp-r01
simulacion/scripts/ejecutar_tcp.sh --all
```

Las corridas HTTP/1.1 validan primero Nginx con `curl` y luego guardan la
salida cruda de `wrk` como texto:

```bash
simulacion/scripts/ejecutar_http.sh estatico-http-r01
simulacion/scripts/ejecutar_http.sh --all
```

Las corridas de contencion TCP+UDP inician UDP a 400K durante 60 s y, a los
10 s, TCP durante los 50 s restantes. Ambas mediciones comparten un PCAP:

```bash
simulacion/scripts/ejecutar_contencion_tcp_udp.sh estatico-tcp-udp-r01
simulacion/scripts/ejecutar_contencion_tcp_udp.sh --all
```

Las corridas de contencion HTTP+UDP envian UDP en reversa (`servidor ->
cliente`) a 400K por 60 s e inician `wrk --timeout 30s` a los 10 s durante los
50 s restantes. Asi UDP y las respuestas HTTP compiten en la cola `R4 -> R2`;
el timeout permite completar el recurso de 256 KiB con la capacidad residual.
Cada fila guarda el JSON UDP, la salida de `wrk` y un PCAP comun:

```bash
simulacion/scripts/ejecutar_contencion_http_udp.sh estatico-http-udp-r01
simulacion/scripts/ejecutar_contencion_http_udp.sh --all
```

Las corridas de convergencia se ejecutan sin intervencion manual. El script
captura `R2-R4` y `R5-R4`, inicia ping con timestamps y HTTP continuo, suspende
por API GNS3 el enlace `R2:e2-R4:e1` a los 20 s durante 60 s y lo restaura. La
duracion total de cada corrida es 300 s:

```bash
simulacion/scripts/ejecutar_convergencia.sh estatico-falla-r01
simulacion/scripts/ejecutar_convergencia.sh --all
```

## Bitacora Manual

### 2026-11-08

- Se implemento `simulacion/scripts/ejecutar_trafico.sh`, con accesos
  compatibles `ejecutar_udp.sh`, `ejecutar_tcp.sh` y `ejecutar_http.sh`, para
  ejecutar corridas formales por ID o todas las pendientes con `--all`. El
  script consulta la
  API local de GNS3, valida los nodos y la conectividad, inicia y detiene la
  captura `R2-R4`, ejecuta `iperf3` en los endpoints Docker, guarda el JSON y
  PCAP, y completa la matriz solo despues de una ejecucion exitosa. Soporta
  los esquemas `estatico`, `rip` y `ospf`; el modo `--dry-run` valida la
  topologia sin generar trafico.
- Se agrego el escalon UDP de 700 Kbit/s, con cinco repeticiones, entre 600K y
  800K. La matriz pasa a contener 65 corridas estaticas previstas.
- Se completo la curva UDP estatica: cinco repeticiones de 60 s para 100K,
  200K, 300K, 400K, 500K, 600K, 700K y 800K. Cada corrida conserva su JSON de
  `iperf3`, su PCAP del cuello y la fila correspondiente de la matriz.
- Las medianas de throughput, jitter y perdida fueron: 100K: 99.996 Kbit/s,
  0.512 ms, 0 %; 200K: 199.989 Kbit/s, 0.809 ms, 0 %; 300K: 299.989 Kbit/s,
  1.252 ms, 0 %; 400K: 399.983 Kbit/s, 0.846 ms, 0 %; 500K: 483.788 Kbit/s,
  2.155 ms, 2.944 %; 600K: 503.554 Kbit/s, 5.401 ms, 15.787 %; 700K:
  518.503 Kbit/s, 7.106 ms, 25.669 %; 800K: 533.567 Kbit/s, 5.201 ms,
  33.080 %. La saturacion comienza en 500K: el throughput deja de seguir la
  carga ofrecida, mientras la perdida y el jitter aumentan.
- Se completo TCP de referencia: cinco corridas de `iperf3 -t 60 -O 10` con
  JSON y PCAP por corrida. Las medianas fueron `484.947 Kbit/s` en el
  receptor, 39 retransmisiones y RTT medio de `292.012 ms`. Cuatro corridas
  quedaron entre 484.472 y 485.141 Kbit/s; `r05` alcanzo 538.275 Kbit/s por
  rafagas de la cola, por lo que se reportaran mediana y dispersion. Los cinco
  flujos usaron CUBIC y registraron retransmisiones, coherentes con el cuello.
- La corrida automatizada `estatico-http-r01` revelo que el cuello inicial era
  unidireccional: la cola de 500K en `R2:ether3` limita datos de
  `cliente -> servidor`, mientras la respuesta HTTP viaja
  `servidor -> cliente` por `R4:ether2`. La prueba alcanzo 118.39 KB/s,
  proxima al limite de 1 Mbit/s de CHR, por lo que queda como evidencia de
  diagnostico y no se compara con UDP/TCP. Antes de repetir HTTP se debe
  configurar en R4 una marca de paquetes de salida por `ether2` y una cola de
  500K asociada a esa marca. Las corridas HTTP restantes permanecen pendientes.
- Se aplico y verifico en R4 el cuello inverso `cuello-R4-R2`: una regla
  `mangle` con `out-interface=ether2` marca `cuello-R4-R2` y una cola arbol
  asociada usa `max-limit=500k`. Se actualizo `config/R4.rsc`. Los artefactos
  de la primera HTTP se archivaron como `diagnostico/*-sin-cuello-inverso` y
  la fila `estatico-http-r01` se libero para repetirla bajo el cuello simetrico.
- La repeticion corregida `estatico-http-r01` completo 13 solicitudes en 60 s,
  con latencia media de 4.37 s y transferencia de 58.67 KB/s. El valor es
  consistente con el nuevo limite de 500 Kbit/s para la respuesta
  `servidor -> cliente`; su JSON no aplica porque `wrk` conserva salida de
  texto, junto con el PCAP correspondiente.
- Se completaron las cinco corridas HTTP/1.1 bajo cuello simetrico. Las
  medianas fueron 4.34 s de latencia, 0.22 solicitudes/s y 59.12 KB/s de
  transferencia, consistentes con descargar un recurso de 256 KiB mediante un
  enlace de aproximadamente 500 Kbit/s.
- Se automatizo la contencion TCP+UDP mediante
  `ejecutar_contencion_tcp_udp.sh`. Para cada fila inicia servidores `iperf3`
  en los puertos 5201 (UDP) y 5202 (TCP), mantiene UDP a 400K por 60 s, inicia
  TCP a los 10 s por los 50 s restantes, conserva dos JSON y un PCAP comun, y
   completa la matriz solo si los tres artefactos son validos.
- Se automatizo la contencion HTTP+UDP mediante
  `ejecutar_contencion_http_udp.sh`. Para cada fila valida Nginx, mantiene UDP
  inverso a 400K por 60 s e inicia `wrk` a los 10 s durante los 50 s restantes.
  Guarda el JSON UDP, la salida de `wrk` y un PCAP comun; el ejecutor sirve para
  los esquemas `estatico`, `rip` y `ospf` definidos en la matriz.
- La primera ejecucion HTTP+UDP uso UDP `cliente -> servidor`, mientras las
  respuestas HTTP viajaron `servidor -> cliente`. UDP recibio 399.93 Kbit/s sin
  perdida, lo que confirmo que eran colas opuestas y no habia contencion. Sus
  artefactos se archivaron como `sin-competencia-direccional`; se corrigio el
  ensayo con `iperf3 -R` para que ambos flujos compartan la cola `R4 -> R2`.
- Durante la correccion inicial, `-R` se aplico por error al ejecutor TCP+UDP,
  no al HTTP+UDP. La captura confirmo que UDP seguia `cliente -> servidor`; sus
  artefactos tambien se archivaron como `sin-competencia-udp-directo`. Se movio
  `-R` al ejecutor correcto antes de repetir la corrida formal. Las cinco
  corridas TCP+UDP terminadas previamente no fueron afectadas.
- La repeticion corregida `estatico-http-udp-r01` confirmo en el PCAP que UDP
  viaja `servidor -> cliente`. UDP recibio 332.64 Kbit/s, con 16.55 % de
  perdida y 6.04 ms de jitter; HTTP bajo a 20.10 KB/s, 0.06 solicitudes/s y
  8.10 s de latencia, con dos timeouts. El total util aproximado de 493.44
  Kbit/s es consistente con que ambos flujos compiten por el cuello de 500K.
- Se completaron las cinco corridas HTTP+UDP corregidas. Las medianas fueron
  334.72 Kbit/s UDP recibido, 15.95 % de perdida UDP, 7.25 ms de jitter y
  19.76 KB/s de transferencia HTTP. `wrk` informo entre dos y tres timeouts por
  corrida; en `r03` la latencia quedo indefinida (`0.00us`), por lo que esa
  metrica no debe agregarse sin tratar explicita y separadamente los timeouts.
- Las cinco corridas HTTP+UDP con `wrk --timeout 10s` se archivaron como
  `diagnostico/*-timeout-10s` porque la capacidad residual requiere cerca de
  13 s para transferir 256 KiB y produjo timeouts en todas las repeticiones.
  Se aumento solo el timeout de este ensayo a 30 s, sin cambiar topologia,
  direccion, cuello, tasa UDP, recurso ni duracion, y se liberaron los cinco
  IDs para repetirlas con latencia HTTP medible.
- Las cinco repeticiones con `wrk --timeout 30s` completaron sin timeouts. Las
  medianas finales fueron 335.20 Kbit/s UDP recibido, 15.87 % de perdida UDP,
  8.30 ms de jitter, 12.16 s de latencia HTTP y 19.70 KB/s de transferencia
  HTTP. El total util aproximado de 492.80 Kbit/s vuelve a ser consistente con
  el cuello de 500K.
- Se implemento `ejecutar_convergencia.sh` para automatizar completamente la
  falla: usa la API local de GNS3 para suspender y restaurar `R2:e2-R4:e1`, sin
  credenciales RouterOS ni accion manual. Conserva ping con timestamps, salida
  HTTP, bitacora de eventos y PCAP simultaneo en `R2-R4` y `R5-R4`. Los valores
  predeterminados son 20 s antes de la falla, 60 s de enlace suspendido y 300 s
  totales. El modo `--dry-run` valida nodos y enlaces sin generar trafico ni
  alterar el estado del enlace.
- La primera corrida automatizada `estatico-falla-r01` completo con todos los
  artefactos y el enlace fue restaurado. La falla se indujo a los 20 s y el
  trafico regreso por el respaldo antes de restaurar el enlace a los 60 s. Con
  la definicion de cinco respuestas ICMP consecutivas, la indisponibilidad fue
  27.785 s.
- Las cinco corridas de convergencia estatica completaron. Aplicando la
  definicion acordada de ultima respuesta antes de la primera evidencia de
  falla hasta la primera de cinco respuestas consecutivas, la mediana de
  indisponibilidad fue 27.347 s (rango: 23.414 a 29.310 s). El primer intento
  de `r05` fue interrumpido por el limite del proceso anfitrion antes de
  archivar capturas; sus temporales se conservaron como diagnostico y la
  repeticion individual posterior completo correctamente.
- Se revalidaron en vivo los cinco routers contra los exports estaticos. R1,
  R3 y R5 conservan direccionamiento y rutas; R2 conserva la cola y marca
  `cuello-R2-R4` de 500k; R4 conserva la cola y marca inversa
  `cuello-R4-R2` de 500k. Los cinco `.rsc` en
  `simulacion/escenarios/estatico/config/` quedan como estado de referencia
  antes de configurar RIPv2.

### 2026-11-07

- Se crearon los nodos `cliente`, `servidor`, `R1`, `R2`, `R3`, `R4` y `R5`
  en el lienzo de GNS3, se conectaron segun la tabla anterior y se iniciaron.
  Todos los enlaces estan activos (verdes).
- Se configuro la primera direccion de R1 desde su consola RouterOS:

  ```routeros
  /ip address add address=10.10.1.1/24 interface=ether1
  ```

  RouterOS no muestra salida ante una alta exitosa y devuelve el prompt. Esta
  direccion conecta R1 con el endpoint `cliente`.
- Se configuro la segunda direccion de R1 para el enlace primario hacia R2:

  ```routeros
  /ip address add address=10.10.12.1/30 interface=ether2
  ```

  La red `10.10.12.0/30` queda disponible entre R1 y R2; todavia no se
  configuraron rutas ni las demas direcciones IP.
- Se configuro la tercera direccion de R1 para el enlace de respaldo hacia R3:

  ```routeros
  /ip address add address=10.10.13.1/30 interface=ether3
  ```

  R1 tiene ahora sus tres interfaces de laboratorio direccionadas.
- Se inicio sesion en R2 con `admin` y se establecio una contraseña de
  laboratorio mediante `/password`. La contraseña no se registra en el
  repositorio.
- Se configuraron las dos direcciones de R2 y se validaron con
  `/ip address print`:

  ```routeros
  /ip address add address=10.10.12.2/30 interface=ether1
  /ip address add address=10.10.24.1/30 interface=ether2
  ```

  La salida mostro ambas direcciones en `ether1` y `ether2`, respectivamente.
- Se inicio sesion en R3, se establecio su contraseña de laboratorio y se
  configuraron sus dos direcciones:

  ```routeros
  /ip address add address=10.10.13.2/30 interface=ether1
  /ip address add address=10.10.35.1/30 interface=ether2
  ```

  `/ip address print` confirmo ambas direcciones en R3.
- Se inicio sesion en R5, se establecio su contraseña de laboratorio y se
  configuraron sus dos direcciones:

  ```routeros
  /ip address add address=10.10.35.2/30 interface=ether1
  /ip address add address=10.10.45.1/30 interface=ether2
  ```

  `/ip address print` confirmo ambas direcciones en R5.
- Se inicio sesion en R4, se establecio su contraseña de laboratorio y se
  configuraron sus tres direcciones:

  ```routeros
  /ip address add address=10.10.24.2/30 interface=ether1
  /ip address add address=10.10.45.2/30 interface=ether2
  /ip address add address=10.10.4.1/24 interface=ether3
  ```

  `/ip address print` confirmo las tres direcciones en R4. Con esto, todos
  los enlaces entre routers tienen direcciones IP en ambos extremos.
- Los endpoints creados inicialmente usaban `sleep infinity` como comando de
  inicio, por lo que su consola quedaba vacia. Se corrigio el comando de inicio
  de los nodos existentes a `/bin/sh`; los nuevos builds de la imagen usan ese
  comando por defecto.
- Se configuro el endpoint `cliente`:

  ```bash
  ip addr add 10.10.1.10/24 dev eth0
  ip route replace default via 10.10.1.1
  ```

  `ip addr show dev eth0` confirmo la direccion `10.10.1.10/24` en `eth0`.
  `ip route` confirmo la ruta por defecto mediante `10.10.1.1` en `eth0`.
- La prueba inicial `ping -c 3 10.10.1.1` desde `cliente` fallo con
  `Destination Host Unreachable`. Se debe verificar la correspondencia entre
  el enlace de GNS3 y la interfaz configurada de R1 antes de continuar.
- El diagnostico en R1 con `/interface ethernet print` mostro `ether1` sin
  estado `RUNNING` y `ether2`, `ether3` y `ether4` activos. El enlace de
  `cliente` esta conectado a `R1:ether4`, no a `ether1`; se debe mover alli
  la direccion `10.10.1.1/24`. Las interfaces de R1 hacia R2 y R3 siguen
  siendo `ether2` y `ether3`.
- Se corrigio R1 moviendo la direccion del cliente a la interfaz activa:

  ```routeros
  /ip address set [find where address="10.10.1.1/24"] interface=ether4
  ```

  `/ip address print` confirmo `10.10.1.1/24` en `R1:ether4`.
- La segunda prueba `ping -c 3 10.10.1.1` desde `cliente` tambien fallo con
  `Destination Host Unreachable`. La interfaz GNS3 del contenedor debe
  identificarse antes de modificar el direccionamiento del endpoint.
- Se verifico que `cliente` solo tiene `eth0`, por lo que el problema no era
  el nombre de su interfaz. La inspeccion de la topologia guardada identifico
  el mapeo real: los adaptadores GNS3 `e1`, `e2` y `e3` de CHR corresponden a
  `ether2`, `ether3` y `ether4` de RouterOS. `ether1` queda sin enlace. Las
  direcciones configuradas inicialmente en todos los routers deben desplazarse
  una interfaz para coincidir con la tabla de puertos anterior.
- Se realinearon las tres direcciones de R1 y se verificaron con
  `/ip address print`:

  ```routeros
  /ip address set [find where address="10.10.1.1/24"] interface=ether2
  /ip address set [find where address="10.10.12.1/30"] interface=ether3
  /ip address set [find where address="10.10.13.1/30"] interface=ether4
  ```

- La prueba posterior `ping -c 3 10.10.1.1` desde `cliente` recibio tres
  respuestas (0 % de perdida). Queda validada la red directamente conectada
  `cliente-R1`.
- Se realinearon las direcciones de R2 y se verificaron con
  `/ip address print`:

  ```routeros
  /ip address set [find where address="10.10.12.2/30"] interface=ether2
  /ip address set [find where address="10.10.24.1/30"] interface=ether3
  ```

- Se realinearon las direcciones de R3 y se verificaron con
  `/ip address print`:

  ```routeros
  /ip address set [find where address="10.10.13.2/30"] interface=ether2
  /ip address set [find where address="10.10.35.1/30"] interface=ether3
  ```

- Se realinearon las direcciones de R5 y se verificaron con
  `/ip address print`:

  ```routeros
  /ip address set [find where address="10.10.35.2/30"] interface=ether2
  /ip address set [find where address="10.10.45.1/30"] interface=ether3
  ```

- Se realinearon las direcciones de R4 y se verificaron con
  `/ip address print`:

  ```routeros
  /ip address set [find where address="10.10.24.2/30"] interface=ether2
  /ip address set [find where address="10.10.45.2/30"] interface=ether3
  /ip address set [find where address="10.10.4.1/24"] interface=ether4
  ```

  Todos los enlaces entre routers tienen ahora direcciones IP en sus puertos
  físicos correctos.
- Desde R1, `ping 10.10.12.2 count=3` recibio tres respuestas sin perdida.
  Queda validado el enlace directo primario `R1-R2`.
- Desde R1, `ping 10.10.13.2 count=3` recibio tres respuestas sin perdida.
  Queda validado el primer enlace del respaldo, `R1-R3`.
- Desde R2, `ping 10.10.24.2 count=3` recibio tres respuestas sin perdida.
  Queda validado el enlace `R2-R4`, donde se aplicara el cuello de botella.
- Desde R3, `ping 10.10.35.2 count=3` recibio tres respuestas sin perdida.
  Queda validado el enlace `R3-R5`.
- Desde R5, `ping 10.10.45.2 count=3` recibio tres respuestas sin perdida.
  Queda validado el enlace `R5-R4`; todos los enlaces entre routers superaron
  la prueba de conectividad directa.
- Se configuro el endpoint `servidor`:

  ```bash
  ip addr add 10.10.4.10/24 dev eth0
  ip route replace default via 10.10.4.1
  ```

  `ip addr show dev eth0` confirmo la direccion `10.10.4.10/24` en `eth0`.
  `ip route` confirmo la ruta por defecto mediante `10.10.4.1`; el ping a esa
  puerta de enlace recibio tres respuestas sin perdida. Queda validada la red
  directamente conectada `R4-servidor`.
- Se inicio el escenario de rutas estaticas en R1:

  ```routeros
  /ip route add dst-address=10.10.4.0/24 gateway=10.10.12.2 distance=1 comment=primaria-R2
  /ip route add dst-address=10.10.4.0/24 gateway=10.10.13.2 distance=2 comment=respaldo-R3-R5
  ```

  `/ip route print` confirmo activa la ruta primaria por R2 y disponible como
  respaldo la ruta por R3-R5.
- Se configuraron en R4 las rutas estaticas de retorno hacia `cliente`:

  ```routeros
  /ip route add dst-address=10.10.1.0/24 gateway=10.10.24.1 distance=1 comment=primaria-R2
  /ip route add dst-address=10.10.1.0/24 gateway=10.10.45.1 distance=2 comment=respaldo-R5-R3
  ```

  La tabla de R4 confirmo activa la ruta primaria por R2 y disponible el
  respaldo por R5-R3.
- Se configuraron en R2 las rutas de tránsito del camino primario:

  ```routeros
  /ip route add dst-address=10.10.1.0/24 gateway=10.10.12.1 comment=hacia-cliente
  /ip route add dst-address=10.10.4.0/24 gateway=10.10.24.2 comment=hacia-servidor
  ```

  Ambas rutas quedaron activas en la tabla de R2.
- Se configuraron en R3 las rutas de tránsito del camino de respaldo:

  ```routeros
  /ip route add dst-address=10.10.1.0/24 gateway=10.10.13.1 comment=hacia-cliente
  /ip route add dst-address=10.10.4.0/24 gateway=10.10.35.2 comment=hacia-servidor
  ```

  Ambas rutas quedaron activas en la tabla de R3.
- Se configuraron en R5 las rutas de tránsito del camino de respaldo:

  ```routeros
  /ip route add dst-address=10.10.1.0/24 gateway=10.10.35.1 comment=hacia-cliente
  /ip route add dst-address=10.10.4.0/24 gateway=10.10.45.2 comment=hacia-servidor
  ```

  Ambas rutas quedaron activas en la tabla de R5.
- La prueba inicial desde `cliente` a `10.10.4.10` recibio tres respuestas sin
  perdida por el camino primario `R1-R2-R4`.
- Se corrigio el seguimiento de falla del primario en R1. Una ruta estática
  normal solo detecta la disponibilidad del siguiente salto R2, no la caída de
  `R2-R4`; por eso se agrego un monitoreo recursivo de la IP de R4:

  ```routeros
  /ip route add dst-address=10.10.24.2/32 gateway=10.10.12.2 scope=10 comment=monitor-R4-via-R2
  /ip route set [find where comment="primaria-R2"] gateway=10.10.24.2 check-gateway=ping target-scope=11
  ```

  La tabla mostro activas tanto la ruta primaria a `10.10.4.0/24` como la
  ruta recursiva de monitoreo. Si `R2-R4` falla, R1 detectara que
  `10.10.24.2` deja de responder y activara el respaldo por R3-R5.
- La repetición posterior de `ping -c 3 10.10.4.10` desde `cliente` recibio
  tres respuestas sin perdida. El monitoreo recursivo no alteró la
  conectividad por el camino primario.
- Se inició el ensayo de falla estática deshabilitando `R2:ether3`, el enlace
  hacia R4, mientras `cliente` ejecutaba `ping -D -i 0.2 10.10.4.10`. El ping
  dejó de recibir respuestas después de la secuencia 77; la conmutación aún no
  se confirmó y se debe inspeccionar la tabla de R1 antes de restaurar el
  enlace.
- La tabla de R1 durante la falla confirmó la detección esperada: la ruta
  primaria por `10.10.24.2` quedó inactiva (`I`) y el respaldo por
  `10.10.13.2` quedó activo (`A`). Como el ping todavía no recuperó, se debe
  verificar el camino de retorno en R4.
- La tabla de R4 reveló que su primaria hacia `10.10.24.1` continuó activa
  durante la falla. Se debe habilitar `check-gateway=ping` en esa ruta para
  que R4 detecte la pérdida de R2 y active el respaldo por R5.
- En R4 se habilitó el monitoreo de su ruta primaria:

  ```routeros
  /ip route set [find where comment="primaria-R2"] check-gateway=ping
  ```

  Tras el período de detección, el ping continuo desde `cliente` volvió a
  recibir respuestas. Queda validada la conmutación estática completa por
  `R1-R3-R5-R4` ante la falla inducida de `R2-R4`.
- Tras restaurar `R2:ether3`, R2 informó la interfaz en estado `RUNNING`, pero
  R1 todavía no pudo alcanzar `10.10.24.2` y mantuvo el respaldo activo. Se
  debe comprobar la conectividad directa R2-R4 y el retorno de las sondas de
  monitoreo antes de declarar recuperado el camino primario.
- La prueba directa posterior desde R2 a `10.10.24.2` tuvo 100 % de pérdida,
  pese a que `R2:ether3` informó `RUNNING`. Se debe comprobar el estado del
  extremo R4 antes de modificar rutas.
- R4 también informó `ether2` en estado `RUNNING`. La investigación continúa
  en ARP para determinar por qué los extremos activos no intercambian tráfico
  IP después de restaurar el enlace.
- R2 resolvió correctamente por ARP `10.10.24.2` a la MAC de `R4:ether2` y la
  marcó como `reachable`; la capa 2 está operativa. Falta aislar el fallo ICMP
  en uno de los extremos.
- R4 alcanzó a `10.10.24.1` tres veces sin pérdida. El enlace y R4 funcionan;
  se investiga la dirección de origen usada por los pings emitidos desde R2.
- R2 alcanzó a R4 al forzar el origen `10.10.24.1`, lo que confirma que las
  respuestas a la fuente elegida automáticamente carecen de ruta de retorno.
  Se debe agregar en R4 una ruta a `10.10.12.0/30` por R2 para permitir las
  sondas recursivas emitidas desde R1.
- Se agregó en R4 la ruta de retorno para las sondas de R1:

  ```routeros
  /ip route add dst-address=10.10.12.0/30 gateway=10.10.24.1 check-gateway=ping comment=retorno-monitor-R1
  ```

  Tras la detección, la tabla de R1 volvió a mostrar `primaria-R2` activa y
  `respaldo-R3-R5` inactiva. El escenario estático queda validado en estado
  normal, durante la falla de `R2-R4`, y tras la recuperación del enlace.
- Se creó el cuello de botella en la salida de R2 hacia R4:

  ```routeros
  /queue tree add name=cuello-R2-R4 parent=ether3 max-limit=500k
  ```

  `/queue tree print` confirmó `parent=ether3` y `max-limit=500k`. Se debe
  medir con `iperf3` antes de iniciar los ensayos formales.
- La validación TCP inicial ejecutó `iperf3 -c 10.10.4.10 -t 20 -i 1` desde
  `cliente`. El receptor informó `1.03 Mbit/s`, no los `500 Kbit/s` esperados,
  con ráfagas, intervalos sin transferencia y 167 retransmisiones. La cola
  existe pero se debe verificar si está contabilizando el tráfico antes de
  usarla como cuello experimental.
- `/queue tree print stats` en R2 mostró cero bytes, paquetes y descartes para
  `cuello-R2-R4`. La cola no procesó el flujo de la prueba; se debe confirmar
  el camino activo antes de modificar el mecanismo de limitación.
- La tabla de R1 confirmó `primaria-R2` activa durante la investigación de la
  cola. El tráfico recorrió R2; se debe inspeccionar si FastTrack está
  evitando que la cola procese paquetes.
- R2 no tiene reglas de filtro, por lo que FastTrack no es la causa. La causa
  real es que una cola árbol requiere paquetes marcados por `mangle`; la cola
  original no tenía `packet-mark` y por eso no contabilizó tráfico. Se debe
  marcar en `forward` todo paquete que salga por `R2:ether3` y asociar esa
  marca a la cola.
- Se corrigió la cola en R2:

  ```routeros
  /ip firewall mangle add chain=forward out-interface=ether3 action=mark-packet new-packet-mark=cuello-R2-R4 passthrough=no comment=marca-cuello-R2-R4
  /queue tree set [find where name="cuello-R2-R4"] packet-mark=cuello-R2-R4
  ```

  La cola conserva `parent=ether3`, `max-limit=500k` y ahora tiene
  `packet-mark=cuello-R2-R4`. Falta repetir la medición TCP y consultar sus
  contadores.
- La repetición TCP de 20 s con `iperf3` confirmó el cuello: el receptor
  informó `479 Kbit/s`, con intervalos mayormente entre `463` y `498 Kbit/s`.
  El valor coincide con el objetivo de `500 kbit/s`; la diferencia inicial y
  final corresponde al arranque y cierre del flujo TCP.
- Se exportó la configuración del escenario estático de R1 en su sistema de
  archivos RouterOS con `/export file=R1-estatico`. `/file print` confirmó el
  archivo `R1-estatico.rsc` de 920 bytes. La copia al repositorio se hará tras
  exportar los cinco routers.
- Se exportaron R2, R3, R4 y R5 del escenario estático y se copiaron los cinco
  exports, sin `system id`, a `simulacion/escenarios/estatico/config/R1.rsc`
  hasta `R5.rsc`.
- Se definio la metodologia en dos ensayos separados: primero, congestion con
  el enlace `R2-R4` activo para observar throughput, perdida, latencia,
  retransmisiones y jitter sin cambio de ruta; segundo, falla controlada al
  deshabilitar ese enlace para medir el tiempo de conmutacion entre rutas
  estaticas, RIPv2 y OSPF.
- Se identifico que `iperf3` en modo TCP genera un flujo TCP de referencia,
  pero no solicitudes HTTP. Se conservara para medir el comportamiento de TCP
  bajo congestion y se incorporara trafico HTTP/1.1 real sobre las mismas
  maquinas endpoint: Nginx servira un recurso estatico en `servidor` y `wrk`
  lo solicitara desde `cliente`. La imagen Docker, la matriz de corridas y la
  monografia se actualizaran mas adelante; todavia no se modificaron.
- Se actualizo `simulacion/endpoint/Dockerfile` para incluir Nginx, `wrk` y
  `curl`, y para generar los recursos estaticos `/var/www/html/archivo-10m.bin`
  de 10 MiB y `/var/www/html/archivo-256k.bin` de 256 KiB. La imagen local
  `netrunners-endpoint:1.0` fue reconstruida.
  Los endpoints ya iniciados en GNS3 conservan la imagen anterior y no tienen
  salida a Internet, por lo que deben recrearse desde la plantilla Docker para
  aplicar la imagen nueva. Luego se les respondera su direccionamiento actual:
  `cliente` con `10.10.1.10/24` y gateway `10.10.1.1`; `servidor` con
  `10.10.4.10/24` y gateway `10.10.4.1`.
- Se recrearon los endpoints con la imagen actualizada, se reconectaron a
  `R1:e1` y `R4:e3` (que corresponden a `ether2` y `ether4` en RouterOS), se
  aplico el direccionamiento y se inicio Nginx en `servidor`. El ping de
  `cliente` a `10.10.4.10` no tuvo perdida. Una solicitud HTTP/1.1 a ambos
  recursos devolvio `200 OK`; `wrk` requiere indicar el puerto `:80` y usar
  `--timeout 10s` en este enlace. Una verificacion TCP de 10 s con `iperf3`
  obtuvo `487.95 Kbit/s` en el receptor, consistente con el cuello de
  `500 kbit/s`.
- Se creo `simulacion/experimentos/matriz.csv` con 60 corridas previstas para
  el esquema estatico: 35 de curva UDP, 5 TCP de referencia, 5 HTTP/1.1, 10
  de contencion TCP/UDP y HTTP/UDP, y 5 de convergencia con HTTP e ICMP. Cada
  fila tiene un ID, parametros, repeticion y campos vacios para fecha,
  ejecutor y archivos producidos durante la ejecucion.
- Se valido la captura sin interfaz grafica de GNS3: en el enlace cuello debe
  elegirse `R2:Ethernet2` a `R4:Ethernet1` y desmarcar `Start the capture
  visualization program`. Una prueba TCP de 10 s genero
  `project-files/captures/R2_Ethernet2_to_R4_Ethernet1.pcap`; `tshark` mostro
  la conversacion `10.10.1.10:33752` a `10.10.4.10:5201` durante 10.52 s, con
  785 tramas y 697 kB. Las capturas formales se iniciaran y detendran de esta
  forma, y luego se procesaran con `tshark` sin abrir Wireshark.
- Se excluyeron de Git los artefactos de ejecucion de GNS3 y las capturas
  crudas `.pcap` y `.pcapng`; se conservaran en el repositorio las
  configuraciones, la topologia, los resultados derivados y la evidencia
  procesada de cada corrida.
- Se ejecuto la primera corrida formal de la matriz,
  `estatico-udp-100k-r01`, con captura en `R2:Ethernet2` a `R4:Ethernet1`.
  El receptor de `iperf3` obtuvo `99.997 Kbit/s`, jitter de `0.532 ms` y
  `0 %` de perdida sobre 60 s. La captura contiene 627 datagramas UDP durante
  59.9 s y quedo guardada fuera de Git como
  `capturas/estatico-udp-100k-r01-R2-R4.pcap`; el JSON versionable esta en
  `resultados/raw/estatico-udp-100k-r01.json`.
- Se desactivo la proteccion con contrasena del servidor GNS3 local, limitado
  a `localhost`, para poder automatizar las operaciones de la API sin
  credenciales. Se verifico la API y se iniciaron los nodos del proyecto desde
  ella; despues del reinicio se restauro el direccionamiento de los endpoints
  y se inicio Nginx en `servidor`. La conectividad extremo a extremo y HTTP/1.1
  volvieron a validarse. En adelante, las capturas de enlace pueden iniciarse
  y detenerse mediante la API, sin abrir Wireshark ni realizar clicks manuales.
  El proximo ensayo pendiente es `estatico-udp-100k-r02`; debe repetir el
  trafico UDP de 100 Kbit/s durante 60 s con captura automatizada en `R2-R4`.
