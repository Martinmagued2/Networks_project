# feat: init client with binary header protocol (fire-and-forget)

#############################################################
## This version establishes the struct based binary header ##
##  (Version, Type, ID, Seq, Timestamp) but sends packets  ##
##  immediately without waiting for ACKs or batching data. ##
#############################################################

import os
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
CLIENT_VERSION = 1


class TelemetrySensor:
    def __init__(self, device_id, host, port):
        self.device_id = device_id
        self.server_addr = (host, port)
        self.seq_num = 0
        self.socket = None

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"{GREEN}Sensor {self.device_id} is ready.{RESET}")
        print(f"{GREEN}Target: {self.server_addr}{RESET}")

    def _send_packet(self, msg_type, payload=b''):
        """Packs a binary header and sends the packet (Fire-and-Forget)"""
        self.seq_num += 1
        vmt = (CLIENT_VERSION << 4) | msg_type
        timestamp = int(time.time())

        # Pack header: VMT (version & type), DeviceID, Seq, Timestamp, Flags
        header = struct.pack(HEADER_FORMAT, vmt, self.device_id, self.seq_num, timestamp, 0)
        packet = header + payload

        # Send immediately
        self.socket.sendto(packet, self.server_addr)

        readable_type = {0: "INIT", 1: "DATA", 2: "HEARTBEAT"}.get(msg_type, "UNKNOWN")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Seq:{self.seq_num} Type:{readable_type} (Sent)")

    def send_init(self):
        self._send_packet(MSG_INIT)

    def send_heartbeat(self):
        self._send_packet(MSG_HEARTBEAT)

    def send_data(self, data):
        # Phase 1: No batching, send immediately
        payload = json.dumps(data).encode()
        self._send_packet(MSG_DATA, payload)

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