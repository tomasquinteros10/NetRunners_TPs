# Exportado de R1 para el escenario RIP con RouterOS 7.24.6 el 2026-11-08.
/ip address
add address=10.10.1.1/24 interface=ether2 network=10.10.1.0
add address=10.10.12.1/30 interface=ether3 network=10.10.12.0
add address=10.10.13.1/30 interface=ether4 network=10.10.13.0
/routing rip instance
add name=rip-v2 redistribute=connected
/routing rip interface-template
add instance=rip-v2 interfaces=ether3,ether4
add instance=rip-v2 interfaces=ether2
