# Exportado de R4 para el escenario RIP con RouterOS 7.24.6 el 2026-11-08.
/queue tree
add max-limit=500k name=cuello-R4-R2 packet-mark=cuello-R4-R2 parent=ether2
/ip address
add address=10.10.24.2/30 interface=ether2 network=10.10.24.0
add address=10.10.45.2/30 interface=ether3 network=10.10.45.0
add address=10.10.4.1/24 interface=ether4 network=10.10.4.0
/ip firewall mangle
add action=mark-packet chain=forward comment=marca-cuello-R4-R2 new-packet-mark=cuello-R4-R2 out-interface=ether2 passthrough=no
/routing rip instance
add name=rip-v2 redistribute=connected
/routing rip interface-template
add instance=rip-v2 interfaces=ether2,ether3
add instance=rip-v2 interfaces=ether4
