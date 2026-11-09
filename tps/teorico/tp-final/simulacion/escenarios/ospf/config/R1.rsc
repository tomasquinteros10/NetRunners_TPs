# Exportado de R1 para el escenario OSPF con RouterOS 7.24.6 el 2026-11-08.
/ip address
add address=10.10.1.1/24 interface=ether2 network=10.10.1.0
add address=10.10.12.1/30 interface=ether3 network=10.10.12.0
add address=10.10.13.1/30 interface=ether4 network=10.10.13.0
/routing ospf instance
add name=ospf-v2 redistribute=connected router-id=10.255.0.1
/routing ospf area
add area-id=0.0.0.0 instance=ospf-v2 name=backbone
/routing ospf interface-template
add area=backbone cost=10 interfaces=ether3
add area=backbone cost=20 interfaces=ether4
