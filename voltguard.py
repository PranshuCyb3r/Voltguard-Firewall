import sys
import socket
import struct
import time
from collections import deque
from PyQt6 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

# Telemetry Wire Configuration
TELEMETRY_PORT = 5555
FRAME_SIZE_32 = 32
FRAME_SIZE_28 = 28

class TacticalCard(QtWidgets.QFrame):
    """Modern Cyber-Physical Instrumentation Metric Card"""
    def __init__(self, title, default_val, accent_color="#ef4444"):
        super().__init__()
        self.accent_color = accent_color
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #0d121d;
                border: 1px solid #1e2638;
                border-top: 2px solid {accent_color};
                border-radius: 6px;
            }}
        """)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        self.title_lbl = QtWidgets.QLabel(title.upper())
        self.title_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 700; letter-spacing: 1px; border: none;")
        
        self.val_lbl = QtWidgets.QLabel(default_val)
        self.val_lbl.setStyleSheet("color: #f8fafc; font-size: 16px; font-weight: 800; font-family: 'Consolas', monospace; border: none;")

        layout.addWidget(self.title_lbl)
        layout.addWidget(self.val_lbl)

    def set_value(self, val, color=None):
        self.val_lbl.setText(val)
        if color:
            self.val_lbl.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: 800; font-family: 'Consolas', monospace; border: none;")

class VoltGuardTacticalProWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoltGuard :: Cyber-Physical OT Ingress Console")
        self.resize(1340, 820)
        self.setStyleSheet("background-color: #070a10; color: #e2e8f0; font-family: 'Segoe UI', Consolas, sans-serif;")

        self.max_points = 150
        self.time_points = deque(maxlen=self.max_points)
        self.rpm_data = deque(maxlen=self.max_points)
        self.shock_data = deque(maxlen=self.max_points)
        self.start_time = time.time()

        # Non-blocking UDP Socket bound to 0.0.0.0
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_sock.bind(("0.0.0.0", TELEMETRY_PORT))
        self.udp_sock.setblocking(False)

        self.init_ui()

        # 50 FPS Real-time Refresh Loop
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.process_packets)
        self.timer.start(20)

    def init_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root_layout = QtWidgets.QHBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(14)

        # ---------------- 1. LEFT SIDEBAR: OT HARDWARE CHASSIS ----------------
        sidebar = QtWidgets.QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #0b0f19;
                border: 1px solid #1a2233;
                border-radius: 8px;
            }
        """)
        side_layout = QtWidgets.QVBoxLayout(sidebar)
        side_layout.setContentsMargins(14, 14, 14, 14)
        side_layout.setSpacing(10)

        brand_badge = QtWidgets.QLabel("VOLTGUARD // ENCLAVE")
        brand_badge.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: 900; letter-spacing: 1.5px; border: none;")
        side_layout.addWidget(brand_badge)

        sub_brand = QtWidgets.QLabel("KINETIC-PHYSICS FIREWALL")
        sub_brand.setStyleSheet("color: #64748b; font-size: 9px; font-weight: bold; border: none;")
        side_layout.addWidget(sub_brand)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet("border-color: #1e293b;")
        side_layout.addWidget(sep)

        # Operational Tripwires Box
        bounds_title = QtWidgets.QLabel("PHYSICAL BOUNDS")
        bounds_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 700; border: none;")
        side_layout.addWidget(bounds_title)

        limits_text = """
        <div style='font-family: Consolas; font-size: 11px; line-height: 1.8;'>
          <span style='color:#64748b;'>Rotor Max:</span> <b style='color:#ef4444;'>3,600 RPM</b><br/>
          <span style='color:#64748b;'>Cavitation:</span> <b style='color:#eab308;'>500 RPM</b><br/>
          <span style='color:#64748b;'>Max Shock:</span> <b style='color:#f87171;'>16.0 Bar</b><br/>
          <span style='color:#64748b;'>Nominal:</span> <b style='color:#22c55e;'>1,800 RPM</b>
        </div>
        """
        limits_lbl = QtWidgets.QLabel(limits_text)
        limits_lbl.setStyleSheet("border: none; padding: 4px 0;")
        side_layout.addWidget(limits_lbl)

        side_layout.addStretch()

        # Hardware Enclave Telemetry
        enclave_status = """
        <div style='font-family: Consolas; font-size: 10px; line-height: 1.6; color: #475569;'>
          [+] DIN Rail: <span style='color:#22c55e;'>24.1V OK</span><br/>
          [+] Hardware Key: <span style='color:#38bdf8;'>ARMED</span><br/>
          [+] Zero-Copy: <span style='color:#22c55e;'>ACTIVE</span><br/>
          [+] Ingress Port: <span style='color:#f8fafc;'>TCP 5502</span>
        </div>
        """
        hw_lbl = QtWidgets.QLabel(enclave_status)
        hw_lbl.setStyleSheet("border: none;")
        side_layout.addWidget(hw_lbl)

        root_layout.addWidget(sidebar)

        # ---------------- 2. MAIN COCKPIT AREA ----------------
        main_cockpit = QtWidgets.QVBoxLayout()
        main_cockpit.setSpacing(12)

        # Top Tactical Status Ribbon
        hud_bar = QtWidgets.QHBoxLayout()
        
        hud_title = QtWidgets.QLabel("REAL-TIME OSCILLOSCOPE & INGRESS JOURNAL")
        hud_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #f8fafc; letter-spacing: 0.5px;")
        hud_bar.addWidget(hud_title)

        hud_bar.addStretch()

        self.pill_stream = QtWidgets.QLabel("● UDP:5555 STREAM ACTIVE")
        self.pill_stream.setStyleSheet("background: #064e3b; color: #34d399; font-size: 10px; font-weight: 800; padding: 4px 10px; border-radius: 4px;")
        hud_bar.addWidget(self.pill_stream)

        self.pill_airgap = QtWidgets.QLabel("AIR-GAPPED ENCLAVE")
        self.pill_airgap.setStyleSheet("background: #7f1d1d; color: #fecaca; font-size: 10px; font-weight: 800; padding: 4px 10px; border-radius: 4px;")
        hud_bar.addWidget(self.pill_airgap)

        main_cockpit.addLayout(hud_bar)

        # KPI Metrics Header
        cards_row = QtWidgets.QHBoxLayout()
        cards_row.setSpacing(10)

        self.card_rpm = TacticalCard("Commanded Shaft Speed", "-- RPM", "#38bdf8")
        self.card_shock = TacticalCard("Joukowsky Shock (ΔP)", "-- Bar", "#ef4444")
        self.card_state = TacticalCard("Enclave Boundary State", "STANDBY", "#94a3b8")
        self.card_verdict = TacticalCard("Deterministic Verdict", "LISTENING...", "#22c55e")

        cards_row.addWidget(self.card_rpm)
        cards_row.addWidget(self.card_shock)
        cards_row.addWidget(self.card_state)
        cards_row.addWidget(self.card_verdict)
        main_cockpit.addLayout(cards_row)

        # High-Contrast Oscilloscope Plot
        pg.setConfigOptions(antialias=True)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#05080e")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.18)
        self.plot_widget.setLabel('bottom', "Relative Time (Seconds)", color='#64748b')
        self.plot_widget.setLabel('left', "Shaft RPM", color='#cbd5e1')
        self.plot_widget.setYRange(0, 55000, padding=0.04)

        # Limit Line 1: Tripwire Ceiling (3,600 RPM)
        self.limit_ceiling = pg.InfiniteLine(
            pos=3600, angle=0,
            pen=pg.mkPen(color='#ef4444', width=2, style=QtCore.Qt.PenStyle.DashLine),
            label="DYNAMIC ROTOR LIMIT: 3,600 RPM",
            labelOpts={'position': 0.85, 'color': '#ef4444', 'movable': False}
        )
        self.plot_widget.addItem(self.limit_ceiling)

        # Limit Line 2: Cavitation Floor (500 RPM)
        self.limit_floor = pg.InfiniteLine(
            pos=500, angle=0,
            pen=pg.mkPen(color='#eab308', width=1.5, style=QtCore.Qt.PenStyle.DotLine),
            label="CAVITATION FLOOR: 500 RPM",
            labelOpts={'position': 0.15, 'color': '#eab308', 'movable': False}
        )
        self.plot_widget.addItem(self.limit_floor)

        # Active Commanded Waveform
        self.rpm_curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#ffffff', width=2.5),
            symbol='o', symbolSize=8, symbolBrush='#ef4444', symbolPen=pg.mkPen('#ffffff', width=1),
            name="Commanded RPM Curve"
        )
        main_cockpit.addWidget(self.plot_widget, stretch=4)

        # Log Strip Console at Bottom
        self.log_terminal = QtWidgets.QLabel("VoltGuard Live Telemetry Ingress Ready. Waiting for SCADA packet injection on TCP port 5502...")
        self.log_terminal.setStyleSheet("""
            background-color: #090d16;
            color: #64748b;
            font-family: 'Consolas', monospace;
            font-size: 11px;
            padding: 8px 12px;
            border: 1px solid #1e2638;
            border-radius: 4px;
        """)
        main_cockpit.addWidget(self.log_terminal, stretch=0)

        root_layout.addLayout(main_cockpit)

    def process_packets(self):
        while True:
            try:
                data, _ = self.udp_sock.recvfrom(2048)
                if not data:
                    break

                # Robust wire unpack (handles 32-byte production & 28-byte legacy)
                if len(data) >= FRAME_SIZE_32:
                    ts_ns, tx_id, reg, rpm, shock_bar, verdict, _ = struct.unpack("<QHHffB11s", data[:32])
                elif len(data) >= FRAME_SIZE_28:
                    ts_ns, tx_id, reg, rpm, shock_bar, verdict, _ = struct.unpack("<QHHffB7s", data[:28])
                else:
                    continue

                elapsed = round(time.time() - self.start_time, 2)
                self.time_points.append(elapsed)
                self.rpm_data.append(rpm)
                self.shock_data.append(shock_bar)

                self.rpm_curve.setData(list(self.time_points), list(self.rpm_data))

                # Update Card Values
                self.card_rpm.set_value(f"{rpm:,.0f} RPM", "#ffffff")
                self.card_shock.set_value(f"{shock_bar:.2f} Bar", "#ef4444" if shock_bar > 16.0 else "#38bdf8")

                if verdict == 1:
                    self.card_state.set_value("NOMINAL LAMINAR", "#22c55e")
                    self.card_verdict.set_value("[ PERMIT DISPATCH ]", "#22c55e")
                    log_msg = f"[INGRESS ALLOW] Tx: 0x{tx_id:04X} | Target Reg: 0x{reg:04X} | RPM: {rpm:,.0f} | Shock: {shock_bar:.2f} Bar -> INVARIANT SOUND"
                else:
                    reason = "ROTOR OVERSPEED BREACH" if rpm > 3600 else "CAVITATION STALL COLLAPSE"
                    self.card_state.set_value(reason, "#ef4444")
                    self.card_verdict.set_value("[ ATTACK INTERCEPTED ]", "#ef4444")
                    log_msg = f"[INGRESS DROP] Tx: 0x{tx_id:04X} | Target Reg: 0x{reg:04X} | RPM: {rpm:,.0f} | Shock: {shock_bar:.2f} Bar -> TRIPPED & KILLED"

                self.log_terminal.setText(log_msg)
                print(log_msg)

            except BlockingIOError:
                break
            except Exception as e:
                print(f"[RECV ERROR] {e}")
                break

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = VoltGuardTacticalProWindow()
    window.show()
    sys.exit(app.exec())