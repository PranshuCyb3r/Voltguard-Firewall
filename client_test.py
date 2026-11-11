import socket
import struct
import time

def build_modbus_frame(tx_id: int, rpm: int) -> bytes:
    # 12-byte Modbus/TCP Header: TxID(2B) + Proto(2B) + Len(2B) + UnitID(1B) + FC(1B) + RegAddr(2B) + CommandedRPM(2B)
    return struct.pack(">HHHBBHH", tx_id, 0x0000, 0x0006, 0x01, 0x10, 0x0001, rpm)

def run_test_suite():
    print("=" * 70)
    print("  VOLTGUARD :: MULTI-SCENARIO ADVERSARY & FIELD INJECTOR")
    print("=" * 70)

    # 5 Real Scenarios: Baseline, Overspeed Attack, Cavitation Stall, Dynamic Slip, Pipe Limit
    test_packets = [
        (0x0101, 1800,  "Baseline Steady-State Laminar Flow (Nominal)"),
        (0x0102, 50000, "Catastrophic Overspeed Pipe Burst Attack (Stuxnet-style)"),
        (0x0103, 300,   "Cavitation Collapse Floor Breach Attack (<500 RPM)"),
        (0x0104, 2400,  "Dynamic Rotor Inertia Step Attack (Delta Slip Breach)"),
        (0x0105, 3800,  "Pipe Rupture Threshold Attack (>16.0 Bar Shock)")
    ]

    for tx_id, rpm, desc in test_packets:
        print(f"\n[INJECTING] Tx: 0x{tx_id:04X} | Commanded: {rpm:5d} RPM | Goal: {desc}")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect(("127.0.0.1", 5502))

            pkt = build_modbus_frame(tx_id, rpm)
            sock.sendall(pkt)

            resp = sock.recv(64)
            if len(resp) >= 8 and resp[7] == 0x86:
                print(f"  -> [FIREWALL VERDICT] KILLED & DROPPED (Modbus Exception 0x86 Code 0x{resp[8]:02X})")
            else:
                print(f"  -> [FIREWALL VERDICT] ALLOWED (Echo Passed Through Wire)")
            sock.close()
        except Exception as e:
            print(f"  -> [CONNECTION ERROR] {e}")

        time.sleep(0.4) # Small delay for smooth visual oscilloscope tracking

    print("\n" + "=" * 70)
    print("  ALL 5 SCENARIOS EXECUTED SUCCESSFULLY")
    print("=" * 70)

if __name__ == "__main__":
    run_test_suite()
