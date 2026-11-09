# Exportado de R2 para el escenario OSPF con RouterOS 7.24.6 el 2026-11-08.
/queue tree
add max-limit=500k name=cuello-R2-R4 packet-mark=cuello-R2-R4 parent=ether3
/ip address
add address=10.10.12.2/30 interface=ether2 network=10.10.12.0
add address=10.10.24.1/30 interface=ether3 network=10.10.24.0
/ip firewall mangle
add action=mark-packet chain=forward comment=marca-cuello-R2-R4 new-packet-mark=cuello-R2-R4 out-interface=ether3 passthrough=no
/routing ospf instance
add name=ospf-v2 redistribute=connected router-id=10.255.0.2
/routing ospf area
add area-id=0.0.0.0 instance=ospf-v2 name=backbone
/routing ospf interface-template
add area=backbone cost=10 interfaces=ether2
add area=backbone cost=10 interfaces=ether3
