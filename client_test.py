import socket
import struct
import time

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5502

TEST_PACKETS = [
    {"name": "Normal Baseline Pump Speed",           "tx_id": 0x0101, "rpm": 1800},
    {"name": "Stuxnet Destructive Overspeed Attack", "tx_id": 0x0102, "rpm": 50000},
    {"name": "Sub-Idle Cavitation Attack",           "tx_id": 0x0103, "rpm": 300},
    {"name": "Valid Mid-Range Speed Transition",     "tx_id": 0x0104, "rpm": 2400},
    {"name": "Slight Over-Ceiling Actuation",         "tx_id": 0x0105, "rpm": 3800},
]

def build_modbus_frame(tx_id, register_address, rpm_value):
    return struct.pack(">HHHBBHH", tx_id, 0x0000, 0x0006, 0x01, 0x06, register_address, rpm_value)

def run_tests():
    print("========================================================================")
    print("        VoltGuard Real-Time Network Packet Injection Suite              ")
    print("========================================================================")

    for test in TEST_PACKETS:
        tx_id = test["tx_id"]
        rpm = test["rpm"]
        name = test["name"]

        packet = build_modbus_frame(tx_id, 0x0001, rpm)

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                s.connect((SERVER_IP, SERVER_PORT))
                s.sendall(packet)
                resp = s.recv(1024)

                print(f"[SCADA Transmission] {name} -> Commanded: {rpm:,} RPM")
                # Modbus Exception response has Function Code 0x86 (0x80 | 0x06) at byte index 7
                if len(resp) >= 8 and (resp[7] == 0x86 or resp[7] > 0x80):
                    print("  [FIREWALL VERDICT] -> STATUS: BLOCKED_BY_VOLTGUARD_PHYSICS_ENGINE")
                else:
                    print("  [FIREWALL VERDICT] -> STATUS: ALLOWED")
        except Exception as e:
            print(f"  [ERROR] Transmission failed: {e}")

        time.sleep(0.4)

    print("========================================================================")
    print("  Test execution completed. Check server.exe & voltguard.py for live sync! ")
    print("========================================================================")

if __name__ == "__main__":
    run_tests()