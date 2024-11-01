# 실시간 캡쳐, data 정보 저장을 위한 lib
import pyshark
import collections
import random
import threading
import socket
import time
import subprocess

# 라즈베리파이 IP 주소
# E1, E2, E3: Edge Layer device들의 IP 주소
# DST: Destination Layer device의 IP 주소
E1 = "192.168.0.7"
E2 = "192.168.0.8"
E3 = "192.168.0.10"
DST = "192.168.0.17"

pi_addresses = {
    E1: '00',
    E2: '01',
    E3: '10'
}

E1_FLAG = pi_addresses[E1] # 00
E2_FLAG = pi_addresses[E2] # 01
E3_FLAG = pi_addresses[E3] # 10

# 1. 패킷 실시간 캡쳐 & 데이터 정보 저장
# 캡처 인터페이스 (wifi -> 'en0')
INTERFACE = 'en0'

# Average Throughput 계산 시 사용할 time window size
t_c = 3

# Throughput 계산 시 사용할 queue 초기화 
A_input_queue = collections.deque([0], maxlen=t_c)
A_output_queue = collections.deque([0], maxlen=t_c)
A_latency = 0

B_input_queue = collections.deque([0], maxlen=t_c)
B_output_queue = collections.deque([0], maxlen=t_c)
B_latency = 0

C_input_queue = collections.deque([0], maxlen=t_c)
C_output_queue = collections.deque([0], maxlen=t_c)
C_latency = 0

last_second = None

# 각 노드의 input bits, output bits, source와의 채널 상태 업데이트 함수
def update_queues_and_throughput(current_time, source_ip, label, length):
    # current_time: 해당 데이터의 시간          packet.sniff_time.timestamp()
    # souce_ip: 데이터를 보낸 source의 IP       str(packet.ip.src)   
    # label: 수신자 식별하는 label              str(udp_payload_str[0:2])
    # length: 해당 데이터의 길이                int(packet.length) - 43
    global A_input_queue, A_output_queue
    global B_input_queue, B_output_queue
    global C_input_queue, C_output_queue
    global A_latency, B_latency, C_latency
    global last_second

    current_second = int(current_time)
    # 새로운 초로 넘어가면 큐에 0을 추가
    if last_second is None or current_second > last_second:
        if last_second is not None:
            for _ in range(current_second - last_second):
                A_input_queue.append(0)
                A_output_queue.append(0)
                B_input_queue.append(0)
                B_output_queue.append(0)
                C_input_queue.append(0)
                C_output_queue.append(0)
        last_second = current_second

    # capture한 데이터의 source_ip에 따라 output queue 업데이트
    if source_ip == "192.168.0.7": # 전송한 노드가 A이면
        if label == '01':           # A -> B
            A_output_queue[-1] += length
            B_input_queue[-1] += length
        elif label == '10':         # A -> C
            A_output_queue[-1] += length
            C_input_queue[-1] += length

    elif source_ip == "192.168.0.8": # 전송한 노드가 B이면
        if label == '00':           # B -> A
            B_output_queue[-1] += length
            A_input_queue[-1] += length
        elif label == '10':         # B -> C
            B_output_queue[-1] += length
            C_input_queue[-1] += length

    else:                           # 전송한 노드가 C이면
        if label == '01':           # C -> B
            C_output_queue[-1] += length
            B_input_queue[-1] += length
        elif label == '00':         # C -> A
            C_output_queue[-1] += length
            A_input_queue[-1] += length

