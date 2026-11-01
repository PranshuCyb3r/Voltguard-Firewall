import sys
import socket
import struct
from collections import deque
from PyQt6 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

# Configure pyqtgraph dark tactical theme
pg.setConfigOption('background', '#0b0f17')
pg.setConfigOption('foreground', '#94a3b8')
pg.setConfigOption('antialias', True)

class VoltGuardOscilloscope(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoltGuard :: Cyber-Physical OT Ingress Console & Physics Oscilloscope")
        self.resize(1380, 850)
        self.setStyleSheet("""
            QMainWindow { background-color: #080b11; }
            QLabel { color: #f1f5f9; font-family: 'Segoe UI', monospace; }
        """)

        # Data Deques
        self.history_len = 100
        self.time_history = deque(maxlen=self.history_len)
        self.rpm_history = deque(maxlen=self.history_len)
        self.twin_history = deque(maxlen=self.history_len)
        self.sample_idx = 0

        # Initial baseline visualization points
        for i in range(5):
            self.time_history.append(float(i))
            self.rpm_history.append(1800.0)
            self.twin_history.append(1800.0)
        self.sample_idx = 4

        self.init_ui()
        self.init_udp_socket()

    def init_ui(self):
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QtWidgets.QHBoxLayout(main_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # ----------------- LEFT SIDEBAR -----------------
        sidebar = QtWidgets.QFrame()
        sidebar.setFixedWidth(280)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #0f141f;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
        """)
        sb_layout = QtWidgets.QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(14, 14, 14, 14)
        sb_layout.setSpacing(12)

        title_lbl = QtWidgets.QLabel("VOLTGUARD // ENCLAVE\n<span style='font-size:11px; color:#ef4444;'>KINETIC-PHYSICS FIREWALL</span>")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; border: none;")
        sb_layout.addWidget(title_lbl)

        # Invariant Reference Box
        rules_box = QtWidgets.QGroupBox("PHYSICAL BOUNDS")
        rules_box.setStyleSheet("QGroupBox { color: #38bdf8; font-weight: bold; border: 1px solid #1e293b; margin-top: 10px; padding: 10px; }")
        rb_layout = QtWidgets.QVBoxLayout(rules_box)
        rb_layout.addWidget(QtWidgets.QLabel("Rotor Shear Max: <b style='color:#ef4444;'>3,600 RPM</b>"))
        rb_layout.addWidget(QtWidgets.QLabel("Nominal Baseline: <b style='color:#10b981;'>1,800 RPM</b>"))
        rb_layout.addWidget(QtWidgets.QLabel("Cavitation Floor: <b style='color:#f59e0b;'>500 RPM</b>"))
        rb_layout.addWidget(QtWidgets.QLabel("Max Pipe Shock: <b style='color:#ef4444;'>16.0 Bar</b>"))
        sb_layout.addWidget(rules_box)

        # Network Stats
        net_box = QtWidgets.QGroupBox("MICROSECOND BUS")
        net_box.setStyleSheet("QGroupBox { color: #a855f7; font-weight: bold; border: 1px solid #1e293b; margin-top: 10px; padding: 10px; }")
        nb_layout = QtWidgets.QVBoxLayout(net_box)
        nb_layout.addWidget(QtWidgets.QLabel("[+] Ingress Port: <b>TCP 5502</b>"))
        nb_layout.addWidget(QtWidgets.QLabel("[+] Telemetry UDP: <b>UDP 5555</b>"))
        nb_layout.addWidget(QtWidgets.QLabel("[+] Frame Size: <b>32 Bytes Packed</b>"))
        nb_layout.addWidget(QtWidgets.QLabel("[+] Inspection Latency: <b style='color:#10b981;'>&lt; 1.0 μs</b>"))
        sb_layout.addWidget(net_box)

        sb_layout.addStretch()

        status_tag = QtWidgets.QLabel("● AIR-GAPPED ENCLAVE ACTIVE")
        status_tag.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        status_tag.setStyleSheet("background-color: #450a0a; color: #ef4444; border: 1px solid #ef4444; border-radius: 4px; padding: 6px; font-weight: bold;")
        sb_layout.addWidget(status_tag)

        main_layout.addWidget(sidebar)

        # ----------------- RIGHT CONTENT -----------------
        content_layout = QtWidgets.QVBoxLayout()
        content_layout.setSpacing(12)

        # 1. Header Badges
        header_bar = QtWidgets.QHBoxLayout()
        h_title = QtWidgets.QLabel("REAL-TIME KINEMATIC OSCILLOSCOPE & INGRESS JOURNAL")
        h_title.setStyleSheet("font-size: 17px; font-weight: bold; color: #f8fafc;")
        header_bar.addWidget(h_title)
        header_bar.addStretch()

        badge_udp = QtWidgets.QLabel("● UDP:5555 STREAM ACTIVE")
        badge_udp.setStyleSheet("background-color: #064e3b; color: #10b981; border: 1px solid #10b981; border-radius: 4px; padding: 4px 10px; font-size: 11px; font-weight: bold;")
        header_bar.addWidget(badge_udp)

        content_layout.addLayout(header_bar)

        # 2. Metric KPI Cards Row
        cards_layout = QtWidgets.QHBoxLayout()
        cards_layout.setSpacing(10)

        self.card_rpm = self.create_kpi_card("COMMANDED SHAFT SPEED", "1,800 RPM", "#38bdf8")
        self.card_shock = self.create_kpi_card("JOUKOWSKY SHOCK (ΔP)", "7.75 Bar", "#38bdf8")
        self.card_twin = self.create_kpi_card("DIGITAL TWIN (RK4)", "1,800 RPM", "#f59e0b")
        self.card_verdict = self.create_kpi_card("DETERMINISTIC L2 VERDICT", "[ ALLOW: INVARIANT VALID ]", "#10b981")

        cards_layout.addWidget(self.card_rpm)
        cards_layout.addWidget(self.card_shock)
        cards_layout.addWidget(self.card_twin)
        cards_layout.addWidget(self.card_verdict)
        content_layout.addLayout(cards_layout)

        # 3. High-Clarity Plot Widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.25)
        self.plot_widget.setLabel('left', 'Shaft Velocity (RPM)', color='#94a3b8', size='12pt')
        self.plot_widget.setLabel('bottom', 'Relative Telemetry Sequence (Packets / Time)', color='#94a3b8', size='12pt')
        
        # Initial View Limits
        self.plot_widget.setYRange(0, 4500, padding=0.05)
        self.plot_widget.setXRange(0, 10, padding=0.05)

        # Threshold Visual Zone Lines
        self.tripwire_line = pg.InfiniteLine(
            pos=3600, angle=0, 
            pen=pg.mkPen(color='#ef4444', width=2, style=QtCore.Qt.PenStyle.DashLine), 
            label="DYNAMIC ROTOR LIMIT: 3,600 RPM", 
            labelOpts={'position': 0.85, 'color': '#ef4444'}
        )
        self.cavitation_line = pg.InfiniteLine(
            pos=500, angle=0, 
            pen=pg.mkPen(color='#f59e0b', width=1.5, style=QtCore.Qt.PenStyle.DotLine), 
            label="CAVITATION FLOOR: 500 RPM", 
            labelOpts={'position': 0.15, 'color': '#f59e0b'}
        )
        
        self.plot_widget.addItem(self.tripwire_line)
        self.plot_widget.addItem(self.cavitation_line)

        # Curves
        self.curve_wire = self.plot_widget.plot(
            list(self.time_history), list(self.rpm_history),
            pen=pg.mkPen(color='#38bdf8', width=2.5),
            symbol='o', symbolSize=8, symbolBrush='#38bdf8', symbolPen='w',
            name="Commanded Wire Ingress"
        )
        self.curve_twin = self.plot_widget.plot(
            list(self.time_history), list(self.twin_history),
            pen=pg.mkPen(color='#f59e0b', width=2, style=QtCore.Qt.PenStyle.DashLine),
            name="RK4 Digital Twin Model"
        )

        content_layout.addWidget(self.plot_widget, stretch=4)

        # 4. Ingress Journal Terminal Strip
        self.terminal_lbl = QtWidgets.QLabel("[INGRESS JOURNAL] Ready. Waiting for telemetry frames from server.exe...")
        self.terminal_lbl.setStyleSheet("""
            background-color: #0b0f19;
            color: #64748b;
            border: 1px solid #1e293b;
            border-radius: 4px;
            padding: 8px;
            font-family: Consolas, monospace;
            font-size: 12px;
        """)
        content_layout.addWidget(self.terminal_lbl)

        main_layout.addLayout(content_layout, stretch=1)

    def create_kpi_card(self, title, val_text, color):
        card = QtWidgets.QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #0f141f;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(6, 6, 6, 6)
        lbl_title = QtWidgets.QLabel(title)
        lbl_title.setStyleSheet("font-size: 10px; color: #94a3b8; font-weight: bold; border:none;")
        lbl_val = QtWidgets.QLabel(val_text)
        lbl_val.setStyleSheet(f"font-size: 17px; font-weight: bold; color: {color}; border:none;")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        card.value_lbl = lbl_val
        return card

    def init_udp_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        try:
            self.sock.bind(("127.0.0.1", 5555))
        except Exception as e:
            print(f"[ERROR] Socket bind failed on port 5555: {e}")

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.poll_telemetry)
        self.timer.start(25)  # 40 Hz polling rate

    def poll_telemetry(self):
        while True:
            try:
                data, _ = self.sock.recvfrom(256)
                if len(data) == 32:
                    # FIX: <IHHffB7sQ = 4 + 2 + 2 + 4 + 4 + 1 + 7 + 8 = 32 Bytes
                    magic, tx_id, rpm, shock, twin_rpm, verdict, res, ts = struct.unpack("<IHHffB7sQ", data)
                    if magic == 0x5647544D:
                        self.update_telemetry(tx_id, rpm, shock, twin_rpm, verdict)
            except (BlockingIOError, socket.error):
                break
            except Exception as e:
                print(f"[RECV EXCEPTION] {e}")
                break

    def update_telemetry(self, tx_id, rpm, shock, twin_rpm, verdict):
        self.sample_idx += 1
        t = float(self.sample_idx)

        self.time_history.append(t)
        self.rpm_history.append(float(rpm))
        self.twin_history.append(float(twin_rpm))

        # Update Plot Curves
        x_data = list(self.time_history)
        y_rpm = list(self.rpm_history)
        y_twin = list(self.twin_history)

        self.curve_wire.setData(x_data, y_rpm)
        self.curve_twin.setData(x_data, y_twin)

        # Dynamic Auto-Range for X-Axis
        if len(x_data) > 1:
            self.plot_widget.setXRange(max(0, x_data[-1] - 25), x_data[-1] + 2, padding=0.02)

        # Dynamic Y-Range Expansion for large attack spikes
        current_max = max(y_rpm)
        if current_max > 4500:
            self.plot_widget.setYRange(0, max(current_max * 1.15, 55000), padding=0.05)
        else:
            self.plot_widget.setYRange(0, 4500, padding=0.05)

        # Update Metric KPI Cards
        self.card_rpm.value_lbl.setText(f"{rpm:,} RPM")
        self.card_shock.value_lbl.setText(f"{shock:.2f} Bar")
        self.card_twin.value_lbl.setText(f"{int(twin_rpm):,} RPM")

        # Update Verdict Card & Journal Strip
        if verdict == 1:
            self.card_verdict.value_lbl.setText("[ ALLOW: INVARIANT VALID ]")
            self.card_verdict.value_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #10b981; border:none;")
            self.terminal_lbl.setText(f"[INGRESS ALLOW] Tx: 0x{tx_id:04X} | Target Reg: 0x0001 | RPM: {rpm:,} | Shock: {shock:.2f} Bar | Invariant Valid")
            self.terminal_lbl.setStyleSheet("background-color: #064e3b; color: #10b981; border: 1px solid #10b981; border-radius: 4px; padding: 8px; font-family: Consolas, monospace; font-size: 12px;")
        else:
            self.card_verdict.value_lbl.setText("[ ATTACK INTERCEPTED / DROP ]")
            self.card_verdict.value_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #ef4444; border:none;")
            self.terminal_lbl.setText(f"[INGRESS DROP] Tx: 0x{tx_id:04X} | Target Reg: 0x0001 | RPM: {rpm:,} | Shock: {shock:.2f} Bar -> TRIPPED & KILLED")
            self.terminal_lbl.setStyleSheet("background-color: #450a0a; color: #ef4444; border: 1px solid #ef4444; border-radius: 4px; padding: 8px; font-family: Consolas, monospace; font-size: 12px;")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = VoltGuardOscilloscope()
    win.show()
    sys.exit(app.exec())