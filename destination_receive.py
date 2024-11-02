import time
import socket

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket: 
    server_socket.bind(("sender device IP". 60604)) 

    while True:
        packet, addr = server_socket.recvfrom(4096)
        payload = packet
        print(f"{payload}")
        print(f"Data length: {len(payload)}")
        print(f"Time: {time.time()}")