# 패킷 캡처 및 처리 함수 정의 : thread로 background에서 지속적으로 실행
def capture_packets():
    capture_filter = "udp and ip.src == 192.168.0.7 or ip.src == 192.168.0.8 or ip.src == 192.168.0.10"
    capture = pyshark.LiveCapture(interface='en0', display_filter=capture_filter)

    for packet in capture.sniff_continuously(): # source의 wireshark에서 모든 패킷 캡쳐 중
        try:
            if 'UDP' in packet: # 패킷이 UDP로 보내졌다면
                ip_src = packet.ip.src # 일단 source IP 딴다.

                if ip_src in pi_addresses: # 만약 source IP가 Edge들 IP 중 하나라면,
                    current_time = packet.sniff_time.timestamp() # [확인 출력용] 시간 찍어보기

                    # update 함수를 위한 type 변경
                    source_ip = str(ip_src) # source 식별용
                    udp_payload_str = str(packet.udp.payload) # destination 식별용
                    packet_label = udp_payload_str[0:2] 
                    data_length = int(packet.length) - 43 # 데이터 크기 식별용

                    if packet_label == E1_FLAG:
                        ip_dst = E1
                    elif packet_label == E2_FLAG:
                        ip_dst = E2
                    else:
                        ip_dst = E3

                    update_queues_and_throughput(current_time, source_ip, packet_label, data_length)

        except Exception as e:
            print(f"An error occurred: {e}")

# 스레드 생성 및 실행
capture_thread = threading.Thread(target=capture_packets)
capture_thread.start()


# 2. PFS 진행 코드
# Throughput 계산용 함수
def get_throughput(queue):
    if queue:
        total_bits = sum(queue)
        return total_bits / len(queue)  # 3초 동안의 평균 throughput
    return 0

def get_channelState():
    global A_latency, B_latency, C_latency
    # 채널 상태를 의미하는 latency 구하기
    ping_command = ["ping", "-c", "1", E1]
    ping_result = subprocess.run(ping_command, capture_output=True, text=True)

    lines = ping_result.stdout.splitlines()
    resTime_info = lines[-1]
    resTime = resTime_info.split('=')[1].strip()
    lst = resTime.split('/')
    A_latency = float(lst[1])

    ping_command = ["ping", "-c", "1", E2]
    ping_result = subprocess.run(ping_command, capture_output=True, text=True)

    lines = ping_result.stdout.splitlines()
    resTime_info = lines[-1]
    resTime = resTime_info.split('=')[1].strip()
    lst = resTime.split('/')
    B_latency = float(lst[1])

    ping_command = ["ping", "-c", "1", E3]
    ping_result = subprocess.run(ping_command, capture_output=True, text=True)

    lines = ping_result.stdout.splitlines()
    resTime_info = lines[-1]
    resTime = resTime_info.split('=')[1].strip()
    lst = resTime.split('/')
    C_latency = float(lst[1])

# 네트워크 throughput update용 함수 (PFS 알고리즘을 참고)
def network_throughput_update(num):
    global T_1, T_2, T_3
    global R_1, R_2, R_3

    if num == 0:
        T_1 = (1-1/t_c)*T_1 + (1/t_c)*R_1
        T_2 = (1-1/t_c)*T_2
        T_3 = (1-1/t_c)*T_3
    elif num == 1:
        T_1 = (1-1/t_c)*T_1
        T_2 = (1-1/t_c)*T_2 + (1/t_c)*R_2
        T_3 = (1-1/t_c)*T_3
    else:
        T_1 = (1-1/t_c)*T_1
        T_2 = (1-1/t_c)*T_2
        T_3 = (1-1/t_c)*T_3 + (1/t_c)*R_3
    return 0


# 엔터를 누르는 행위 -> Source에서 데이터를 전송한다는 application의 명령
start = input()

T_1 = 0; T_2 = 0; T_3 = 0
R_1 = 0; R_2 = 0; R_3 = 0

LOOP = 4 # PFS는 기본적으로 4번 진행 (할당율을 4번 결정)
allocationRatio = [0, 0, 0] # 데이터 조각을 어느 곳에 줄 것인가
unbusyness = [0, 0, 0] # 각 Edge의 부하 (R_k/T_k를 의미)

