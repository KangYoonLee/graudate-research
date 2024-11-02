import socket
import time
import threading

# 수신한 데이터들을 저장할 변수들
data_from_7 = []
data_from_8 = []
data_from_10 = []

# 최종 조립된 데이터를 저장할 변수
assembled_data = b''

def receive_data(port, data_storage, ip):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind(("sender IP", port))

        while True:
            fragment, addr = server_socket.recvfrom(4096)
            print(f"Received data from {addr}")

            # 수신한 데이터 저장
            data_storage.append(fragment)

def process_data():
    global assembled_data
    all_data = [data_from_7, data_from_8, data_from_10]
    all_fragments = []

    while True:
        for data_list in all_data:
            if data_list:
                fragment = data_list.pop(0)
                all_fragments.append(fragment)

                seq_number = fragment[0] & 0b01111111
                flag_bit = fragment[0] & 0b10000000
                payload = fragment[2:] # 2 bytes for sequence and flag bits

                if seq_number == 0: 
                    if flag_bit:
                        assembled_data = payload
                        print(f"Assembled data: {assembled_data}")
                        print(f"Data lengtha {len(assembled_data)}")
                        print(f"Time: {time.time()}")
                    else:
                        assembled_data = payload
                elif seq_number == 1:
                    if flag_bit:
                        assembled_data += payload
                        print(f"Assembled data: {assembled_data}")
                        print(f"Data lengtha {len(assembled_data)}")
                        print(f"Time: {time.time()}")
                    else:
                        assembled_data += payload
                elif seq_number == 2:
                    assembled_data += pay load
                    if flag_bit:
                        print(f"Assembled data: {assembled_data}")
                        print(f"Data lengtha {len(assembled_data)}")
                        print(f"Time: {time.time()}")
                else:
                    assembled_data += payload
                    if flag bit:
                        print(f"Assembled data: {assembled_data}")
                        print(f"Data lengtha {len(assembled_data)}")
                        print(f"Time: {time.time()}")

if __name__ == "__main__":
    receiver_threads = [
        threading.Thread(target=receive_data, args = ('port number', data_from_7, "Edge 1 IP"))
        threading.Thread(target=receive_data, args = ('port number', data_from_7, "Edge 2 IP"))
        threading.Thread(target=receive_data, args = ('port number', data_from_7, "Edge 3 IP"))
    ]
    
    for thread in receiver_threads:
        thread.start()
    
    process_thread = threading.Thread(target=process_data)
    process_thread.start()

    for thread in receiver_threads:
        thread.join()

    process_thread.join()