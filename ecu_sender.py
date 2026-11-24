"""
ecu_sender.py

ECU 1: Generates and transmits authenticated engine RPM messages.

This script also initializes the virtual CAN bus
and starts ECU 2 in a background thread.
"""

import argparse
import can
import time
import threading

from ecu_receiver import ECUReceiver
from mac_algorithms import ALGORITHMS, get_mac


# CAN configuration
CHANNEL = "CAN_BUS_1"
RPM_CAN_ID = 0x123

TRANSMISSION_INTERVAL = 1.0

# Demo only: shared pre-provisioned 128-bit key
KEY = bytes.fromhex("00112233445566778899aabbccddeeff")

# Valid CAN FD payload lengths
VALID_FD_LENGTHS = {0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 20, 24, 32, 48, 64}

# Simulated engine RPM values
RPM_VALUES = [
    800,
    1000,
    1200,
    1500,
    2000,
    2500,
    3000,
    3500,
    4000,
    4500
]


def parse_args():
    p = argparse.ArgumentParser(description="CAN ECU sender with selectable MAC")
    p.add_argument("--mac", choices=ALGORITHMS.keys(), default="none",
                   help="MAC algorithm used to authenticate messages")
    p.add_argument("--tag-len", type=int, default=16,
                   help="truncated tag length in bytes (4 + tag-len must be a valid CAN FD length)")
    p.add_argument("--interval", type=float, default=TRANSMISSION_INTERVAL,
                   help="seconds between messages")
    return p.parse_args()


def main():

    args = parse_args()
    mac = get_mac(args.mac, KEY, args.tag_len)

    if 4 + mac.tag_len not in VALID_FD_LENGTHS:
        raise SystemExit(
            f"Invalid --tag-len {args.tag_len}: payload of "
            f"{4 + mac.tag_len} bytes is not a valid CAN FD length."
        )

    print("===================================")
    print("   CAN BUS ECU COMMUNICATION")
    print("===================================")
    print(f"MAC: {mac.name} | tag length: {mac.tag_len} bytes\n")

    # Create two virtual CAN FD bus interfaces
    sender_bus = can.Bus(
        interface="virtual",
        channel=CHANNEL,
        fd=True
    )

    receiver_bus = can.Bus(
        interface="virtual",
        channel=CHANNEL,
        fd=True
    )

    # Event used to stop the receiver thread
    stop_event = threading.Event()

    # Initialize ECU 2 (now receives the same MAC configuration)
    receiver = ECUReceiver(receiver_bus, stop_event, mac)

    receiver_thread = threading.Thread(
        target=receiver.start,
        daemon=True
    )

    receiver_thread.start()

    print("\n[ECU 1] Transmitter started.\n")

    try:

        counter = 0

        for rpm in RPM_VALUES:

            # Encode RPM and counter into 4 bytes
            rpm_bytes = rpm.to_bytes(2, byteorder="big")
            counter_bytes = counter.to_bytes(2, byteorder="big")

            payload = rpm_bytes + counter_bytes

            # MAC over CAN ID || rpm || counter
            tag = mac.compute(RPM_CAN_ID.to_bytes(2, "big") + payload)

            # Construct CAN FD message: payload followed by tag
            message = can.Message(
                arbitration_id=RPM_CAN_ID,
                data=payload + tag,
                is_extended_id=False,
                is_fd=True
            )

            # Transmit message
            sender_bus.send(message)

            print(
                f"[ECU 1] Message sent | "
                f"Counter: {counter:04d} | "
                f"Engine RPM: {rpm} RPM | "
                f"Tag: {tag.hex() if tag else '-'}"
            )

            counter += 1

            time.sleep(args.interval)

    except KeyboardInterrupt:

        print("\n[ECU 1] Transmission interrupted.")

    finally:

        # Stop receiver
        stop_event.set()

        receiver_thread.join(timeout=2)

        sender_bus.shutdown()
        receiver_bus.shutdown()

        print("\n===================================")
        print("          SIMULATION END")
        print("===================================")

        print(
            f"Total messages received: "
            f"{receiver.get_received_count()}"
        )
        print(f"Total messages rejected: {receiver.rejected}")


if __name__ == "__main__":
    main()