for i in range(LOOP):
    if i == 0: # 처음 돌리는 것이라면 -> 처음에 T_k를 구해줘야함.
        T_1 = get_throughput(A_output_queue)
        T_2 = get_throughput(B_output_queue)
        T_3 = get_throughput(C_output_queue)
    
    print("***\n***\n***")
    print(f"T_1 = {T_1}")
    print(f"T_2 = {T_2}")
    print(f"T_3 = {T_3}")

    get_channelState()
    R_1 = 1/A_latency
    R_2 = 1/B_latency
    R_3 = 1/C_latency
    
    print()
    print(f"R_1 = {R_1}")
    print(f"R_2 = {R_2}")
    print(f"R_3 = {R_3}")

    unbusyness[0] = R_1/T_1 # Edge1
    unbusyness[1] = R_2/T_2 # Edge2
    unbusyness[2] = R_3/T_3 # Edge3
    
    print()
    print(f"unbusyness E1 = {R_1/T_1}")
    print(f"unbusyness E2 = {R_2/T_2}")
    print(f"unbusyness E3 = {R_3/T_3}")

    # Unbusyness(R_k/T_k)가 가장 큰 노드 선택
    maxUnbusyness = max(unbusyness)
    maxNode = unbusyness.index(maxUnbusyness)

    # allocation Ratio 지정해주기
    allocationRatio[maxNode] += 1
    
    print()
    print(f"{allocationRatio}")
    print("***\n***\n***\n")

    network_throughput_update(maxNode)


# 3. 데이터 생성 코드
MTU = 4096 # 데이터 payload 크기 (min: 100, max: 4096, avg: 엣지의 Throughput에서 평균을 냄)

def generate_random_data(size):
    return bytearray(random.getrandbits(8) for _ in range(size))

data = generate_random_data(MTU) 



# 4. data fragmentation 후 각 Edge에게 전송하는 함수
def fragmentation_send(data, allocationRatio, IPs, ports):
    # 각 비율에 따라 데이터 길이 계산
    total_length = len(data)
    frag_lengths = [total_length * ratio // 4 for ratio in allocationRatio]
    
    # 데이터 분할
    frag1 = data[:frag_lengths[0]]
    frag2 = data[frag_lengths[0]:frag_lengths[0] + frag_lengths[1]]
    frag3 = data[frag_lengths[0] + frag_lengths[1]:frag_lengths[0] + frag_lengths[1] + frag_lengths[2]]
    frags = [frag1, frag2, frag3]
    notZero = sum(1 for ratio in allocationRatio if ratio != 0)

    print(len(frag1))
    print(len(frag2))
    print(len(frag3))
    
    # 각 조각에 시퀀스 번호 및 플래그 비트 추가하여 전송
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
        temp = 1
        seq_number = 0
        for i, frag in enumerate(frags):
            if len(frag) != 0:
                if temp == notZero: # 첫 번째라면 
                    seq_with_frag = seq_with_frag = bytes([seq_number | 0b10000000]) + bytes([seq_number]) + frag
                    temp += 1
                elif temp < notZero:
                    seq_with_frag = bytes([seq_number]) + frag
                    temp += 1

                seq_number += 1
                client_socket.sendto(seq_with_frag, (IPs[i], ports[i]))
                send_time = time.time()
                print(f"Sent fragment {i} to {IPs[i]}:{ports[i]} with length {len(seq_with_frag)} at {send_time:.6f} seconds")

# Single Path Transmission (STP) 방식 고용 -> 비교할 알고리즘
def naive_send(data, IP, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.sendto(data, (IP, port))
    send_time = time.time()
    print(f"(Naive) Sent data to {IP}:{port} with length {len(data)} data in {send_time}")
    client_socket.close()

IPs = [E1, E2, E3]
ports = [60601, 60602, 60603]

# 데이터 분할 및 전송
fragmentation_send(data, allocationRatio, IPs, ports)
naive_send(data, DST, 60604)