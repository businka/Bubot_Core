import socket
import struct
#
# UDP_IP = "192.168.1.147"  # localhost
# UDP_PORT = 5683
message = "Hello, World!".encode()
#
#
# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# sock.bind(('', 44440))
# print(sock.sendto(MESSAGE, (UDP_IP, UDP_PORT)))
# sock.close()

UDP_IP ='fe80::5166:b5ee:f3a7:c0ee'
UDP_IP = "fe80::c934:184d:e7a:da17"  # localhost
UDP_PORT = 37691

UDP_IP = "fe80::158"  # localhost
UDP_PORT = 5683


sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
sock.bind(('', 44441))
sock_addr = socket.getaddrinfo(UDP_IP, UDP_PORT, socket.AF_INET6, socket.SOCK_DGRAM)[0][4]
ttl = struct.pack('i', 5)
sock.setsockopt(41, socket.IPV6_MULTICAST_HOPS, ttl)
print(sock.sendto(message, (UDP_IP, UDP_PORT)))
sock.close()