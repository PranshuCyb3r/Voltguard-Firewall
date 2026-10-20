import socket
import struct
import time

TARGET_HOST = "127.0.0.1"
TARGET_PORT = 5502

def send_modbus_rpm(tx_id: int, rpm_value: int) -> str:
    """Builds a Modbus TCP frame (MBAP Header + Write Single Register PDU) and transmits."""
    # MBAP: TxID (2B), Protocol=0 (2B), Length=6 (2B), UnitID=1 (1B)
    # PDU: Function Code=0x06 (1B), Register Address=0x0001 (2B), Value=RPM (2B)
    packet = struct.pack(">HHHBBHH", tx_id, 0x0000, 6, 1, 0x06, 0x0001, rpm_value)
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((TARGET_HOST, TARGET_PORT))
            s.sendall(packet)
            response = s.recv(1024).decode('utf-8', errors='ignore').strip()
            return response
    except ConnectionRefusedError:
        return "ERROR: VoltGuard Server is not running on port 5502."
    except Exception as e:
        return f"ERROR: {e}"

def run_test_suite():
    print("========================================================================")
    print("        VoltGuard Real-Time Network Packet Injection Suite              ")
    print("========================================================================")
    
    test_cases = [
        (101, 1800, "Normal SCADA Setpoint (1,800 RPM)", "EXPECT: ALLOW"),
        (102, 50000, "Stuxnet-Style Overspeed Attack (50,000 RPM)", "EXPECT: BLOCKED"),
        (103, 300,  "Sub-Idle Cavitation Command (300 RPM)", "EXPECT: BLOCKED"),
        (104, 2400, "Valid Mid-Range Speed Transition (2,400 RPM)", "EXPECT: ALLOW")
    ]

    for tx_id, rpm, description, expectation in test_cases:
        print(f"\n[SCADA Transmission] {description} -> Payload: {rpm} RPM ({expectation})")
        resp = send_modbus_rpm(tx_id, rpm)
        print(f"  [FIREWALL RESPONSE] -> {resp}")
        time.sleep(0.8)

    print("\n========================================================================")
    print("  Test execution completed. Check server terminal for real-time logs!   ")
    print("========================================================================")

if __name__ == "__main__":
    run_test_suite()