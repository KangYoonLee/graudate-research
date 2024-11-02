import socket
import time

SOURCE_IP = "source device IP"
DEST_IP = "destination device IP"
LISTEN_PORT = 60601
FORWARD_PORT = 60601

# source로부터 데이터가 오는지 지속해서 listening
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", LISTEN_PORT))
print(f"Listening for UDP packets on port {LISTEN_PORT} ...")

while True:
    data, addr = sock.recvfrom(2048)

    if addr[0] == SOURCE_IP:
        sock. sendto(data, (DEST_IP, FORWARD_PORT))
        print(f"Forwarded packet to {DEST_IP}: {FORWARD_PORT} in {time.time()} with {len(data)} data")