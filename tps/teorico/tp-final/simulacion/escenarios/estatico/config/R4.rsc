# Exportado de R4 para el escenario estatico con RouterOS 7.24.6 el 2026-11-08; revalidado desde la instancia el 2026-11-08.
/interface ethernet
set [ find default-name=ether1 ] disable-running-check=no
set [ find default-name=ether2 ] disable-running-check=no
set [ find default-name=ether3 ] disable-running-check=no
set [ find default-name=ether4 ] disable-running-check=no
/queue tree
add max-limit=500k name=cuello-R4-R2 packet-mark=cuello-R4-R2 parent=ether2
/ip address
add address=10.10.24.2/30 interface=ether2 network=10.10.24.0
add address=10.10.45.2/30 interface=ether3 network=10.10.45.0
add address=10.10.4.1/24 interface=ether4 network=10.10.4.0
/ip dhcp-client
# Interface not active
add interface=ether1 name=client1
/ip firewall mangle
add action=mark-packet chain=forward comment=marca-cuello-R4-R2 \
    new-packet-mark=cuello-R4-R2 out-interface=ether2 passthrough=no
/ip route
add check-gateway=ping comment=primaria-R2 distance=1 dst-address=\
    10.10.1.0/24 gateway=10.10.24.1
add comment=respaldo-R5-R3 distance=2 dst-address=10.10.1.0/24 gateway=\
    10.10.45.1
add check-gateway=ping comment=retorno-monitor-R1 dst-address=10.10.12.0/30 \
    gateway=10.10.24.1
