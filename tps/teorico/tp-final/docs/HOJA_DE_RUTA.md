# Hoja de Ruta de la Simulacion

Esta guia define un camino reproducible para simular congestion y
convergencia de encaminamiento con GNS3, MikroTik CHR, iperf3 y Wireshark.
La topologia, las configuraciones, los comandos y los resultados derivados
deben quedar versionados en este repositorio. Las imagenes de maquinas
virtuales y las capturas grandes no se versionan.

## Convenciones

- `[ ]`: pendiente.
- **Manual**: requiere una accion en GNS3, RouterOS o con privilegios de
  administrador. OpenCode no debe ejecutarla sin indicacion explicita.
- **Todos**: cada integrante que vaya a ejecutar la simulacion debe repetir
  el paso. Esto evita resultados dependientes de una sola computadora.
- **OpenCode**: paso que puede automatizarse o verificarse desde el
  repositorio cuando el grupo lo solicite.

Antes de marcar un paso, registrar debajo el responsable, fecha y evidencia:
comando ejecutado, captura, nombre de archivo o hash de la imagen.

## 1. Preparar el stack

### 1.1 Requisitos de la computadora

- [x] **Todos / manual** Cada integrante que ejecute pruebas debe verificar:

  ```bash
  virt-host-validate qemu
  command -v gns3 gns3server qemu-system-x86_64 wireshark iperf3 docker git
  df -h .
  ```

  **Check de aceptacion:** KVM, `/dev/kvm` y TUN accesibles; al menos 10 GB
  libres; todos los comandos devuelven una ruta. Registrar las versiones de
   GNS3, QEMU, Wireshark, iperf3 y Docker en el [`README.md`](../README.md).

### 1.2 Instalacion del stack

- [x] **Todos / manual** En Ubuntu/Debian, instalar el stack:

  ```bash
  sudo apt update
   sudo apt install gns3-gui gns3-server qemu-system-x86 qemu-utils wireshark tshark \
     iperf3 tcpdump docker.io git make python3
   ```

   Responsable: rac877. Fecha: 2026-11-07. Evidencia: GNS3, QEMU, Docker y
   TShark instalados y operativos; `tshark --version` informa 4.6.9.

- [x] **Todos / manual** Verificar el acceso sin privilegios adicionales:

  ```bash
  docker info
  tshark -D
   virt-host-validate qemu
   ```

   Responsable: rac877. Fecha: 2026-11-07. Evidencia: `docker info` conecta
   al daemon Docker 29.1.3, `tshark -D` enumera interfaces de captura y
   `virt-host-validate qemu` da PASS para KVM, `/dev/kvm` y TUN. Las
   advertencias de cgroup `devices` y Secure Guest no bloquean el laboratorio.

- [ ] **Todos / manual, solo si falla el check anterior** Agregar el usuario
  al grupo que corresponda y cerrar sesion/iniciar sesion:

  ```bash
  sudo usermod -aG docker "$USER"
  sudo usermod -aG kvm "$USER"
  sudo usermod -aG wireshark "$USER"
  ```

  `docker` es necesario si los endpoints se ejecutan como contenedores y el
  comando `docker info` falla sin `sudo`. `kvm` solo es necesario si QEMU no
  puede acceder a `/dev/kvm`. `wireshark` solo es necesario si `tshark` o
  Wireshark no pueden capturar sin privilegios; algunas distribuciones usan
  capacidades de Linux en `dumpcap` y no requieren el grupo. `libvirt` no es
  necesario para GNS3 con QEMU local.

  El grupo `docker` concede privilegios equivalentes a root sobre el host;
  agregarlo solo en equipos confiables y exclusivamente cuando se usen nodos
  Docker.

- [x] **Todos / manual** Confirmar que `tshark --version` funciona. Durante
   la instalacion, elegir permiso de captura para usuarios no root si el
   instalador lo consulta.

   Responsable: rac877. Fecha: 2026-11-07. Evidencia: `tshark --version`
   devuelve TShark (Wireshark) 4.6.9.

### 1.3 Configuracion inicial de GNS3

