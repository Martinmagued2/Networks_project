
import socket
import struct
import datetime

HOST = '127.0.0.1'
PORT = 5000
BUFFER_SIZE = 1024

def create_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    return sock

def receive_packet(sock):
    return sock.recvfrom(BUFFER_SIZE)


HEADER_FORMAT = '<B H H L B'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# Message type constants
MSG_INIT = 0
MSG_DATA = 1
MSG_HEARTBEAT = 2

def parse_header(data):
    if len(data) < HEADER_SIZE:
        return None, "Malformed"

    version_msgtype, device_id, seq, ts, flags = struct.unpack(
        HEADER_FORMAT, data[:HEADER_SIZE]
    )

    version = version_msgtype >> 4
    msg_type = version_msgtype & 0x0F

    msg_name = {
        MSG_INIT: "INIT",
        MSG_DATA: "DATA",
        MSG_HEARTBEAT: "HEARTBEAT"
    }.get(msg_type, "UNKNOWN")

    return {
        "version": version,
        "msg_type": msg_type,
        "msg_name": msg_name,
        "device_id": device_id,
        "seq": seq,
        "timestamp": ts,
        "flags": flags
    }, None



# ============================================
#  SECTION 3 — Server Logic / Printing (Person C)
#  - Calls networking + parsing
#  - Displays decoded info
# ============================================

def start_server():
    sock = create_socket()
    print("TinyTelemetry Server started on port 5000\n")

    while True:
        data, addr = receive_packet(sock)
        recv_time = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]

        header, error = parse_header(data)

        if error:
            print(f"[{recv_time}]  Malformed packet from {addr}")
            continue

        print(f"[{recv_time}] From {addr} → "
              f"Ver={header['version']}, Type={header['msg_name']}, "
              f"DevID={header['device_id']}, Seq={header['seq']}, "
              f"Ts={header['timestamp']}, Flags={header['flags']}")

if __name__ == "__main__":
    start_server()
