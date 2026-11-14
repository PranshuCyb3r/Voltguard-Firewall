import socket
import struct
import time

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5502

def create_modbus_packet(tx_id, register_addr, value):
    protocol_id = 0x0000
    length = 0x0006
    unit_id = 0x01
    function_code = 0x06
    return struct.pack('>HHHBBHH', tx_id, protocol_id, length, unit_id, function_code, register_addr, value)

def send_packet(tx_id, register_addr, value, description):
    packet = create_modbus_packet(tx_id, register_addr, value)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect((SERVER_IP, SERVER_PORT))
        s.sendall(packet)
        resp = s.recv(1024)
        
        if len(resp) >= 8 and resp[7] == 0x86:
            verdict = "❌ [DROP / BLOCKED BY VOLTGUARD IPS]"
        else:
            verdict = "✅ [ALLOW / FORWARDED]"
            
        print(f"Tx: 0x{tx_id:04X} | Command: {value:5d} RPM | Verdict: {verdict} | Note: {description}")
        s.close()
    except Exception as e:
        print(f"Tx: 0x{tx_id:04X} | FAILED TO CONNECT: {e}")

if __name__ == "__main__":
    print("========================================================================")
    print("  VOLTGUARD :: WEEK 4 INDUSTRIAL ATTACK & INVARIANT TEST SUITE")
    print("  Testing: Kinematic Limits, Instant Surge & Cumulative Fatigue Breach")
    print("========================================================================")
    time.sleep(1.0)

    # 1. Nominal Steady Baseline
    send_packet(0x0101, 0x0001, 1800, "Nominal Laminar Baseline")
    time.sleep(0.3)

    # 2. Gradual Safe Operational Step
    send_packet(0x0102, 0x0001, 2000, "Gradual Safe Step (Within Slip Limits)")
    time.sleep(0.3)

    # 3. Direct Stuxnet Catastrophic Overpressure (50,000 RPM)
    send_packet(0x0103, 0x0001, 50000, "Catastrophic Rotor Ceiling Breach (>3600 RPM)")
    time.sleep(0.3)

    # 4. Impeller Cavitation Vacuum Attack (300 RPM)
    send_packet(0x0104, 0x0001, 300, "Cavitation Floor Breach (<500 RPM)")
    time.sleep(0.3)

    # 5. Stealth Low-and-Slow Attack Sequence (Sustained 3,400 RPM Stress)
    print("\n--- INJECTING STEALTH SUSTAINED FATIGUE ATTACK (3,400 RPM) ---")
    for i in range(5):
        tx = 0x0105 + i
        send_packet(tx, 0x0001, 3400, f"Sustained Stress Injection Step {i+1}")
        time.sleep(0.2)

    print("========================================================================")
