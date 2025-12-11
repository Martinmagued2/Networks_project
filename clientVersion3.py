##############################################
##  This final version adds the run() loop  ##
## (which drives the timing and randomness) ##
##  and the main() function with argparse   ##
##     to make the script executable.       ##
##############################################

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

    def send_init(self):
        """Send an INIT message to the server."""
        if self._send_message(MSG_INIT):
            print(f"[{self._get_time()}] Sent INIT (seq: {self.seq_num})")

    def send_heartbeat(self):
        """
        Send a HEARTBEAT message, but flush any pending data first.
        """
        self.flush_data_batch()  # Send any pending data before heartbeat
        if self._send_message(MSG_HEARTBEAT):
            print(f"[{self._get_time()}] Sent HEARTBEAT (seq: {self.seq_num})")

    def send_data_batch(self, readings_list):
        """
        Send a DATA message with a list (batch) of sensor readings.
        """
        if not readings_list:
            return

        payload_dict = {
            'readings': readings_list
        }

        if self._send_message(MSG_DATA, payload_dict):
            print(f"[{self._get_time()}] Sent DATA (seq: {self.seq_num}): "
                  f"Batch of {len(readings_list)} readings")

    def flush_data_batch(self):
        """
        Helper function to send any pending readings in the batch.
        """
        if not self.reading_batch:
            return

        self.send_data_batch(self.reading_batch)
        self.reading_batch = []  # Clear batch after sending

    def simulate_sensor_readings(self):
        """
        Generate realistic sensor readings, borrowing from both scripts.
        """
        # Simulate temperature: 20-30 C
        temperature = 20.0 + random.random() * 10.0

        # Simulate humidity: 30-70%
        humidity = 30.0 + random.random() * 40.0

        # Simulate voltage: 3.1 - 3.5V
        voltage = 3.3 + random.uniform(-0.2, 0.2)

        return temperature, humidity, voltage

    def run(self, interval=1.0, duration=60, batch_size=1):
        """
        Run sensor simulation.

        Args:
            interval: Reporting interval in seconds.
            duration: Total duration in seconds.
            batch_size: Number of readings to collect before sending.
        """
        self.batch_size = batch_size
        print(f"[SENSOR] Batch size set to: {self.batch_size}")

        try:
            self.connect()

            # Send initial INIT message
            self.send_init()

            print(f"\n[SENSOR] Starting data transmission (interval: {interval}s, duration: {duration}s)")
            print("-" * 80)

            start_time = time.time()
            end_time = start_time + duration

            while time.time() < end_time:
                # Use logic from Script 2: 85% chance for DATA, 15% for HEARTBEAT
                if random.random() < 0.85:
                    # Generate sensor data
                    temp, hum, volt = self.simulate_sensor_readings()

                    # Create reading dict
                    reading = {
                        'temperature': round(temp, 2),
                        'humidity': round(hum, 2),
                        'voltage': round(volt, 2)
                    }

                    # Add to batch
                    self.reading_batch.append(reading)

                    # If batch is full, send it
                    if len(self.reading_batch) >= self.batch_size:
                        self.flush_data_batch()  # This will send and clear the batch
                else:
                    # Send a heartbeat (which flushes data first)
                    self.send_heartbeat()

                # Wait for the next interval
                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n[SENSOR] Interrupted by user")
        except Exception as e:
            print(f"[ERROR] Sensor error: {e}")
        finally:
            print("-" * 80)
            print(f"[SENSOR] Simulation ended. Flushing final batch...")
            # Send any remaining data before closing
            self.flush_data_batch()

            if self.socket:
                self.socket.close()
            print(f"[SENSOR] Transmission complete. Sent {self.seq_num} messages total.")

def main():
    """Main entry point"""
    # Use argparse (from Script 2) for robust argument parsing
    parser = ArgumentParser(description="TinyTelemetry Sensor (with Batching)")
    parser.add_argument("--server", default="127.0.0.1:5000",
                        help="Server address host:port (default: 127.0.0.1:5000)")
    parser.add_argument("--device", type=int, default=1001,
                        help="Numeric Device ID (default: 1001)")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="Send interval in seconds (default: 1.0)")
    parser.add_argument("--duration", type=int, default=60,
                        help="Total simulation duration in seconds (default: 60)")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE,
                        help="Number of readings to batch per message (default: 1)")
    args = parser.parse_args()

    try:
        host, port_s = args.server.split(":")
        port = int(port_s)
    except ValueError:
        print(f"Error: Invalid server format '{args.server}'. Use 'host:port'.")
        return
    except Exception as e:
        print(f"Error parsing server: {e}")
        return

    # Create and run the sensor
    sensor = TelemetrySensor(args.device, host, port)
    sensor.run(interval=args.interval,
               duration=args.duration,
               batch_size=args.batch_size)


if __name__ == '__main__':
    main()