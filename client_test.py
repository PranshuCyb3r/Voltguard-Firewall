import socket
import struct
import time

def send_modbus_rpm(tx_id, rpm_value):
    # Modbus TCP Frame Header (MBAP Header) + PDU
    # Transaction ID (2B), Protocol ID (2B = 0), Length (2B = 6), Unit ID (1B = 1), Function Code (1B = 0x06)
    # Register Address (2B = 0x0001), Register Value (2B = requested RPM)
    packet = struct.pack(">HHHBBHH", tx_id, 0x0000, 6, 1, 0x06, 0x0001, rpm_value)
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', 5502))
        s.sendall(packet)
        response = s.recv(1024).decode('utf-8', errors='ignore').strip()
        s.close()
        return response
    except Exception as e:
        return f"Error: {e}"

print("========================================================================")
print("     VoltGuard Live Network Injection Test Client                      ")
print("========================================================================")

# Test 1: Normal Industrial Command
print("\n[SCADA Operator] Sending Normal Command: 1,800 RPM...")
res1 = send_modbus_rpm(101, 1800)
print(f"  [FIREWALL RESPONSE] -> {res1}")

time.sleep(1)

# Test 2: Malicious Cyber Attack (Stuxnet style Catastrophic Overspeed)
print("\n[ATTACKER SCRIPT] Sending Malicious Exploit Packet: 50,000 RPM...")
res2 = send_modbus_rpm(102, 50000)
print(f"  [FIREWALL RESPONSE] -> {res2}")

print("\n========================================================================")
print("  Network Injection Complete! Check Server Terminal for Real-Time Logs  ")
print("========================================================================")