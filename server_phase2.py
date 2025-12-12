import csv
import time
import json
import random
import socket
import struct
import datetime

from collections import defaultdict
from argparse import ArgumentParser





# --- COLOR CONFIGURATION ---
class Colors:
    RED =    "\033[91m"
    GREEN =  "\033[92m"
    YELLOW = "\033[93m"
    BLUE =   "\033[94m"
    RESET =  "\033[0m"
# ---------------------------

HOST = '0.0.0.0'
PORT = 5000
BUFFER_SIZE = 4096

HEADER_FORMAT = '<B H H L B'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

MSG_INIT = 0
MSG_DATA = 1
MSG_HEARTBEAT = 2
MSG_ACK = 3

CSV_LOG = "server_recv_log.csv"

last_seq = defaultdict(lambda: -1)

# Init CSV file
with open(CSV_LOG, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "recv_time", "addr", "device_id", "seq", "msg_type",
        "is_duplicate", "payload_len", "batch_count", "cpu_ms"
    ])


def start_server(simulate_loss_rate=0.0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))

    print(f"{Colors.GREEN}[+] Phase-3 Server running on port {PORT}{Colors.RESET}")
    print(f"    Simulated Loss Rate: {simulate_loss_rate * 100}%")
    print(f"{Colors.GREEN}[+] Listening...{Colors.RESET}")

    while True:
        try:
            data, addr = sock.recvfrom(BUFFER_SIZE)
            start_cpu = time.process_time()
            recv_time = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]

            # Simulated packet loss
            if random.random() < simulate_loss_rate:
                print(f"{Colors.RED}[{recv_time}] [X] [Simulated Drop] Dropping packet from {addr}{Colors.RESET}")
                continue

            # Ensure header exists
            if len(data) < HEADER_SIZE:
                continue

            # Parse header
            vmt, device_id, seq, ts_field, flags = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
            version = vmt >> 4
            msg_type = vmt & 0x0F
            payload = data[HEADER_SIZE:]


