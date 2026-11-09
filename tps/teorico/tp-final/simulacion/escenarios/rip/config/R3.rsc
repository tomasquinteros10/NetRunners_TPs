# Exportado de R3 para el escenario RIP con RouterOS 7.24.6 el 2026-11-08.
/ip address
add address=10.10.13.2/30 interface=ether2 network=10.10.13.0
add address=10.10.35.1/30 interface=ether3 network=10.10.35.0
/routing rip instance
add name=rip-v2 redistribute=connected,rip
/routing rip interface-template
add instance=rip-v2 interfaces=ether2,ether3
