import sys
import socket
import struct
import time
from collections import deque
from PyQt6 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

# Strict 32-Byte Wire Format:
# uint64_t timestamp_ns (8 bytes) -> Q
# uint16_t transaction_id (2 bytes) -> H
# uint16_t target_register (2 bytes) -> H
# float    injected_rpm (4 bytes)   -> f
# float    joukowsky_bar (4 bytes)  -> f
# uint8_t  verdict (1 byte)         -> B
# uint8_t  reserved[11] (11 bytes)  -> 11s
# Total = 8 + 2 + 2 + 4 + 4 + 1 + 11 = 32 Bytes
FRAME_FORMAT = "<QHHffB7s"
FRAME_SIZE = struct.calcsize(FRAME_FORMAT)
TELEMETRY_PORT = 5555

class VoltGuardTacticalRedWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoltGuard - Industrial OT Physics Firewall (Tactical Red)")
        self.resize(1100, 680)
        self.setStyleSheet("background-color: #0a0e17; color: #ffffff; font-family: 'Segoe UI', Consolas, sans-serif;")

        self.max_points = 120
        self.time_points = deque(maxlen=self.max_points)
        self.rpm_data = deque(maxlen=self.max_points)
        self.shock_data = deque(maxlen=self.max_points)
        self.start_time = time.time()

        # Non-blocking UDP Socket bound to 0.0.0.0 to capture all local loopback traffic
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_sock.bind(("0.0.0.0", TELEMETRY_PORT))
        self.udp_sock.setblocking(False)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header with Red Tactical Accents
        header_layout = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("VOLTGUARD :: RED TACTICAL OT FIREWALL & JOUKOWSKY STREAM")
        title.setStyleSheet("font-size: 15px; font-weight: 800; color: #ffffff; letter-spacing: 1px;")
        header_layout.addWidget(title)

        self.lbl_rx_status = QtWidgets.QLabel("PACKET STREAM: ACTIVE [PORT 5555]")
        self.lbl_rx_status.setStyleSheet("font-size: 11px; font-weight: bold; color: #22c55e; background: #052e16; padding: 4px 10px; border-radius: 4px;")
        header_layout.addWidget(self.lbl_rx_status, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        badge = QtWidgets.QLabel("AIR-GAPPED ENCLAVE :: ENFORCED")
        badge.setStyleSheet("font-size: 11px; font-weight: bold; color: #ffffff; background: #dc2626; padding: 4px 10px; border-radius: 4px; margin-left: 8px;")
        header_layout.addWidget(badge, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        main_layout.addLayout(header_layout)

        # Metric KPI Cards (Red and Crisp White theme)
        cards_layout = QtWidgets.QHBoxLayout()
        card_base = "background-color: #181b25; border: 1px solid #353943; border-radius: 8px; padding: 10px 14px; font-size: 13px; font-weight: bold;"

        self.lbl_rpm = QtWidgets.QLabel("RPM: WAITING...")
        self.lbl_rpm.setStyleSheet(f"{card_base} color: #ffffff; border-left: 4px solid #ef4444;")
        
        self.lbl_shock = QtWidgets.QLabel("Surge Shock: -- Bar")
        self.lbl_shock.setStyleSheet(f"{card_base} color: #ffffff; border-left: 4px solid #f87171;")

        self.lbl_tripwire = QtWidgets.QLabel("Tripwire Ceiling: 3,600 RPM")
        self.lbl_tripwire.setStyleSheet(f"{card_base} color: #f8fafc;")

        self.lbl_verdict = QtWidgets.QLabel("Verdict: LISTENING...")
        self.lbl_verdict.setStyleSheet(f"{card_base} color: #94a3b8;")

        for w in [self.lbl_rpm, self.lbl_shock, self.lbl_tripwire, self.lbl_verdict]:
            cards_layout.addWidget(w)
        main_layout.addLayout(cards_layout)

        # Plot Widget
        pg.setConfigOptions(antialias=True)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#05080e")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.setLabel('bottom', "Relative Time (Seconds)", color='#cbd5e1')
        self.plot_widget.setLabel('left', "Shaft RPM", color='#ffffff')
        self.plot_widget.setYRange(0, 55000, padding=0.04)
        self.plot_widget.addLegend(offset=(15, 15))

        # Red Max Limit Line (3600 RPM)
        self.limit_line = pg.InfiniteLine(
            pos=3600, angle=0,
            pen=pg.mkPen(color='#ef4444', width=2, style=QtCore.Qt.PenStyle.DashLine),
            label="TRIPWIRE CEILING: 3,600 RPM",
            labelOpts={'position': 0.85, 'color': '#ef4444', 'movable': False}
        )
        self.plot_widget.addItem(self.limit_line)

        # Telemetry White/Red Curve
        self.rpm_curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#ffffff', width=2.5),
            symbol='o', symbolSize=7, symbolBrush='#ef4444',
            name="Commanded Motor RPM"
        )
        main_layout.addWidget(self.plot_widget)

        # Poll Timer (20ms = 50 FPS)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.process_packets)
        self.timer.start(20)

    def process_packets(self):
        while True:
            try:
                data, addr = self.udp_sock.recvfrom(2048)
                if not data:
                    break

                # If packet matches or is larger than 32 bytes
                if len(data) >= FRAME_SIZE:
                    ts_ns, tx_id, reg, rpm, shock_bar, verdict, _ = struct.unpack(FRAME_FORMAT, data[:FRAME_SIZE])
                    
                    elapsed = round(time.time() - self.start_time, 2)
                    self.time_points.append(elapsed)
                    self.rpm_data.append(rpm)
                    self.shock_data.append(shock_bar)

                    # Update Curve
                    self.rpm_curve.setData(list(self.time_points), list(self.rpm_data))
                    
                    # Update Cards
                    self.lbl_rpm.setText(f"RPM: {rpm:,.0f} (Reg 0x{reg:04X})")
                    self.lbl_shock.setText(f"Surge Shock: {shock_bar:.2f} Bar")

                    if verdict == 1:
                        self.lbl_verdict.setText(f"Verdict: [ ALLOWED ] (Tx: 0x{tx_id:X})")
                        self.lbl_verdict.setStyleSheet("background-color: #14532d; border: 1px solid #22c55e; border-radius: 8px; padding: 10px 14px; font-size: 13px; font-weight: bold; color: #ffffff;")
                        self.lbl_tripwire.setText("State: NOMINAL LAMINAR")
                        self.lbl_tripwire.setStyleSheet("background-color: #181b25; border: 1px solid #22c55e; border-radius: 8px; padding: 10px 14px; font-size: 13px; font-weight: bold; color: #4ade80;")
                    else:
                        self.lbl_verdict.setText("Verdict: [ ATTACK INTERCEPTED / DROP ]")
                        self.lbl_verdict.setStyleSheet("background-color: #7f1d1d; border: 1px solid #ef4444; border-radius: 8px; padding: 10px 14px; font-size: 13px; font-weight: bold; color: #ffffff;")
                        self.lbl_tripwire.setText("State: TRIPWIRE CEILING BREACH")
                        self.lbl_tripwire.setStyleSheet("background-color: #7f1d1d; border: 1px solid #ef4444; border-radius: 8px; padding: 10px 14px; font-size: 13px; font-weight: bold; color: #fca5a5;")
                    
                    print(f"[QT VISUALIZER] Plotted: TxID=0x{tx_id:X} | RPM={rpm:,.0f} | Shock={shock_bar:.2f} Bar | Verdict={'ALLOW' if verdict==1 else 'DROP'}")
                else:
                    print(f"[WARNING] Received malformed packet of length {len(data)}, expected {FRAME_SIZE}")
            except BlockingIOError:
                break
            except Exception as e:
                print(f"[RECV ERROR] {e}")
                break

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = VoltGuardTacticalRedWindow()
    window.show()
    sys.exit(app.exec())