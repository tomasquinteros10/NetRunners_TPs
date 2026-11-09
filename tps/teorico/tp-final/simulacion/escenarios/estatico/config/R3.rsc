# Exportado de R3 para el escenario estatico con RouterOS 7.24.6 el 2026-11-08; revalidado desde la instancia el 2026-11-08.
/interface ethernet
set [ find default-name=ether1 ] disable-running-check=no
set [ find default-name=ether2 ] disable-running-check=no
set [ find default-name=ether3 ] disable-running-check=no
set [ find default-name=ether4 ] disable-running-check=no
/ip address
add address=10.10.13.2/30 interface=ether2 network=10.10.13.0
add address=10.10.35.1/30 interface=ether3 network=10.10.35.0
/ip dhcp-client
# Interface not active
add interface=ether1 name=client1
/ip route
add comment=hacia-cliente dst-address=10.10.1.0/24 gateway=10.10.13.1
add comment=hacia-servidor dst-address=10.10.4.0/24 gateway=10.10.35.2
