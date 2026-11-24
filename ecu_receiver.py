
"""
ecu_receiver.py

ECU 2: Receives and interprets engine RPM messages.
"""

import can
import threading


RPM_CAN_ID = 0x123


class ECUReceiver:

    def __init__(self, bus, stop_event):
        self.bus = bus
        self.stop_event = stop_event
        self.received_messages = 0

    def start(self):

        print("\n[ECU 2] Receiver started. Waiting for messages...\n")

        while not self.stop_event.is_set():

            message = self.bus.recv(timeout=0.5)

            if message is None:
                continue

            # Ignore messages with unexpected CAN IDs
            if message.arbitration_id != RPM_CAN_ID:
                continue

            # Check expected payload length
            if len(message.data) != 4:
                print("[ECU 2] Invalid message length!")
                continue

            # Decode RPM and message counter
            rpm = int.from_bytes(message.data[0:2], byteorder="big")
            counter = int.from_bytes(message.data[2:4], byteorder="big")

            self.received_messages += 1

            print(
                f"[ECU 2] Message received | "
                f"Counter: {counter:04d} | "
                f"Engine RPM: {rpm} RPM"
            )

    def get_received_count(self):
        return self.received_messages
