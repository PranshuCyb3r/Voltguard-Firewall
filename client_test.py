import socket
import struct
import time

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5502

def build_modbus_write_packet(tx_id: int, reg_addr: int, reg_val: int) -> bytes:
    # Modbus TCP Header (MBAP): TxID(2), ProtoID(2=0), Length(2=6), UnitID(1=1)
    # PDU: FunctionCode(1=0x06 Write Single Register), Address(2), Value(2)
    mbap = struct.pack(">HHHB", tx_id, 0x0000, 6, 1)
    pdu = struct.pack(">BHH", 0x06, reg_addr, reg_val)
    return mbap + pdu

def send_scada_command(test_label: str, tx_id: int, rpm: int, delay_after: float = 1.0):
    print(f"\n[SCADA Transmission] {test_label} -> Commanded: {rpm:,} RPM")
    packet = build_modbus_write_packet(tx_id, 0x0001, rpm)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    try:
        sock.connect((SERVER_HOST, SERVER_PORT))
        sock.sendall(packet)
        response = sock.recv(1024).decode('utf-8', errors='ignore').strip()
        print(f"  [FIREWALL VERDICT] -> {response}")
    except ConnectionRefusedError:
        print("  [ERROR] Connection Refused! Is server.exe running on port 5502?")
    except socket.timeout:
        print("  [ERROR] Server socket timed out.")
    except Exception as e:
        print(f"  [ERROR] Failed: {e}")
    finally:
        sock.close()
    
    time.sleep(delay_after)

def run_test_suite():
    print("=" * 72)
    print("        VoltGuard Real-Time Network Packet Injection Suite              ")
    print("=" * 72)

    # 1. Normal Base SCADA command
    send_scada_command("Normal Baseline Pump Speed", tx_id=0x0101, rpm=1800, delay_after=1.2)

    # 2. Stuxnet-Style Destructive Overspeed
    send_scada_command("Stuxnet Destructive Overspeed Attack", tx_id=0x0102, rpm=50000, delay_after=1.2)

    # 3. Sub-Idle Low-Frequency Cavitation Attack
    send_scada_command("Sub-Idle Cavitation Attack", tx_id=0x0103, rpm=300, delay_after=1.2)

    # 4. Valid Mid-Range Operating Transition
    send_scada_command("Valid Mid-Range Speed Transition", tx_id=0x0104, rpm=2400, delay_after=1.2)

    # 5. Over-Ceiling Dynamic Transient
    send_scada_command("Slight Over-Ceiling Actuation", tx_id=0x0105, rpm=3800, delay_after=0.5)

    print("=" * 72)
    print("  Test execution completed. Check server.exe & voltguard.py for live sync! ")
    print("=" * 72)

if __name__ == "__main__":
    run_test_suite()