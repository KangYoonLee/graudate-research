import socket
import random
import time

sender_ip = 'IP' # edge devices 각 IP

# traffic을 주고받을 IP 리스트: edge devices IP와 port 번호가 들어감
receivers = [('IP1', 'given port 1'), ('IP2', 'given port 2'), ('IP3', 'given port 3')] 

sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_packet(receiver_ip, receiver_port):
    # 추후 어떤 엣지에서 왔는지 알기 위한 meta data인 Tag를 붙여준다.
    if receiver_ip == 'IP1':
        tag = b'\x01'
    else:
        tag = b'\x10'

    packet_size = random.randint(100,1460) # random size 지정
    packet = bytearray(random.getrandbits(8) for _ in range(packet_size))
    sender_socket.sendto(tag + packet, (receiver_ip, receiver_port)) 
    sender_socket.sendto(tag + packet, ('source IP', 'port')) # source에게도 보냈다는 사실을 알려주기 위함
    print(f"Sent packet of size {packet_size} bytes to {receiver_ip}: {receiver_port}")
    random_interval = random.uniform(0.1, 2) # random interval 지정
    time.sleep(random_interval)


while True:
    for receiver_ip, receiver_port in receivers:
        send_packet(receiver_ip, receiver_port)

