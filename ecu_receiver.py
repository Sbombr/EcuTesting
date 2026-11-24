"""
ecu_receiver.py

ECU 2: Receives, authenticates and interprets engine RPM messages.
"""

import can
import threading


RPM_CAN_ID = 0x123
PAYLOAD_LEN = 4   # 2 bytes RPM + 2 bytes counter


class ECUReceiver:

    def __init__(self, bus, stop_event, mac):
        self.bus = bus
        self.stop_event = stop_event
        self.mac = mac
        self.received_messages = 0
        self.rejected = 0
        self.last_counter = -1

    def start(self):

        print("\n[ECU 2] Receiver started. Waiting for messages...\n")

        while not self.stop_event.is_set():

            message = self.bus.recv(timeout=0.5)

            if message is None:
                continue

            # Ignore messages with unexpected CAN IDs
            if message.arbitration_id != RPM_CAN_ID:
                continue

            # Check expected length: payload + truncated tag
            expected = PAYLOAD_LEN + self.mac.tag_len
            if len(message.data) != expected:
                self.rejected += 1
                print("[ECU 2] Invalid message length!")
                continue

            payload = bytes(message.data[:PAYLOAD_LEN])
            tag = bytes(message.data[PAYLOAD_LEN:])

            # Verify MAC over CAN ID || rpm || counter
            if self.mac.tag_len and not self.mac.verify(
                RPM_CAN_ID.to_bytes(2, "big") + payload, tag
            ):
                self.rejected += 1
                print("[ECU 2] MAC verification FAILED, message dropped")
                continue

            # Decode RPM and message counter
            rpm = int.from_bytes(payload[0:2], byteorder="big")
            counter = int.from_bytes(payload[2:4], byteorder="big")

            # Replay protection: counter must strictly increase
            if counter <= self.last_counter:
                self.rejected += 1
                print("[ECU 2] Replay detected, message dropped")
                continue
            self.last_counter = counter

            self.received_messages += 1

            print(
                f"[ECU 2] Message received | "
                f"Counter: {counter:04d} | "
                f"Engine RPM: {rpm} RPM | "
                f"Auth: {'OK' if self.mac.tag_len else 'none'}"
            )

    def get_received_count(self):
        return self.received_messages