- [x] **Todos / manual** Al abrir GNS3 por primera vez, completar el
  asistente inicial seleccionando `Run appliances on my local computer`.
  No usar GNS3 VM ni un servidor remoto para este laboratorio.
- [x] **Todos / manual** En `Local server configuration`, conservar los
  valores locales por defecto:

  ```text
  Server path: /usr/bin/gns3server
  Host binding: localhost
  Port: 3080 TCP
  ```

  Si `gns3server` esta instalado en otra ruta, obtenerla con
  `command -v gns3server` y usar ese resultado como `Server path`.

  **Check de aceptacion:** GNS3 abre un proyecto vacio sin informar error de
  conexion con el servidor local.

### 1.4 Imagen CHR y plantilla QEMU

- [x] **Todos / manual** Descargar la misma version estable de MikroTik CHR
  para QEMU/KVM desde <https://mikrotik.com/download>, en formato `Raw disk
  image (.img.zip)`. Registrar en el futuro `README.md` de esta carpeta:
   version RouterOS, formato de imagen, URL y salida de `sha256sum` en
   [`README.md`](../README.md).
- [x] **Todos / manual** Descomprimir el archivo descargado. Debe quedar un
  archivo llamado `chr-<version>.img`.
- [x] **Todos / manual** Copiar la imagen RAW al directorio que GNS3 explora
  para las imagenes QEMU antes de abrir el asistente de plantilla:

  ```bash
  cp "/ruta/de/descarga/chr-<version>.img" "$HOME/GNS3/images/QEMU/"
  sha256sum "/ruta/de/descarga/chr-<version>.img" \
    "$HOME/GNS3/images/QEMU/chr-<version>.img"
  ```

  Las dos sumas deben ser iguales. Conservar la copia original hasta iniciar
  correctamente una instancia de prueba. Si el directorio no existe, abrir
  GNS3 una vez para que cree su estructura local.
- [x] **Todos / manual** Crear la plantilla desde
  `Edit -> Preferences -> QEMU -> QEMU VMs -> New` con estos valores:

  ```text
  Run this QEMU VM on my local computer
  Name: MikroTik-CHR-<version>
  QEMU binary: qemu-system-x86_64
  RAM: 512 MB
  Console type: telnet
  Disk image: chr-<version>.img (Existing image)
  Network adapters: 4
  Adapter type: virtio-net-pci
  ```

  GNS3 puede proponer por defecto un solo adaptador de tipo `e1000`. Antes de
  aplicar la plantilla, cambiar explicitamente `Adapters` a `4` y `Type` a
  `virtio-net-pci`. Si la plantilla ya fue creada, usar `Edit` en
  `Edit -> Preferences -> QEMU -> QEMU VMs` para corregir ambos valores.

  No marcar `This is a legacy ASA VM`. No elegir `New image` ni un archivo
  `OVMF_CODE.fd` como disco; son discos o firmware no correspondientes a CHR.
- [x] **Todos / manual** Arrastrar una instancia de prueba al lienzo,
  iniciarla y abrir la consola. El primer acceso de RouterOS es con el usuario
  `admin` sin contrasena; establecer una contrasena nueva inmediatamente.

  Validar la instancia desde la consola con:

  ```routeros
  /system resource print
  /system license print
  /interface ethernet print
  ```

  **Check de aceptacion:** RouterOS informa la version CHR elegida, licencia
  `free`, 512 MiB de memoria, una CPU y las interfaces `ether1` a `ether4`.
- [x] **Todos / manual** Usar dos endpoints Docker basados en una misma
   imagen fijada por tag, por ejemplo `netrunners-endpoint:1.0`. Esa imagen
   debera incluir `iperf3`, `ping` e `iproute2`.

   Responsable: rac877. Fecha: 2026-11-07. Evidencia: imagen local
   `netrunners-endpoint:1.0` construida; `iperf3 --version`, `ping -V` e
   `ip -V` ejecutan correctamente en contenedores efimeros.

- [x] **OpenCode** Crear mas adelante el `Dockerfile` reproducible de los
   endpoints y documentar el comando `docker build`.

   Responsable: OpenCode. Fecha: 2026-11-07. Evidencia:
   `simulacion/endpoint/Dockerfile` y `README.md` documentan el build y las
   verificaciones.

  **Check de aceptacion:** la instancia CHR muestra el prompt de RouterOS en
  la consola. Mas adelante, tras crear los endpoints, deben iniciar cuatro
  CHR y dos endpoints; cada endpoint debe ejecutar `iperf3 --version` y
  `ping -V`.

## 2. Versionar la base del experimento

- [ ] **OpenCode** Crear, cuando el grupo lo autorice, la estructura:

  ```text
   README.md
   simulacion/
     endpoint/Dockerfile
     topologia/red-congestion.gns3
     escenarios/
       estatico/{config,resultados,capturas}/
       rip/{config,resultados,capturas}/
       ospf/{config,resultados,capturas}/
     experimentos/matriz.csv
     scripts/procesar_iperf.py
     scripts/extraer_pcap.sh
     resultados-derivados/
  ```

- [x] **Manual** Exportar la configuracion de cada RouterOS con `export` y
  copiar los archivos `.rsc` sin claves, usuarios ni secretos al directorio
  `simulacion/escenarios/<esquema>/config/` correspondiente.

   Responsable: rac877. Fecha: 2026-11-08. Evidencia: exports estáticos de
   R1-R5, sin `system id`, en `simulacion/escenarios/estatico/config/`.
- [ ] **OpenCode** Incorporar reglas de `.gitignore` para imagenes CHR,
  overlays QEMU, snapshots, temporales, logs y capturas crudas grandes.
- [ ] **Todos / manual** Confirmar que `git status` no propone subir
  `.qcow2`, `.img`, `project-files/tmp`, `snapshots` ni capturas masivas.

  **Check de aceptacion:** una clonacion limpia contiene la documentacion,
  topologia, configuraciones y scripts, pero no requiere descargar binarios
  desde Git para evitar conflictos y problemas de licencia.

## 3. Armar la topologia manualmente

- [x] **Manual** Crear la topologia en diamante:

  ```text
   Cliente -- R1 -- R2 -- R4 -- Servidor
                 \          /
   R3 -- R5
   ```

   Responsable: rac877. Fecha: 2026-11-07. Evidencia: nodos creados,
   conectados e iniciados en GNS3; todos los enlaces estan activos.

- [x] **Manual** Usar una subred `/30` distinta para cada enlace entre
  routers y redes separadas para Cliente-R1 y R4-Servidor. Guardar el plan de
  direccionamiento en [`README.md`](../README.md).

   Responsable: rac877. Fecha: 2026-11-07. Evidencia: plan y puertos en
   `README.md`; todos los enlaces directamente conectados fueron validados con
   tres respuestas ICMP sin perdida.
- [x] **Manual** Nombrar los nodos exactamente `cliente`, `R1`, `R2`, `R3`,
  `R4`, `R5` y `servidor`; etiquetar los enlaces como `primario`, `respaldo`
  y `cuello`.

   Responsable: rac877. Fecha: 2026-11-07. Evidencia: nodos y enlaces
   etiquetados en el lienzo de GNS3.
- [x] **Manual** Aplicar en R2 una cola de salida sobre el enlace `R2-R4`
  que limite a `500 kbit/s`. La licencia gratuita de CHR limita cada egreso a
  1 Mbps; por eso el cuello deliberado debe estar por debajo de ese valor.

   Responsable: rac877. Fecha: 2026-11-07. Evidencia: cola
   `cuello-R2-R4` configurada en `R2:ether3` con `max-limit=500k`.
- [ ] **Manual** Verificar que el camino primario sea `R1-R2-R4` y el de
  respaldo `R1-R3-R5-R4`.

**Check de aceptacion:** `ping` Cliente-Servidor funciona; una captura en
`R2-R4` muestra trafico durante el estado normal; una captura en `R5-R4`
no muestra trafico de datos en ese estado.

## 4. Configurar los tres esquemas de encaminamiento

La topologia, direccionamiento, cuello, endpoints y parametros de carga no
cambian entre esquemas. Solo cambia el encaminamiento.

- [x] **Manual** Configurar rutas estaticas con una ruta primaria por R2 y
  una ruta estatica flotante por R3-R5 de mayor distancia administrativa.

   Responsable: rac877. Fecha: 2026-11-07. Evidencia: rutas primarias y de
   respaldo configuradas en R1 y R4; R1 usa monitoreo recursivo a
   `10.10.24.2` y R4 `check-gateway=ping` para detectar R2-R4. La conmutación
   por R3-R5 y el retorno al primario fueron validados con ping continuo.
- [ ] **Manual** Configurar RIPv2 en los cinco routers. El camino por R2 debe
  tener dos saltos entre R1 y R4, mientras que el respaldo por R3-R5 debe
  tener tres.
- [ ] **Manual** Configurar OSPF en area 0. Ajustar costos de interfaz para
  que R2 sea el camino preferido y R3-R5 el respaldo. No depender del costo
  automatico por defecto.
- [ ] **Manual** Antes de cada ensayo, exportar la configuracion efectiva y
  compararla con el `.rsc` correspondiente del repositorio.

**Check de aceptacion:** para cada esquema, las tablas de R1 y R4 muestran
el camino primario esperado. Deshabilitar `R2-R4` conmuta el trafico por
R3-R5.

## 5. Definir y ejecutar las corridas

### 5.1 Regla de reproducibilidad

- [ ] **Todos / manual** Usar una matriz de corridas comun. Cada fila debe
  tener: `id`, protocolo de ruta, tipo de trafico, tasa ofrecida, duracion,
  repeticion, fecha, ejecutor y nombre de archivos generados.
- [ ] **Todos / manual** Ejecutar cinco repeticiones independientes por fila
  y esperar que la red vuelva al estado estable antes de repetir.
- [ ] **Manual** Capturar en el enlace `R2-R4` para los ensayos de congestion.
  Para convergencia, capturar simultaneamente `R2-R4` y `R5-R4`.

### 5.2 Curva de congestion UDP

- [ ] **Manual** Mantener el cuello en 500 kbit/s y correr UDP con tasas
  ofrecidas de 100K, 200K, 300K, 400K, 500K, 600K, 700K y 800K. Duracion: 60 s.
- [ ] **Manual** En el servidor iniciar una instancia por corrida:

  ```bash
  iperf3 -s -1
  ```

- [ ] **Manual** En el cliente ejecutar, reemplazando la IP y el identificador
  de corrida:

  ```bash
  iperf3 -c <IP_SERVIDOR> -u -b 400K -l 1200 -t 60 -i 1 -J \
    > /tmp/udp-<id>.json
  ```

- [ ] **Manual** Copiar el JSON al host y guardarlo como
  `resultados/raw/udp-<id>.json`; guardar la captura como
  `capturas/udp-<id>.pcapng` fuera de Git si es grande.

  **Check de aceptacion:** bajo 500K no hay perdida significativa; por encima
  del cuello se observan throughput limitado, perdida y/o jitter crecientes.

### 5.3 TCP y contencion TCP-UDP

- [ ] **Manual** Medir TCP aislado durante 60 s. Para capacidad estable usar
  `-O 10`; para estudiar slow start y retransmisiones no usar `-O`:

  ```bash
  iperf3 -c <IP_SERVIDOR> -t 60 -O 10 -i 1 -J > /tmp/tcp-<id>.json
  ```

- [ ] **Manual** Para contencion, iniciar UDP a 400K y, diez segundos despues,
  iniciar un flujo TCP. Registrar ambos JSON y una misma captura del cuello.
- [ ] **Manual** No describir iperf3 como HTTP ni RTP en las conclusiones.
  El TCP de iperf3 representa un flujo TCP de referencia y el UDP CBR es una
  aproximacion a trafico sensible a demora.

  **Check de aceptacion:** la captura contiene ACK duplicados o
  retransmisiones cuando haya perdida TCP; el resultado UDP contiene jitter y
  perdida informados por el receptor.

### 5.4 Convergencia ante falla

- [ ] **Manual** Ejecutar ping continuo Cliente-Servidor y guardar salida con
  timestamps. Si el endpoint lo soporta:

  ```bash
  ping -D -i 0.2 <IP_SERVIDOR> > /tmp/ping-<id>.log
  ```

- [ ] **Manual** Con las capturas activas, deshabilitar el enlace o interfaz
  `R2-R4`; no cambiar ningun otro parametro.
- [ ] **Manual** Esperar la recuperacion, detener ping y guardar el log.
  Repetir cinco veces para estatico, RIP y OSPF.
- [ ] **Manual** Medir indisponibilidad como el intervalo entre la ultima
  respuesta antes de la falla y la primera de cinco respuestas consecutivas
  luego de conmutar. Reportar esta definicion en el informe.

**Check de aceptacion:** el trafico posterior a la recuperacion aparece en
`R5-R4`; las capturas permiten relacionar la interrupcion con los mensajes
RIP u OSPF.

## 6. Procesar y verificar resultados

- [ ] **OpenCode** Implementar un procesador sin dependencias externas que
  lea JSON de iperf3 y produzca CSV consolidado.
- [ ] **Manual** Ejecutar el procesador sobre todas las corridas y revisar
  que no existan IDs duplicados, JSON incompletos ni tasas distintas a las
  declaradas en la matriz.
- [ ] **OpenCode** Implementar extraccion reproducible con `tshark` de
  retransmisiones TCP, paquetes RIP/OSPF y campos necesarios para respaldar
  las figuras.
- [ ] **Manual** Revisar visualmente en Wireshark solo las capturas citadas
  en el informe. Wireshark aporta evidencia cualitativa; el CSV consolidado
  es la fuente de los numeros y graficos.

El CSV consolidado debe incluir como minimo:

```text
id,esquema_ruta,tipo_trafico,repeticion,tasa_ofrecida_kbps,
throughput_mbps,perdida_pct,jitter_ms,rtt_mediana_ms,
retransmisiones_tcp,indisponibilidad_s
```

**Check de aceptacion:** cada valor del informe se puede rastrear a un ID de
corrida, un JSON/PCAP y una configuracion versionada.

## 7. Graficos y conclusiones

- [ ] **OpenCode** Integrar los CSV derivados en graficos PGFPlots de LaTeX:
  carga ofrecida vs throughput, carga vs perdida/jitter, TCP vs UDP y
  distribucion de indisponibilidad por protocolo.
- [ ] **Manual** Validar que cada grafico indique unidades, cantidad de
  repeticiones, cuello configurado y esquema de encaminamiento.
- [ ] **Manual** Redactar cada hallazgo como: observacion cuantitativa,
  prediccion teorica y explicacion o limitacion.
- [ ] **Manual** Explicitar las limitaciones: CHR gratuito a 1 Mbps por
  egreso, topologia pequena, carga sintetica iperf3, implementacion TCP del
  endpoint y recursos del host.

Conclusiones que solo se pueden afirmar si los datos las respaldan:

- El throughput se estabiliza al acercarse o superar la capacidad del cuello.
- UDP sobrecargado incrementa perdida y jitter.
- TCP responde a perdida/retransmisiones reduciendo su tasa efectiva.
- RIP y OSPF no evitan por si solos una congestion mientras el enlace sigue
  activo; la comparacion entre ellos corresponde a la conmutacion ante falla.

## 8. Compartir una copia ejecutable

- [ ] **Todos / manual** Subir mediante Git solo topologia, Dockerfile,
  configuraciones sin secretos, matriz, scripts, CSV derivados y documentacion.
- [ ] **Manual** Para compartir una copia operativa puntual de GNS3, detener
  el proyecto y usar `File -> Export portable project`.
- [ ] **Manual** En esa exportacion, no marcar `Include base images`,
  `Include snapshots` ni `Keep the original compute IDs`.
- [ ] **Todos / manual** Cada compañero importa el proyecto, instala por su
  cuenta la misma imagen CHR y construye la misma imagen Docker de endpoint.

**Check de aceptacion final:** un integrante que no creo la topologia puede
clonar el repositorio, reconstruir las plantillas indicadas, importar el
proyecto, aplicar las configuraciones y repetir una fila de la matriz con
resultados comparables.
