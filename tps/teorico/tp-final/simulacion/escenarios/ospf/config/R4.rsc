# Exportado de R4 para el escenario OSPF con RouterOS 7.24.6 el 2026-11-08.
/queue tree
add max-limit=500k name=cuello-R4-R2 packet-mark=cuello-R4-R2 parent=ether2
/ip address
add address=10.10.24.2/30 interface=ether2 network=10.10.24.0
add address=10.10.45.2/30 interface=ether3 network=10.10.45.0
add address=10.10.4.1/24 interface=ether4 network=10.10.4.0
/ip firewall mangle
add action=mark-packet chain=forward comment=marca-cuello-R4-R2 new-packet-mark=cuello-R4-R2 out-interface=ether2 passthrough=no
/routing ospf instance
add name=ospf-v2 redistribute=connected router-id=10.255.0.4
/routing ospf area
add area-id=0.0.0.0 instance=ospf-v2 name=backbone
/routing ospf interface-template
add area=backbone cost=10 interfaces=ether2
add area=backbone cost=20 interfaces=ether3
