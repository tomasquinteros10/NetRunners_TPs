# Exportado de R2 para el escenario estatico con RouterOS 7.24.6 el 2026-11-08; revalidado desde la instancia el 2026-11-08.
/interface ethernet
set [ find default-name=ether1 ] disable-running-check=no
set [ find default-name=ether2 ] disable-running-check=no
set [ find default-name=ether3 ] disable-running-check=no
set [ find default-name=ether4 ] disable-running-check=no
/queue tree
add max-limit=500k name=cuello-R2-R4 packet-mark=cuello-R2-R4 parent=ether3
/ip address
add address=10.10.12.2/30 interface=ether2 network=10.10.12.0
add address=10.10.24.1/30 interface=ether3 network=10.10.24.0
/ip dhcp-client
# Interface not active
add interface=ether1 name=client1
/ip firewall mangle
add action=mark-packet chain=forward comment=marca-cuello-R2-R4 \
    new-packet-mark=cuello-R2-R4 out-interface=ether3 passthrough=no
/ip route
add comment=hacia-cliente dst-address=10.10.1.0/24 gateway=10.10.12.1
add comment=hacia-servidor dst-address=10.10.4.0/24 gateway=10.10.24.2
