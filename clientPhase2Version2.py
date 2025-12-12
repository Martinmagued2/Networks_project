# feat: add stop-and-wait ARQ, retries, and CSV logging

#############################################################
## This version adds the _wait_for_ack logic. It pauses to ##
## verify the server received the packet. It also creates  ##
##      a CSV file to record RTT (Round Trip Time) and     ##
##                 success/failure status.                 ##
#############################################################

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
RED =    "\033[91m"
GREEN =  "\033[92m"
YELLOW = "\033[93m"
RESET =  "\033[0m"

os.system('')

# --- PROTOCOL CONSTANTS ---
HEADER_FORMAT = '<B H H L B'

MSG_INIT = 0
MSG_DATA = 1
MSG_HEARTBEAT = 2
MSG_ACK = 3

CLIENT_VERSION = 1
CLIENT_RTO = 0.5
MAX_RETRIES = 5
CLIENT_CSV = "client_measurements.csv"

# NEW: Init CSV
with open(CLIENT_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["send_time", "device_id", "seq", "msg_type", "attempts", "ack_time", "rtt", "status"])


class TelemetrySensor:
    def __init__(self, device_id, host, port):
        self.device_id = device_id
        self.server_addr = (host, port)
        self.seq_num = 0
        self.socket = None

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(CLIENT_RTO)
        print(f"{GREEN}Sensor {self.device_id} is ready.{RESET}")
        print(f"{GREEN}Target: {self.server_addr}{RESET}")

    def _wait_for_ack(self, seq):
        start = time.time()
        try:
            while True:
                data, _ = self.socket.recvfrom(1024)
                vmt, dev, rseq, ts, flags = struct.unpack(HEADER_FORMAT, data)
                # Check if it is ACK (Type 3) and matches our Seq
                if (vmt & 0x0F) == MSG_ACK and rseq == seq:
                    return True, time.time() - start
        except socket.timeout:
            return False, None

    def _send_packet(self, msg_type, payload=b'', wait_for_ack=True):
        self.seq_num += 1
        vmt = (CLIENT_VERSION << 4) | msg_type
        timestamp = int(time.time())
        header = struct.pack(HEADER_FORMAT, vmt, self.device_id, self.seq_num, timestamp, 0)
        packet = header + payload

        readable_type = {0: "INIT", 1: "DATA", 2: "HEARTBEAT"}.get(msg_type, "UNKNOWN")
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Seq:{self.seq_num} Type:{readable_type}")

        attempts = 0
        acked = False
        rtt = 0.0

        if wait_for_ack:
            while attempts < MAX_RETRIES and not acked:
                attempts += 1
                if attempts > 1: print(f"{YELLOW}Retry {attempts - 1}...{RESET}")

                self.socket.sendto(packet, self.server_addr)
                acked, rtt = self._wait_for_ack(self.seq_num)

            status = "OK" if acked else "FAILED"
            if acked:
                print(f"{GREEN}Result: OK (RTT: {rtt * 1000:.2f} ms){RESET}")
            else:
                print(f"{RED}Result: FAILED (Max retries){RESET}")
        else:
            attempts = 1
            self.socket.sendto(packet, self.server_addr)
            status = "SENT (No ACK)"
            print(f"{GREEN}Result: Sent (Fire-and-Forget){RESET}")

        # NEW: Log to CSV
        with open(CLIENT_CSV, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime('%H:%M:%S.%f')[:-3], self.device_id, self.seq_num, msg_type, attempts,
                datetime.now().strftime('%H:%M:%S.%f')[:-3] if acked else "",
                round(rtt, 4) if acked else "", status
            ])

    def send_init(self):
        self._send_packet(MSG_INIT, wait_for_ack=True)

    def send_heartbeat(self):
        self._send_packet(MSG_HEARTBEAT, wait_for_ack=False)  # Heartbeats usually don't need ACKs

    def send_data(self, data):
        payload = json.dumps(data).encode()
        self._send_packet(MSG_DATA, payload, wait_for_ack=True)

    def run(self, interval=1, duration=30):
        self.connect()
        self.send_init()
        end_time = time.time() + duration
        try:
            while time.time() < end_time:
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
            print(f"\n{YELLOW}Stopped.{RESET}")


def main():
    parser = ArgumentParser()
    parser.add_argument("--server", default="127.0.0.1:5000")
    parser.add_argument("--device", type=int, default=1001)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--duration", type=int, default=30)
    args = parser.parse_args()

    host, port = args.server.split(":")
    sensor = TelemetrySensor(args.device, host, int(port))
    sensor.run(args.interval, args.duration)


if __name__ == "__main__":
    main()