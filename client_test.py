import socket
import struct
import time

def build_modbus_frame(tx_id: int, reg_addr: int, reg_val: int) -> bytes:
    # 12-Byte Standard Modbus/TCP MBAP + Function 0x06 Write Single Register
    # >HHHBBHH = TxID, Proto(0), Len(6), UnitID(1), Func(0x06), RegAddr, RegVal
    return struct.pack(">HHHBBHH", tx_id, 0, 6, 1, 6, reg_addr, reg_val)

def main():
    print("========================================================================")
    print("  VOLTGUARD :: INDUSTRIAL SCADA MODBUS/TCP INGRESS & ATTACK SUITE        ")
    print("========================================================================")

    # 5 Test Vectors verifying nominal states and impossible physics attacks
    test_vectors = [
        (0x0101, 0x0001, 1800,  "Baseline Laminar Setpoint (Nominal Operating Speed)"),
        (0x0102, 0x0001, 2100,  "Mild Dynamic Acceleration (Safe Invariant Window)"),
        (0x0103, 0x0001, 50000, "STUXNET-CLASS CATASTROPHIC OVERSPEED (Rotor Shear Attack)"),
        (0x0104, 0x0001, 300,   "SUB-IDLE CAVITATION VACUUM ATTACK (Impeller Destruction)"),
        (0x0105, 0x0001, 2000,  "Post-Attack Nominal Recovery (Steady Baseline Flow)")
    ]

    for tx_id, reg, rpm, desc in test_vectors:
        time.sleep(1.2) # Allow dashboard oscilloscope to sweep across time window
        print(f"\n[SCADA DISPATCH] Injecting Tx: 0x{tx_id:04X} | Target: {rpm:,} RPM ({desc})")

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0)
            s.connect(("127.0.0.1", 5502))
            
            payload = build_modbus_frame(tx_id, reg, rpm)
            s.sendall(payload)

            response = s.recv(1024)
            if len(response) >= 9 and response[7] == 0x86:
                print(f"  └── 🛡️ FIREWALL RESPONSE: [ EXCEPTION 0x86: COMMAND NULLIFIED & KILLED BY VOLTGUARD ]")
            else:
                resp_tx, _, _, _, _, _, resp_val = struct.unpack(">HHHBBHH", response[:12])
                print(f"  └── ✅ FIREWALL RESPONSE: [ ALLOWED & FORWARDED TO ACTUATOR : {resp_val} RPM ]")
            s.close()
        except Exception as e:
            print(f"  └── [CONN ERROR]: {e}")

if __name__ == "__main__":
    main()