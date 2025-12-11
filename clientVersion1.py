##########################################
##  This part establishes the imports,  ##
##   configuration constants, and the   ##
##   base TelemetrySensor class with    ##
##   initialization, connection, and    ##
##  the low-level message sending logic ##
##########################################

#!/usr/bin/env python3
"""
TinyTelemetry Client (Sensor) - Mixed Version (with Batching)

Combines the OOP style of Script 1 with features (argparse,
heartbeat, voltage) from Script 2, using a simple JSON protocol.

New feature: Supports batching readings via --batch-size.
"""

import socket
import time
import json
import random
from datetime import datetime
from argparse import ArgumentParser

# Define simple message types
MSG_INIT = "INIT"
MSG_DATA = "DATA"
MSG_HEARTBEAT = "HEARTBEAT"
BATCH_SIZE = 1  # Default batch size


class TelemetrySensor:
    """
    Simulates an IoT sensor sending telemetry data over UDP.
    Can batch multiple readings into a single message.
    """

    def __init__(self, device_id, server_host, server_port):
        self.device_id = device_id
        self.server_host = server_host
        self.server_port = server_port
        self.server_addr = (server_host, server_port)
        self.socket = None
        self.seq_num = 0

        # Batching attributes
        self.batch_size = BATCH_SIZE
        self.reading_batch = []

    def connect(self):
        """Create UDP socket"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"[SENSOR] TinyTelemetry Sensor (Batching v4)")
        print(f"[SENSOR] Device ID: {self.device_id}")
        print(f"[SENSOR] Target server: {self.server_host}:{self.server_port}")
        print("-" * 80)

    def _get_time(self):
        """Helper to get formatted timestamp"""
        return datetime.now().strftime('%H:%M:%S')

    def _send_message(self, msg_type, payload=None):
        """
        Internal helper to build, serialize, and send a message.
        Uses a simple JSON structure for the entire message.
        """
        self.seq_num += 1
        message_dict = {
            "device_id": self.device_id,
            "seq_num": self.seq_num,
            "timestamp": datetime.now().isoformat(),
            "msg_type": msg_type,
            "payload": payload or {}
        }

        try:
            message_bytes = json.dumps(message_dict).encode('utf-8')
            self.socket.sendto(message_bytes, self.server_addr)
            return True
        except Exception as e:
            print(f"[{self._get_time()}] [ERROR] Failed to send message: {e}")
            return False

def main():
    parser = ArgumentParser(description="TinyTelemetry Sensor (Batching v4)")
    parser.add_argument("--device-id", type=int, required=True,
                        help="Unique device ID")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Server IP/hostname")
    parser.add_argument("--port", type=int, default=5000,
                        help="Server UDP port")
    parser.add_argument("--interval", type=float, default=2.0,
                        help="Interval between sensor readings")
    parser.add_argument("--heartbeat-interval", type=float, default=10.0,
                        help="Interval between heartbeat messages")
    parser.add_argument("--batch-size", type=int, default=1,
                        help="Number of readings to batch before sending")

    args = parser.parse_args()

    # Create sensor instance
    sensor = TelemetrySensor(args.device_id, args.host, args.port)
    sensor.batch_size = args.batch_size
    sensor.connect()

    last_heartbeat = time.time()

    print(f"[SENSOR] Batch size: {sensor.batch_size}")
    print("[SENSOR] Starting event loop...\n")

    # Send INIT message
    sensor._send_message(MSG_INIT, {"status": "online"})

    while True:
        time.sleep(args.interval)

        # Generate fake sensor reading
        reading = {
            "temperature": round(random.uniform(20.0, 35.0), 2),
            "humidity": round(random.uniform(30.0, 70.0), 2),
            "voltage": round(random.uniform(3.5, 4.2), 2)
        }

        sensor.reading_batch.append(reading)

        print(f"[{sensor._get_time()}] Queued reading: {reading}")

        # If batch full → send DATA message
        if len(sensor.reading_batch) >= sensor.batch_size:
            payload = {"batch": sensor.reading_batch}
            sensor._send_message(MSG_DATA, payload)
            print(f"[{sensor._get_time()}] Sent batch ({len(sensor.reading_batch)} readings)")
            sensor.reading_batch.clear()

        # Heartbeat logic
        if time.time() - last_heartbeat >= args.heartbeat_interval:
            sensor._send_message(MSG_HEARTBEAT, {"status": "alive"})
            print(f"[{sensor._get_time()}] Sent HEARTBEAT")
            last_heartbeat = time.time()

if __name__ == "__main__":
    main()
