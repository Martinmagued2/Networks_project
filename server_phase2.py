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
            if msg_type == MSG_INIT:
                # Client restarted — reset sequence counter
                if last_seq[device_id] != -1:
                    print(f"{Colors.BLUE}[{recv_time}] [+] Device {device_id} Re-connected. Resetting Sequence.{Colors.RESET}")
                last_seq[device_id] = -1

            # Detect batch size
            batch_count = 0
            if msg_type == MSG_DATA and len(payload) > 0:
                try:
                    obj = json.loads(payload.decode())
                    batch_count = len(obj) if isinstance(obj, list) else 1
                except:
                    batch_count = 0

            is_dup = 0

            # Duplicate detection
            if seq <= last_seq[device_id]:
                is_dup = 1

                # Send ACK for duplicate to stop client retries
                ack_header = struct.pack(HEADER_FORMAT, (version << 4) | MSG_ACK,
                                         device_id, seq, int(time.time()), 0)
                sock.sendto(ack_header, addr)

                print(f"{Colors.YELLOW}[{recv_time}] [!] DUPLICATE: Seq={seq} Dev={device_id} (Ignored){Colors.RESET}")

            else:
                # Gap detection
                expected = last_seq[device_id] + 1
                if last_seq[device_id] != -1 and seq > expected:
                    gap_len = seq - expected
                    print(f"{Colors.YELLOW}[{recv_time}] [!] GAP DETECTED: Missing {gap_len} pkts! (Exp {expected}, Got {seq}){Colors.RESET}")

                last_seq[device_id] = seq

                  # Send ACK
                if msg_type in (MSG_INIT, MSG_DATA, MSG_HEARTBEAT):
                    ack_header = struct.pack(HEADER_FORMAT, (version << 4) | MSG_ACK, device_id, seq, int(time.time()),
                                             0)
                    sock.sendto(ack_header, addr)

            end_cpu = time.process_time()
            cpu_ms = (end_cpu - start_cpu) * 1000

            # Log
            with open(CSV_LOG, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    recv_time, addr, device_id, seq, msg_type,
                    is_dup, len(payload), batch_count, f"{cpu_ms:.4f}"
                ])

            type_str = {0: "INIT", 1: "DATA", 2: "HEARTBEAT"}.get(msg_type, "UNK")

            if not is_dup:
                print(
                    f"{Colors.GREEN}[{recv_time}] Seq={seq} Type={type_str} Batch={batch_count} CPU={cpu_ms:.3f}ms{Colors.RESET}")
                if batch_count == 1 and payload:
                    try:
                        print(f"   Payload: {payload.decode()}")
                    except:
                        pass
                elif batch_count > 1:
                    print(f"   Payload: [Batch of {batch_count} items]")

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Server stopping...{Colors.RESET}")
            break
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.RESET}")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--simulate_loss", type=float, default=0.0, help="Probability of dropping packet (0.0-1.0)")
    args = parser.parse_args()
    start_server(simulate_loss_rate=args.simulate_loss)

