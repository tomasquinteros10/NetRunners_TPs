# Exportado de R3 para el escenario OSPF con RouterOS 7.24.6 el 2026-11-08.
/ip address
add address=10.10.13.2/30 interface=ether2 network=10.10.13.0
add address=10.10.35.1/30 interface=ether3 network=10.10.35.0
/routing ospf instance
add name=ospf-v2 redistribute=connected router-id=10.255.0.3
/routing ospf area
add area-id=0.0.0.0 instance=ospf-v2 name=backbone
/routing ospf interface-template
add area=backbone cost=20 interfaces=ether2
add area=backbone cost=20 interfaces=ether3
