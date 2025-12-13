import os
import csv
import time
import json
import socket
import random
import struct

from datetime import datetime
from argparse import ArgumentParser

# --- COLORS ---
# ANSI escape sequences for terminal colors
RED =    "\033[91m"
GREEN =  "\033[92m"
YELLOW = "\033[93m"
RESET =  "\033[0m"

# Enable ANSI colors in Windows terminal
os.system('')

HEADER_FORMAT = '<B H H L B'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

MSG_INIT = 0
MSG_DATA = 1
MSG_HEARTBEAT = 2
MSG_ACK = 3

CLIENT_VERSION = 1
CLIENT_RTO = 0.5
MAX_RETRIES = 5
CLIENT_CSV = "client_measurements.csv"

# Init CSV
with open(CLIENT_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "send_time", "device_id", "seq", "msg_type",
        "attempts", "ack_time", "rtt", "status", "batch_size"
    ])


class TelemetrySensor:
    def __init__(self, device_id, host, port, batch_size=1, random_batch=False, dup_rate=0.0):
        self.device_id = device_id
        self.server_addr = (host, port)
        self.seq_num = 0
        self.socket = None

        SAFE_MAX_BATCH = 3

        # Check if the user tried to set a batch size larger than the limit
        if batch_size > SAFE_MAX_BATCH:
            # Print warning and clamp the size
            print(
                f"{YELLOW}Warning: Requested batch size ({batch_size}) exceeds the safe limit (3) to maintain the 200-byte packet constraint. Clamping to {SAFE_MAX_BATCH}.{RESET}")
            batch_size = SAFE_MAX_BATCH

        self.max_batch_size = batch_size
        self.current_batch_limit = batch_size

        self.random_batch = random_batch
        self.dup_rate = dup_rate
        self.buffer = []

        # If random batching is on, start with a random limit based on the (now clamped) max_batch_size
        if self.random_batch:
            self.current_batch_limit = random.randint(1, self.max_batch_size)

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(CLIENT_RTO)

        print(f"{GREEN}Sensor {self.device_id} is ready.{RESET}")
        print(f"{GREEN}Target: {self.server_addr}{RESET}")
        print(f"{GREEN}Batching: {'Random (1-' + str(self.max_batch_size) + ')' if self.random_batch else str(self.max_batch_size)}{RESET}")
        print(f"{GREEN}Simulated Duplication Rate: {self.dup_rate * 100}%{RESET}")

    def _wait_for_ack(self, seq):
        start = time.time()
        try:
            while True:
                data, _ = self.socket.recvfrom(1024)
                vmt, dev, rseq, ts, flags = struct.unpack(HEADER_FORMAT, data)
                if (vmt & 0x0F) == MSG_ACK and rseq == seq:
                    return True, time.time() - start
        except socket.timeout:
            return False, None

    def _send_packet(self, msg_type, payload=b'', max_retries=MAX_RETRIES, wait_for_ack=True):
        self.seq_num += 1
        vmt = (CLIENT_VERSION << 4) | msg_type
        timestamp = int(time.time())

        header = struct.pack(HEADER_FORMAT, vmt, self.device_id, self.seq_num, timestamp, 0)
        packet = header + payload

        readable_type = {0: "INIT", 1: "DATA", 2: "HEARTBEAT"}.get(msg_type, "UNKNOWN")

        # VISUALIZATION LOGIC
        current_batch_count = 1
        content_display = ""
        if msg_type == MSG_DATA and payload:
            try:
                decoded = payload.decode()
                content_display = decoded
                data_obj = json.loads(decoded)
                if isinstance(data_obj, list):
                    current_batch_count = len(data_obj)
            except:
                content_display = "<Binary>"

        print(
            f"\n[{datetime.now().strftime('%H:%M:%S')}] Seq:{self.seq_num} Type:{readable_type} Items:{current_batch_count}")
        if content_display:
            print(f"   Data: {content_display}")

        attempts = 0
        acked = False
        rtt = 0.0

        if wait_for_ack:
            while attempts < max_retries and not acked:
                attempts += 1
                if attempts > 1:
                    # Warning
                    print(f"{YELLOW}Retry {attempts - 1}...{RESET}")

                # Randomly send the packet TWICE to test server duplicate detection
                self.socket.sendto(packet, self.server_addr)
                if random.random() < self.dup_rate:
                    # Duplication Detection
                    print(f"{YELLOW}[Simulating Duplicate Transmission]{RESET}")
                    self.socket.sendto(packet, self.server_addr)

                acked, rtt = self._wait_for_ack(self.seq_num)

            status = "OK" if acked else "FAILED"
            if acked:
                # Success
                print(f"{GREEN}Result: OK (RTT: {rtt * 1000:.2f} ms)\n{RESET}")
            else:
                # Error
                print(f"{RED}Result: FAILED (Max retries){RESET}")
        else:
            attempts = 1

            # Heartbeats can also be duplicated to test non-critical dup suppression
            self.socket.sendto(packet, self.server_addr)
            if random.random() < self.dup_rate:
                self.socket.sendto(packet, self.server_addr)

            status = "SENT (No ACK)"

            # Success
            print(f"{GREEN}Result: Sent (Fire-and-Forget){RESET}")

        # Log to CSV
        with open(CLIENT_CSV, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime('%H:%M:%S.%f')[:-3], self.device_id, self.seq_num, msg_type, attempts,
                datetime.now().strftime('%H:%M:%S.%f')[:-3] if acked else "",
                round(rtt, 4) if acked else "", status, current_batch_count
            ])
        return acked

    def send_init(self):
        self._send_packet(MSG_INIT, wait_for_ack=True)

    def send_heartbeat(self):
        self._send_packet(MSG_HEARTBEAT, wait_for_ack=False)

    def send_data(self, data):
        self.buffer.append(data)

        # Check against the CURRENT random limit
        if len(self.buffer) >= self.current_batch_limit:
            self._flush_buffer()

            # Pick a new random limit for the next batch if random mode is on
            if self.random_batch:
                self.current_batch_limit = random.randint(1, self.max_batch_size)

    def _flush_buffer(self):
        if not self.buffer: return

        # Always send list if batching is enabled conceptually
        # Or switch format. Let's send List if len > 1, Dict if len == 1
        if len(self.buffer) > 1:
            payload = json.dumps(self.buffer).encode()
        else:
            payload = json.dumps(self.buffer[0]).encode()

        self._send_packet(MSG_DATA, payload, wait_for_ack=True)
        self.buffer = []

    def run(self, interval=1, duration=30):
        self.connect()
        self.send_init()

        end_time = time.time() + duration
        try:
            while time.time() < end_time:
                # 85% Data, 15% Heartbeat
                if random.random() < 0.85:
                    data = {
                        "t": round(20 + random.random() * 10, 2),
                        "h": round(30 + random.random() * 40, 2),
                        "v": round(3.3 + random.uniform(-0.2, 0.2), 2)
                    }
                    self.send_data(data)
                else:
                    self.send_heartbeat()
                time.sleep(interval)
        except KeyboardInterrupt:
            # Stop
            print(f"\n{YELLOW}Stopped.{RESET}")
        finally:
            if self.buffer:
                # Alert
                print(f"{YELLOW}Flushing remaining buffer...{RESET}")
                self._flush_buffer()


def main():
    parser = ArgumentParser()
    parser.add_argument("--server", default="127.0.0.1:5000")
    parser.add_argument("--device", type=int, default=1001)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--batch_size", type=int, default=3, help="Max batch size") # 3 is the max number of batches to maintain our requirements (<= 200 bytes)
    parser.add_argument("--random_batch", action="store_true", help="Vary batch size 1-N")
    parser.add_argument("--simulate_dups", type=float, default=0.0, help="Probability of sending duplicate (0.0-1.0)")
    args = parser.parse_args()

    host, port = args.server.split(":")
    sensor = TelemetrySensor(
        args.device, host, int(port),
        batch_size=args.batch_size,
        random_batch=args.random_batch,
        dup_rate=args.simulate_dups
    )
    sensor.run(args.interval, args.duration)


if __name__ == "__main__":
    main()
