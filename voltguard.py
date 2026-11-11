import sys
import socket
import struct
from collections import deque
from PyQt6 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

class VoltGuardOscilloscope(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoltGuard :: Cyber-Physical OT Ingress Console & Physics Oscilloscope")
        self.resize(1280, 800)
        self.setStyleSheet("background-color: #0b0f19; color: #f1f5f9; font-family: 'Segoe UI', Consolas, sans-serif;")

        # UDP Telemetry Socket on Port 5555
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_sock.bind(("127.0.0.1", 5555))
        self.udp_sock.setblocking(False)

        # Ring Buffers for Real-Time Oscilloscope Plot
        self.max_pts = 60
        self.history_time = deque(maxlen=self.max_pts)
        self.history_commanded = deque(maxlen=self.max_pts)
        self.history_twin = deque(maxlen=self.max_pts)
        self.packet_counter = 0

        self.init_ui()

        # 30 FPS Polling Timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.process_packets)
        self.timer.start(33)

    def init_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QHBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # --- LEFT SIDEBAR (Controls & Physical Tripwire Limits) ---
        sidebar = QtWidgets.QFrame()
        sidebar.setFixedWidth(280)
        sidebar.setStyleSheet("background-color: #111827; border: 1px solid #1f293d; border-radius: 8px; padding: 12px;")
        side_layout = QtWidgets.QVBoxLayout(sidebar)

        title = QtWidgets.QLabel("VOLTGUARD // ENCLAVE\n<span style='font-size:11px; color:#94a3b8;'>Physical Dynamic Tripwires</span>")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ef4444;")
        side_layout.addWidget(title)
        side_layout.addSpacing(10)

        # Limits Panel
        limits_box = QtWidgets.QGroupBox("PHYSICAL BOUNDS")
        limits_box.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: bold; border: 1px solid #1e293b; padding: 8px;")
        box_layout = QtWidgets.QVBoxLayout(limits_box)
        box_layout.addWidget(QtWidgets.QLabel("<b style='color:#94a3b8;'>Rotor Shear Max:</b> <span style='color:#ef4444;'>3,600 RPM</span>"))
        box_layout.addWidget(QtWidgets.QLabel("<b style='color:#94a3b8;'>Nominal Baseline:</b> <span style='color:#22c55e;'>1,800 RPM</span>"))
        box_layout.addWidget(QtWidgets.QLabel("<b style='color:#94a3b8;'>Cavitation Floor:</b> <span style='color:#eab308;'>500 RPM</span>"))
        box_layout.addWidget(QtWidgets.QLabel("<b style='color:#94a3b8;'>Max Pipe Shock:</b> <span style='color:#ef4444;'>16.0 Bar</span>"))
        side_layout.addWidget(limits_box)

        side_layout.addSpacing(10)
        bus_box = QtWidgets.QGroupBox("MICROSECOND BUS")
        bus_box.setStyleSheet("color: #a855f7; font-size: 11px; font-weight: bold; border: 1px solid #1e293b; padding: 8px;")
        bus_layout = QtWidgets.QVBoxLayout(bus_box)
        bus_layout.addWidget(QtWidgets.QLabel("<span style='color:#38bdf8;'>[+] Ingress Port:</span> <b>TCP 5502</b>"))
        bus_layout.addWidget(QtWidgets.QLabel("<span style='color:#22c55e;'>[+] Telemetry UDP:</span> <b>UDP 5555</b>"))
        bus_layout.addWidget(QtWidgets.QLabel("<span style='color:#cbd5e1;'>[+] Frame Size:</span> <b>32 Bytes Packed</b>"))
        bus_layout.addWidget(QtWidgets.QLabel("<span style='color:#4ade80;'>[+] Inspection Latency:</span> <b>&lt; 1.0 µs</b>"))
        side_layout.addWidget(bus_box)

        side_layout.addStretch()

        self.btn_status = QtWidgets.QPushButton("● AIR-GAPPED ENCLAVE ACTIVE")
        self.btn_status.setFixedHeight(36)
        self.btn_status.setStyleSheet("background-color: #991b1b; color: #fecaca; font-weight: bold; border-radius: 6px;")
        side_layout.addWidget(self.btn_status)
        main_layout.addWidget(sidebar)

        # --- RIGHT MAIN WORKSPACE ---
        right_panel = QtWidgets.QVBoxLayout()
        right_panel.setSpacing(12)

        # Top Header Bar
        top_bar = QtWidgets.QHBoxLayout()
        header_lbl = QtWidgets.QLabel("REAL-TIME KINEMATIC OSCILLOSCOPE & INGRESS JOURNAL")
        header_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #f8fafc; letter-spacing: 0.5px;")
        top_bar.addWidget(header_lbl)
        top_bar.addStretch()

        self.telemetry_badge = QtWidgets.QLabel("● UDP:5555 STREAM ACTIVE")
        self.telemetry_badge.setStyleSheet("color: #4ade80; background-color: #064e3b; padding: 5px 12px; border-radius: 4px; font-weight: bold; font-size: 11px;")
        top_bar.addWidget(self.telemetry_badge)
        right_panel.addLayout(top_bar)

        # KPI Status Cards
        cards_layout = QtWidgets.QHBoxLayout()
        cards_layout.setSpacing(12)

        self.card_rpm = self.create_card("COMMANDED SHAFT SPEED", "1,800 RPM", "#38bdf8")
        self.card_shock = self.create_card("JOUKOWSKY SHOCK (ΔP)", "7.75 Bar", "#38bdf8")
        self.card_twin = self.create_card("DIGITAL TWIN (RK4)", "1,800 RPM", "#f59e0b")
        self.card_verdict = self.create_card("DETERMINISTIC L2 VERDICT", "[ ALLOW: INVARIANT VALID ]", "#22c55e")

        cards_layout.addWidget(self.card_rpm)
        cards_layout.addWidget(self.card_shock)
        cards_layout.addWidget(self.card_twin)
        cards_layout.addWidget(self.card_verdict)
        right_panel.addLayout(cards_layout)

        # Oscilloscope Waveform Plot (PyQtGraph)
        pg.setConfigOptions(antialias=True)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#070b13")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.18)
        self.plot_widget.setLabel('left', 'Shaft Velocity (RPM)', color='#94a3b8', size='11pt')
        self.plot_widget.setLabel('bottom', 'Relative Telemetry Time Frame (Seconds)', color='#94a3b8', size='11pt')
        self.plot_widget.setYRange(0, 16000)

        # Red Tripwire Ceiling: 3,600 RPM
        rotor_tripwire = pg.InfiniteLine(pos=3600, angle=0, pen=pg.mkPen(color='#ef4444', width=1.5, style=QtCore.Qt.PenStyle.DashLine), label="DYNAMIC ROTOR LIMIT: 3,600 RPM", labelOpts={'position': 0.95, 'color': '#ef4444'})
        self.plot_widget.addItem(rotor_tripwire)

        # Amber Cavitation Floor: 500 RPM
        cav_floor = pg.InfiniteLine(pos=500, angle=0, pen=pg.mkPen(color='#eab308', width=1.2, style=QtCore.Qt.PenStyle.DotLine), label="CAVITATION FLOOR: 500 RPM", labelOpts={'position': 0.2, 'color': '#eab308'})
        self.plot_widget.addItem(cav_floor)

        # Data Curves
        self.curve_commanded = self.plot_widget.plot(pen=pg.mkPen(color='#38bdf8', width=2.5), symbol='o', symbolSize=6, symbolBrush='#38bdf8', name='Commanded Ingress')
        self.curve_twin = self.plot_widget.plot(pen=pg.mkPen(color='#f59e0b', width=2.0, style=QtCore.Qt.PenStyle.DashLine), symbol='s', symbolSize=5, symbolBrush='#f59e0b', name='RK4 Twin Model')

        right_panel.addWidget(self.plot_widget, stretch=4)

        # Terminal Ingress Journal
        self.log_terminal = QtWidgets.QLineEdit()
        self.log_terminal.setReadOnly(True)
        self.log_terminal.setText("[INGRESS JOURNAL] Waiting for incoming packet evaluation...")
        self.log_terminal.setStyleSheet("background-color: #050811; color: #94a3b8; font-family: Consolas; font-size: 12px; border: 1px solid #1e293b; padding: 8px; border-radius: 4px;")
        right_panel.addWidget(self.log_terminal)

        main_layout.addLayout(right_panel)

    def create_card(self, title, initial_val, color):
        frame = QtWidgets.QFrame()
        frame.setStyleSheet("background-color: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 10px;")
        v = QtWidgets.QVBoxLayout(frame)
        lbl_title = QtWidgets.QLabel(title)
        lbl_title.setStyleSheet("font-size: 10px; font-weight: bold; color: #94a3b8;")
        lbl_val = QtWidgets.QLabel(initial_val)
        lbl_val.setStyleSheet(f"font-size: 17px; font-weight: bold; color: {color};")
        v.addWidget(lbl_title)
        v.addWidget(lbl_val)
        frame.lbl_val = lbl_val
        return frame

    def process_packets(self):
        while True:
            try:
                data, _ = self.udp_sock.recvfrom(128)
                if len(data) == 32:
                    # Unpack exact 32 bytes: Magic(4B) + TxID(2B) + RPM(2B) + Shock(4f) + Twin(4f) + Verdict(1B) + Pad(7s) + TS(8Q)
                    magic, tx_id, rpm, shock, twin_rpm, verdict, _, ts = struct.unpack("<IHHffB7sQ", data)
                    
                    self.packet_counter += 1
                    self.history_time.append(self.packet_counter * 0.1)
                    self.history_commanded.append(rpm)
                    self.history_twin.append(twin_rpm)

                    # Update Cards
                    self.card_rpm.lbl_val.setText(f"{rpm:,} RPM")
                    self.card_shock.lbl_val.setText(f"{shock:.2f} Bar")
                    self.card_twin.lbl_val.setText(f"{int(twin_rpm):,} RPM")

                    if verdict == 0:
                        self.card_verdict.lbl_val.setText("[ ALLOW: INVARIANT VALID ]")
                        self.card_verdict.lbl_val.setStyleSheet("font-size: 17px; font-weight: bold; color: #22c55e;")
                        self.log_terminal.setText(f"[INGRESS ALLOW] Tx: 0x{tx_id:04X} | Commanded: {rpm:,} RPM | Shock: {shock:.2f} Bar | Digital Twin: {int(twin_rpm):,} RPM")
                    else:
                        self.card_verdict.lbl_val.setText("[ ATTACK INTERCEPTED / DROP ]")
                        self.card_verdict.lbl_val.setStyleSheet("font-size: 17px; font-weight: bold; color: #ef4444;")
                        self.log_terminal.setText(f"[ATTACK INTERCEPTED] Tx: 0x{tx_id:04X} | Commanded: {rpm:,} RPM | Shock: {shock:.2f} Bar -> INVARIANT BREACH TRIPPED")

                    # Dynamic Auto-scaling for Attack Spikes
                    if max(self.history_commanded) > 15000:
                        self.plot_widget.setYRange(0, 55000)
                    else:
                        self.plot_widget.setYRange(0, 5000)

                    self.curve_commanded.setData(list(self.history_time), list(self.history_commanded))
                    self.curve_twin.setData(list(self.history_time), list(self.history_twin))
            except BlockingIOError:
                break
            except Exception as e:
                print(f"[RECV EXCEPTION] {e}")
                break

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = VoltGuardOscilloscope()
    win.show()
    sys.exit(app.exec())
