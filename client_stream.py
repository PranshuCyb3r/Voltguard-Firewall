import socket
import struct
import time
import random

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5502

def make_modbus_fc06(tx_id, reg, value):
    return struct.pack(">HHHBBHH", tx_id, 0, 6, 1, 6, reg, value)

print("=" * 70)
print("  VOLTGUARD :: AUTONOMOUS SCADA PLC CONTINUOUS FIELD STREAMER")
print("  TARGET: 127.0.0.1:5502 (Modbus-TCP) | INTERVAL: 600ms")
print("=" * 70)

tx_counter = 0x0100

try:
    while True:
        tx_counter = (tx_counter + 1) & 0xFFFF
        if tx_counter == 0:
            tx_counter = 0x0100

        attack_roll = random.random()

        if attack_roll < 0.70:
            rpm = random.randint(1790, 1810)
            tag = "NOMINAL BASELINE"
        elif attack_roll < 0.80:
            rpm = 2100
            tag = "SAFE LOAD INCREASE (2,100 RPM)"
        elif attack_roll < 0.88:
            rpm = random.choice([4800, 50000, 42000])
            tag = "CRITICAL: STUXNET ROTOR OVERSPEED ATTACK"
        elif attack_roll < 0.94:
            rpm = random.choice([200, 300, 150])
            tag = "CRITICAL: CAVITATION VAPOR COLLAPSE ATTACK"
        else:
            rpm = 4600
            tag = "CRITICAL: WATER HAMMER SURGE ATTACK"

        packet = make_modbus_fc06(tx_counter, 0x0001, rpm)

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((SERVER_IP, SERVER_PORT))
            s.sendall(packet)
            s.close()
            print(f"[{time.strftime('%H:%M:%S')}] Tx: 0x{tx_counter:04X} | Sent: {rpm:5d} RPM | Flow: {tag}")
        except ConnectionRefusedError:
            print(f"[WAITING] Server offline on {SERVER_IP}:{SERVER_PORT}... Retrying in 1s")
            time.sleep(1.0)
            continue
        except Exception as e:
            print(f"[ERROR] Stream interrupted: {e}")

        time.sleep(0.6)

except KeyboardInterrupt:
    print("\n[STOPPED] Continuous SCADA Field Stream terminated by operator.")