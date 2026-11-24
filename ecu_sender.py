
"""
ecu_sender.py

ECU 1: Generates and transmits engine RPM messages.

This script also initializes the virtual CAN bus
and starts ECU 2 in a background thread.
"""

import can
import time
import threading

from ecu_receiver import ECUReceiver


# CAN configuration
CHANNEL = "CAN_BUS_1"
RPM_CAN_ID = 0x123

TRANSMISSION_INTERVAL = 1.0

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


def main():

    print("===================================")
    print("   CAN BUS ECU COMMUNICATION")
    print("===================================")

    # Create two virtual CAN bus interfaces
    sender_bus = can.Bus(
        interface="virtual",
        channel=CHANNEL
    )

    receiver_bus = can.Bus(
        interface="virtual",
        channel=CHANNEL
    )

    # Event used to stop the receiver thread
    stop_event = threading.Event()

    # Initialize ECU 2
    receiver = ECUReceiver(receiver_bus, stop_event)

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

            # Construct CAN message
            message = can.Message(
                arbitration_id=RPM_CAN_ID,
                data=payload,
                is_extended_id=False
            )

            # Transmit message
            sender_bus.send(message)

            print(
                f"[ECU 1] Message sent | "
                f"Counter: {counter:04d} | "
                f"Engine RPM: {rpm} RPM"
            )

            counter += 1

            time.sleep(TRANSMISSION_INTERVAL)

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


if __name__ == "__main__":
    main()
