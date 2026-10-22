import sys
import socket
import struct
import time
from collections import deque
from PyQt6 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

# 32-Byte Packed Telemetry Frame Struct:
# uint64_t timestamp_ns (Q)
# uint16_t transaction_id (H)
# uint16_t target_register (H)
# float    injected_rpm (f)
# float    joukowsky_bar (f)
# uint8_t  verdict (B)
# uint8_t  reserved[7] (7s)
FRAME_FORMAT = "<QHHffB7s"
FRAME_SIZE = struct.calcsize(FRAME_FORMAT)

TELEMETRY_PORT = 5555

class VoltGuardQtWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoltGuard - Week 2: Rudimentary Qt Telemetry Visualizer")
        self.resize(1000, 620)
        self.setStyleSheet("background-color: #0f131c; color: #e2e8f0; font-family: 'Segoe UI', Consolas, monospace;")

        # Data Buffers (rolling window)
        self.max_points = 60
        self.time_points = deque(maxlen=self.max_points)
        self.rpm_data = deque(maxlen=self.max_points)
        self.shock_data = deque(maxlen=self.max_points)
        self.start_time = time.time()

        # Setup Non-blocking UDP Socket for Telemetry Ingestion
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception:
            pass
        self.udp_sock.bind(("127.0.0.1", TELEMETRY_PORT))
        self.udp_sock.setblocking(False)

        # Central Widget & Main Layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Top Header Banner
        header = QtWidgets.QLabel("VOLTGUARD OT FIREWALL :: QT TELEMETRY STREAM & GRAPH")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #06b6d4; letter-spacing: 1px;")
        main_layout.addWidget(header)

        # 2. Live Telemetry KPI Cards
        metric_layout = QtWidgets.QHBoxLayout()
        metric_layout.setSpacing(12)

        self.lbl_rpm = QtWidgets.QLabel("RPM: WAITING...")
        self.lbl_shock = QtWidgets.QLabel("Pressure Shock: -- Bar")
        self.lbl_verdict = QtWidgets.QLabel("Verdict: LISTENING...")

        # Base style for cards
        base_card_style = "background-color: #181c24; border: 1px solid #334155; border-radius: 8px; padding: 12px; font-size: 13px; font-weight: bold;"
        
        self.lbl_rpm.setStyleSheet(f"{base_card_style} color: #38bdf8;")
        self.lbl_shock.setStyleSheet(f"{base_card_style} color: #facc15;")
        self.lbl_verdict.setStyleSheet(f"{base_card_style} color: #94a3b8;")

        metric_layout.addWidget(self.lbl_rpm)
        metric_layout.addWidget(self.lbl_shock)
        metric_layout.addWidget(self.lbl_verdict)
        main_layout.addLayout(metric_layout)

        # 3. PyQtGraph Real-time Plotting Area
        pg.setConfigOptions(antialias=True)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#0a0e16")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.25)
        self.plot_widget.setLabel('bottom', "Relative Time (Seconds)", color='#94a3b8')
        self.plot_widget.setLabel('left', "Shaft RPM", color='#38bdf8')
        
        # FIX: Explicit Y-range so massive attacks (50k) and normal ranges (1.8k) are both visible
        self.plot_widget.setYRange(0, 55000, padding=0.05)
        self.plot_widget.enableAutoRange(axis='x', enable=True)
        self.plot_widget.addLegend(offset=(15, 15))

        # Max Safe Mechanical Limit (3600 RPM)
        self.limit_line = pg.InfiniteLine(
            pos=3600,
            angle=0,
            pen=pg.mkPen(color='#ef4444', width=2, style=QtCore.Qt.PenStyle.DashLine),
            label="Max Safe Limit: 3600 RPM",
            labelOpts={'position': 0.85, 'color': '#f87171', 'movable': False}
        )
        self.plot_widget.addItem(self.limit_line)

        # RPM Telemetry Curve
        self.rpm_curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#06b6d4', width=2.5),
            symbol='o',
            symbolSize=7,
            symbolBrush='#38bdf8',
            name="Commanded Motor RPM"
        )

        main_layout.addWidget(self.plot_widget)

        # 4. Ingestion Timer (50 Hz / 20ms poll rate)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.process_incoming_packets)
        self.timer.start(20)

    def process_incoming_packets(self):
        while True:
            try:
                data, _ = self.udp_sock.recvfrom(1024)
                if len(data) >= FRAME_SIZE:
                    ts_ns, tx_id, reg, rpm, shock_bar, verdict, _ = struct.unpack(FRAME_FORMAT, data[:FRAME_SIZE])
                    
                    elapsed = time.time() - self.start_time
                    self.time_points.append(elapsed)
                    self.rpm_data.append(rpm)
                    self.shock_data.append(shock_bar)

                    # Update Graph Curve
                    self.rpm_curve.setData(list(self.time_points), list(self.rpm_data))

                    # Update Telemetry KPI Cards
                    self.lbl_rpm.setText(f"RPM: {rpm:,.0f} (Reg 0x{reg:04X})")
                    self.lbl_shock.setText(f"Pressure Shock: {shock_bar:.2f} Bar")

                    if verdict == 1:
                        self.lbl_verdict.setText(f"Verdict: [ ALLOWED ] (Tx: 0x{tx_id:X})")
                        self.lbl_verdict.setStyleSheet("background-color: #064e3b; border: 1px solid #10b981; border-radius: 8px; padding: 12px; font-size: 13px; font-weight: bold; color: #34d399;")
                    else:
                        self.lbl_verdict.setText(f"Verdict: [ BLOCKED / DROP ] (Trip-Wire)")
                        self.lbl_verdict.setStyleSheet("background-color: #450a0a; border: 1px solid #ef4444; border-radius: 8px; padding: 12px; font-size: 13px; font-weight: bold; color: #f87171;")

            except BlockingIOError:
                break
            except Exception as e:
                print(f"Error unpacking telemetry: {e}")
                break

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = VoltGuardQtWindow()
    window.show()
    sys.exit(app.exec())