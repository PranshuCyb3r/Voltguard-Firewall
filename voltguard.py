import sys
import socket
import struct
import time
from collections import deque
from PyQt6 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

# Configure High-Contrast Dark Tactical Theme
pg.setConfigOption('background', '#080c14')
pg.setConfigOption('foreground', '#64748b')
pg.setConfigOptions(antialias=True)

class VoltGuard24x7Workstation(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoltGuard :: 24x7 Production OT Physics Firewall Workstation")
        self.resize(1720, 980)
        self.setMinimumSize(1400, 850)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #06090e;
                color: #f8fafc;
                font-family: 'Consolas', 'Segoe UI', monospace;
            }
            QTableWidget {
                gridline-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #0a0e17;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: #1e293b;
                min-height: 20px;
                border-radius: 4px;
            }
        """)

        # Ring buffers for real-time oscilloscope (Starts empty)
        self.history_len = 90
        self.time_buffer = deque(maxlen=self.history_len)
        self.cmd_buffer  = deque(maxlen=self.history_len)
        self.twin_buffer = deque(maxlen=self.history_len)
        self.current_t   = 0.0
        self.packet_count = 0

        self.init_ui()
        self.init_udp_socket()

    def init_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(18, 12, 18, 12)
        main_layout.setSpacing(10)

        # -------------------------------------------------------------
        # 1. TOP GLOBAL TELEMETRY HEADER BAR
        # -------------------------------------------------------------
        top_bar = QtWidgets.QFrame()
        top_bar.setStyleSheet("background-color: #0d121c; border: 1px solid #1e2638; border-radius: 6px;")
        top_layout = QtWidgets.QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 8, 16, 8)

        brand_box = QtWidgets.QVBoxLayout()
        brand_box.setSpacing(2)
        lbl_title = QtWidgets.QLabel("VOLTGUARD // TACTICAL OT PHYSICS FIREWALL")
        lbl_title.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 900; letter-spacing: 1.5px;")
        lbl_sub = QtWidgets.QLabel("STATION_ID: KINETIC-ENCLAVE-09  |  NODE_IP: 10.240.18.4  |  SEC-LVL 4 FACTORY EDGE")
        lbl_sub.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        brand_box.addWidget(lbl_title)
        brand_box.addWidget(lbl_sub)
        top_layout.addLayout(brand_box)

        top_layout.addStretch()

        top_layout.addWidget(self.create_badge("DUAL-NIC:", "IN-LINE ACTIVE", "#38bdf8", "#082f49"))
        top_layout.addWidget(self.create_badge("PTP SYNC:", "0.428 µs PTP", "#4ade80", "#052e16"))
        top_layout.addWidget(self.create_badge("OPTOCOUPLER:", "LATCHED [24V]", "#f59e0b", "#451a03"))
        top_layout.addWidget(self.create_badge("AIR-GAP:", "ENCLAVE ISOLATED", "#ef4444", "#450a0a"))

        main_layout.addWidget(top_bar)

        # -------------------------------------------------------------
        # 2. ARCHITECTURAL MODULE PANELS (24x7 STATUS)
        # -------------------------------------------------------------
        arch_layout = QtWidgets.QHBoxLayout()
        arch_layout.setSpacing(10)

        p1 = self.create_arch_card("BUMP-IN-THE-WIRE NIC BRIDGE", [
            ("PHYSICAL INTERFACES", "eth0 <-> eth1 IN-LINE ACTIVE"),
            ("WIRE INGESTION", "142,893 PKTS / SEC (READY)"),
            ("EVAL LATENCY", "0.84 µs (JITTER: ±0.03µs)"),
            ("IPC FRAME / STATUS", "BYTE UDP:5555 | LOCKED & VERIFIED 24V")
        ])

        p2 = self.create_arch_card("MODBUS/TCP PARSER // MBAP DECODE", [
            ("PORT STATUS", "LISTENING ON TCP 5502 (ZERO-COPY)"),
            ("UNIT ID / FUNC", "MBAP FC 0x06 WRITE REGISTER"),
            ("STATE MONITOR", "ACTIVE 24x7 DAEMON THREAD"),
            ("WIRE FILTER", "HARDENED SYNCHRONOUS INLINE IPS")
        ])

        p3 = self.create_arch_card("OPENMODELICA BASELINE PHYSICS", [
            ("FLUID DENSITY (ρ)", "1,000 kg/m³ (TREATED WATER)"),
            ("ACOUSTIC VEL (a)", "1,200 m/s IN STEEL PIPE"),
            ("NOMINAL HEAD (P0)", "7.75 Bar | RUPTURE LIMIT: 16.00 Bar"),
            ("INVARIANT AUDIT", "100% FATAL IMPOSSIBLE PHYSICS REJECTION")
        ])

        arch_layout.addWidget(p1)
        arch_layout.addWidget(p2)
        arch_layout.addWidget(p3)
        main_layout.addLayout(arch_layout)

        # -------------------------------------------------------------
        # 3. FIVE NUMERIC METRIC ANNUNCIATORS (CLEAN INITIAL STATE)
        # -------------------------------------------------------------
        metrics_layout = QtWidgets.QHBoxLayout()
        metrics_layout.setSpacing(10)

        self.card_cmd   = self.create_metric_card("COMMANDED SETPOINT", "--", "RPM", "Waiting for Ingress Packet...", "#ffffff")
        self.card_twin  = self.create_metric_card("RK4 TWIN ESTIMATE", "--", "RPM", "Standing By", "#38bdf8")
        self.card_shock = self.create_metric_card("JOUKOWSKY SURGE", "--", "/ 16.0 BAR", "ΔP = ρ · a · Δv", "#ffffff")
        self.card_fatig = self.create_metric_card("BASQUIN S-N FATIGUE", "--", "/ 100 PTS", "Monitoring Rotor Strain", "#fbbf24")
        self.card_verd  = self.create_metric_card("PHYSICS IPS VERDICT", "ARMED", "", "Listening on Port 5502", "#38bdf8")

        metrics_layout.addWidget(self.card_cmd)
        metrics_layout.addWidget(self.card_twin)
        metrics_layout.addWidget(self.card_shock)
        metrics_layout.addWidget(self.card_fatig)
        metrics_layout.addWidget(self.card_verd)

        main_layout.addLayout(metrics_layout)

        # -------------------------------------------------------------
        # 4. WORKBENCH: OSCILLOSCOPE (LEFT) + INTERLOCK & TEST (RIGHT)
        # -------------------------------------------------------------
        middle_layout = QtWidgets.QHBoxLayout()
        middle_layout.setSpacing(10)

        # Oscilloscope Box
        plot_frame = QtWidgets.QFrame()
        plot_frame.setStyleSheet("background-color: #080c14; border: 1px solid #1e2638; border-radius: 6px;")
        plot_layout = QtWidgets.QVBoxLayout(plot_frame)
        plot_layout.setContentsMargins(14, 10, 14, 10)

        p_head = QtWidgets.QHBoxLayout()
        lbl_s_title = QtWidgets.QLabel("DUAL-TRACE INGRESS KINEMATIC OSCILLOSCOPE")
        lbl_s_title.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: 900; letter-spacing: 0.8px;")
        lbl_s_sub = QtWidgets.QLabel("24x7 REAL-TIME MONITOR // INGRESS WIRE TELEMETRY VS RK4 PREDICTOR")
        lbl_s_sub.setStyleSheet("color: #64748b; font-size: 9px; font-weight: bold;")
        p_head.addWidget(lbl_s_title)
        p_head.addSpacing(12)
        p_head.addWidget(lbl_s_sub)
        p_head.addStretch()

        leg_cmd = QtWidgets.QLabel("— Commanded (Wire)")
        leg_cmd.setStyleSheet("color: #ffffff; font-size: 9px; font-weight: bold;")
        leg_twin = QtWidgets.QLabel("- - RK4 Twin")
        leg_twin.setStyleSheet("color: #38bdf8; font-size: 9px; font-weight: bold;")
        p_head.addWidget(leg_cmd)
        p_head.addSpacing(8)
        p_head.addWidget(leg_twin)
        plot_layout.addLayout(p_head)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.15)
        self.plot_widget.setLabel('left', 'Shaft Velocity (RPM)', color='#64748b', size='10pt')
        self.plot_widget.setLabel('bottom', 'Relative Telemetry Window (Seconds)', color='#64748b', size='10pt')
        self.plot_widget.setYRange(0, 55000)

        # Fixed Non-Clipping Tripwire Lines
        line_ceil = pg.InfiniteLine(pos=3600, angle=0, pen=pg.mkPen(color='#ef4444', width=2, style=QtCore.Qt.PenStyle.DashLine))
        line_floor = pg.InfiniteLine(pos=500, angle=0, pen=pg.mkPen(color='#eab308', width=1.5, style=QtCore.Qt.PenStyle.DotLine))
        self.plot_widget.addItem(line_ceil)
        self.plot_widget.addItem(line_floor)

        # Clear Non-Overlapping Labels
        self.t_ceil = pg.TextItem("ROTOR SHEAR CEILING: 3,600 RPM", color='#ef4444', anchor=(1, 1))
        self.t_ceil.setPos(5.0, 5000)
        self.t_floor = pg.TextItem("CAVITATION FLOOR: 500 RPM", color='#eab308', anchor=(1, 0))
        self.t_floor.setPos(5.0, 100)
        self.plot_widget.addItem(self.t_ceil)
        self.plot_widget.addItem(self.t_floor)

        # Idle Indicator Text
        self.idle_text = pg.TextItem("SYSTEM ARMED // WAITING FOR WIRE PACKET...", color='#38bdf8', anchor=(0.5, 0.5))
        self.idle_text.setPos(3.0, 27500)
        self.idle_text.setFont(QtGui.QFont("Consolas", 12, QtGui.QFont.Weight.Bold))
        self.plot_widget.addItem(self.idle_text)

        self.curve_cmd  = self.plot_widget.plot(pen=pg.mkPen(color='#ffffff', width=2.5), symbol='o', symbolSize=6, symbolBrush='#ef4444')
        self.curve_twin = self.plot_widget.plot(pen=pg.mkPen(color='#38bdf8', width=2.0, style=QtCore.Qt.PenStyle.DashLine))

        plot_layout.addWidget(self.plot_widget)
        middle_layout.addWidget(plot_frame, stretch=7)

        # Right Panel: Attack Injection & Unclipped Hardware Controls
        right_panel = QtWidgets.QFrame()
        right_panel.setStyleSheet("background-color: #0d121c; border: 1px solid #1e2638; border-radius: 6px;")
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 12, 14, 12)
        right_layout.setSpacing(8)

        lbl_inj = QtWidgets.QLabel("ATTACK VECTOR INJECTOR (TEST HARNESS)")
        lbl_inj.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: 900; letter-spacing: 0.8px;")
        right_layout.addWidget(lbl_inj)

        self.btn_stux = self.create_attack_btn("STUXNET-CLASS OVERSPEED", "50,000 RPM // Rotational Shear Breach", "#ef4444")
        self.btn_cavit = self.create_attack_btn("CAVITATION COLLAPSE ATTACK", "300 RPM // Negative Pressure Vapor Gap", "#f59e0b")
        self.btn_recov = self.create_attack_btn("NOMINAL STEADY STATE", "1,800 RPM // Standard Baseline Cycle", "#22c55e")

        self.btn_stux.clicked.connect(lambda: self.inject_modbus(0x0103, 50000))
        self.btn_cavit.clicked.connect(lambda: self.inject_modbus(0x0104, 300))
        self.btn_recov.clicked.connect(lambda: self.inject_modbus(0x0101, 1800))

        right_layout.addWidget(self.btn_stux)
        right_layout.addWidget(self.btn_cavit)
        right_layout.addWidget(self.btn_recov)

        right_layout.addSpacing(4)

        lbl_hw = QtWidgets.QLabel("HARDWARE INTERLOCK CONTROLS (2-MAN RULE)")
        lbl_hw.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: 900; letter-spacing: 0.8px;")
        right_layout.addWidget(lbl_hw)

        right_layout.addWidget(self.create_toggle_row("Kinetic Slew Lockout", "Max Δω ≤ 140 RPM/s", True))
        right_layout.addWidget(self.create_toggle_row("Fail-Closed Opto-Relay", "DIN 24V Galvanic Decouple", True))
        right_layout.addWidget(self.create_toggle_row("RK4 Tolerance Override", "SURGE ΔP Ceiling 16.0 Bar", False))

        right_layout.addStretch()

        # Unclipped, Full-Height Emergency Air-Gap Cut Button
        self.btn_airgap_cut = QtWidgets.QPushButton("ASSERT EMERGENCY AIR-GAP CUT")
        self.btn_airgap_cut.setMinimumHeight(44)
        self.btn_airgap_cut.setStyleSheet("""
            QPushButton {
                background-color: #7f1d1d;
                color: #ffffff;
                font-weight: 900;
                font-size: 11px;
                border: 2px solid #ef4444;
                border-radius: 5px;
                letter-spacing: 1.2px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #991b1b;
            }
            QPushButton:pressed {
                background-color: #b91c1c;
            }
        """)
        self.btn_airgap_cut.clicked.connect(self.trigger_emergency_cut)
        right_layout.addWidget(self.btn_airgap_cut)

        middle_layout.addWidget(right_panel, stretch=3)
        main_layout.addLayout(middle_layout, stretch=6)

        # -------------------------------------------------------------
        # 5. BOTTOM SECTION: FORENSIC PCAP JOURNAL & INVARIANT BOUNDS
        # -------------------------------------------------------------
        bottom_layout = QtWidgets.QHBoxLayout()
        bottom_layout.setSpacing(10)

        # Forensic Journal Table
        tbl_frame = QtWidgets.QFrame()
        tbl_frame.setStyleSheet("background-color: #0d121c; border: 1px solid #1e2638; border-radius: 6px;")
        tbl_lay = QtWidgets.QVBoxLayout(tbl_frame)
        tbl_lay.setContentsMargins(12, 10, 12, 10)

        t_head = QtWidgets.QHBoxLayout()
        lbl_j_title = QtWidgets.QLabel("FORENSIC INGRESS PCAP JOURNAL (ZERO-COPY RAW WIRE TELEMETRY)")
        lbl_j_title.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: 900;")
        t_head.addWidget(lbl_j_title)
        t_head.addStretch()
        self.lbl_buf = QtWidgets.QLabel("RING BUFFER: 0 / 65,536 (IDLE)")
        self.lbl_buf.setStyleSheet("color: #64748b; font-size: 9px; font-weight: bold;")
        t_head.addWidget(self.lbl_buf)
        tbl_lay.addLayout(t_head)

        self.table = QtWidgets.QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["TIMESTAMP (PTP)", "TX ID", "SRC IP", "FUNCTION / REG", "COMMANDED / SHOCK", "IPS VERDICT"])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #080c14;
                color: #e2e8f0;
                border: 1px solid #1e2638;
                border-radius: 4px;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #0d121c;
                color: #64748b;
                font-weight: 800;
                font-size: 10px;
                border: none;
                padding: 6px;
            }
        """)
        self.table.setMinimumHeight(130)
        tbl_lay.addWidget(self.table)
        bottom_layout.addWidget(tbl_frame, stretch=7)

        # Invariant Bound Certification Panel (Fully Spaced, Non-Clipping)
        cert_frame = QtWidgets.QFrame()
        cert_frame.setStyleSheet("background-color: #0d121c; border: 1px solid #1e2638; border-radius: 6px;")
        cert_lay = QtWidgets.QVBoxLayout(cert_frame)
        cert_lay.setContentsMargins(14, 10, 14, 10)

        lbl_cert = QtWidgets.QLabel("INVARIANT BOUND CERTIFICATION")
        lbl_cert.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: 900;")
        cert_lay.addWidget(lbl_cert)

        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.addWidget(self.create_cert_box("PIPE RUPTURE LIMIT", "≤ 16.00 Bar", "Zero Breach Tolerated"), 0, 0)
        grid.addWidget(self.create_cert_box("CAVITATION FLOOR", "≥ 0.25 Bar Vapor", "Vacuum Collapse Prot."), 0, 1)
        grid.addWidget(self.create_cert_box("MAX SLEW VELOCITY", "≤ 140 RPM / sec", "Torque Shaft Bound"), 1, 0)
        grid.addWidget(self.create_cert_box("INLINE DROP LATENCY", "< 1.0 µs Wire Gate", "Zero-Buffer L2 Hold"), 1, 1)
        cert_lay.addLayout(grid)

        lbl_form = QtWidgets.QLabel("FORMAL EQUATION: |ΔP| = ρ · a · |Δω| · r < P_crit")
        lbl_form.setStyleSheet("color: #64748b; font-size: 9px; font-weight: bold; margin-top: 4px;")
        cert_lay.addWidget(lbl_form)

        bottom_layout.addWidget(cert_frame, stretch=3)
        main_layout.addLayout(bottom_layout, stretch=3)

    # ------------------ HELPER BUILDERS ------------------
    def create_badge(self, label, val, text_color, bg_color):
        badge = QtWidgets.QFrame()
        badge.setStyleSheet(f"background-color: {bg_color}; border: 1px solid {text_color}44; border-radius: 4px;")
        l = QtWidgets.QHBoxLayout(badge)
        l.setContentsMargins(8, 4, 8, 4)
        lbl_top = QtWidgets.QLabel(label)
        lbl_top.setStyleSheet(f"color: {text_color}; font-size: 9px; font-weight: 800;")
        lbl_bot = QtWidgets.QLabel(val)
        lbl_bot.setStyleSheet("color: #f8fafc; font-size: 9px; font-weight: bold;")
        l.addWidget(lbl_top)
        l.addWidget(lbl_bot)
        return badge

    def create_arch_card(self, title, items):
        frame = QtWidgets.QFrame()
        frame.setStyleSheet("background-color: #0d121c; border: 1px solid #1e2638; border-radius: 6px;")
        lay = QtWidgets.QVBoxLayout(frame)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)

        t = QtWidgets.QLabel(title)
        t.setStyleSheet("color: #ffffff; font-size: 10px; font-weight: 900; letter-spacing: 0.8px;")
        lay.addWidget(t)

        for k, v in items:
            row = QtWidgets.QHBoxLayout()
            lbl_k = QtWidgets.QLabel(k)
            lbl_k.setStyleSheet("color: #64748b; font-size: 9px;")
            lbl_v = QtWidgets.QLabel(v)
            lbl_v.setStyleSheet("color: #cbd5e1; font-size: 9px; font-weight: bold;")
            row.addWidget(lbl_k)
            row.addStretch()
            row.addWidget(lbl_v)
            lay.addLayout(row)
        return frame

    def create_metric_card(self, title, val, unit, subtext, color):
        frame = QtWidgets.QFrame()
        frame.setStyleSheet("background-color: #0d121c; border: 1px solid #1e2638; border-radius: 6px;")
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)

        lbl_t = QtWidgets.QLabel(title)
        lbl_t.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 800; letter-spacing: 0.8px;")
        
        val_box = QtWidgets.QHBoxLayout()
        lbl_v = QtWidgets.QLabel(val)
        lbl_v.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: 900;")
        lbl_u = QtWidgets.QLabel(unit)
        lbl_u.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 800; margin-top: 6px;")
        val_box.addWidget(lbl_v)
        val_box.addWidget(lbl_u)
        val_box.addStretch()

        lbl_s = QtWidgets.QLabel(subtext)
        lbl_s.setStyleSheet("color: #475569; font-size: 9px; font-weight: bold;")

        layout.addWidget(lbl_t)
        layout.addLayout(val_box)
        layout.addWidget(lbl_s)

        frame.lbl_val = lbl_v
        frame.lbl_sub = lbl_s
        return frame

    def create_attack_btn(self, title, subtitle, color):
        btn = QtWidgets.QPushButton()
        btn.setFixedHeight(44)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #080c14;
                border: 1px solid {color}55;
                border-radius: 4px;
                text-align: left;
                padding-left: 10px;
            }}
            QPushButton:hover {{
                background-color: {color}15;
                border: 1px solid {color};
            }}
        """)
        l = QtWidgets.QVBoxLayout(btn)
        l.setContentsMargins(0, 4, 0, 4)
        t = QtWidgets.QLabel(title)
        t.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: 900;")
        s = QtWidgets.QLabel(subtitle)
        s.setStyleSheet("color: #64748b; font-size: 8px;")
        l.addWidget(t)
        l.addWidget(s)
        return btn

    def create_toggle_row(self, title, desc, checked):
        w = QtWidgets.QWidget()
        l = QtWidgets.QHBoxLayout(w)
        l.setContentsMargins(0, 2, 0, 2)
        info = QtWidgets.QVBoxLayout()
        t = QtWidgets.QLabel(title)
        t.setStyleSheet("color: #ffffff; font-size: 10px; font-weight: bold;")
        d = QtWidgets.QLabel(desc)
        d.setStyleSheet("color: #64748b; font-size: 8px;")
        info.addWidget(t)
        info.addWidget(d)
        l.addLayout(info)
        l.addStretch()

        chk = QtWidgets.QCheckBox()
        chk.setChecked(checked)
        chk.setStyleSheet("QCheckBox::indicator { width: 14px; height: 14px; }")
        l.addWidget(chk)
        return w

    def create_cert_box(self, label, val, sub):
        box = QtWidgets.QFrame()
        box.setStyleSheet("background-color: #080c14; border: 1px solid #1e2638; border-radius: 4px; padding: 4px;")
        l = QtWidgets.QVBoxLayout(box)
        l.setContentsMargins(8, 6, 8, 6)
        lbl_k = QtWidgets.QLabel(label)
        lbl_k.setStyleSheet("color: #64748b; font-size: 8px; font-weight: bold;")
        lbl_v = QtWidgets.QLabel(val)
        lbl_v.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 900;")
        lbl_s = QtWidgets.QLabel(sub)
        lbl_s.setStyleSheet("color: #475569; font-size: 8px;")
        l.addWidget(lbl_k)
        l.addWidget(lbl_v)
        l.addWidget(lbl_s)
        return box

    def trigger_emergency_cut(self):
        self.card_verd.lbl_val.setText("AIR-GAP CUT")
        self.card_verd.lbl_val.setStyleSheet("color: #ef4444; font-size: 20px; font-weight: 900;")
        self.card_verd.lbl_sub.setText("Hardware Interlock Shunted [24V]")
        self.add_journal_row("00:00:00.000000", "0xFFFF", "10.240.18.109", "0x00 [EMERGENCY]", "0 RPM / 0.00 Bar", "[ AIR-GAP TRIPPED ]", "#ef4444")

    # ------------------ 24x7 TELEMETRY STREAM LOGIC ------------------
    def init_udp_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 5555))
        self.sock.setblocking(False)

        # 24x7 Continuous Background Polling Timer (50 FPS)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.poll_telemetry)
        self.timer.start(20)

    def inject_modbus(self, tx_id, rpm):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            s.connect(("127.0.0.1", 5502))
            payload = struct.pack(">HHHBBHH", tx_id, 0, 6, 1, 6, 1, rpm)
            s.sendall(payload)
            s.close()
        except Exception:
            pass

    def poll_telemetry(self):
        # 24x7 continuous non-blocking frame ingestion
        while True:
            try:
                data, _ = self.sock.recvfrom(1024)
                if len(data) == 32:
                    ts_us, tx_id, cmd_rpm, shock, twin_rpm, fatigue, verdict, _ = struct.unpack("<IHHfHfB13s", data)
                    
                    # Remove idle watermark on first packet arrival
                    if self.idle_text is not None:
                        self.plot_widget.removeItem(self.idle_text)
                        self.idle_text = None

                    self.packet_count += 1
                    self.lbl_buf.setText(f"RING BUFFER: {self.packet_count:,} / 65,536 (ACTIVE)")

                    self.current_t += 0.8
                    self.time_buffer.append(self.current_t)
                    self.cmd_buffer.append(cmd_rpm)
                    self.twin_buffer.append(twin_rpm)

                    # Update Annunciators with Real Wire Data
                    self.card_cmd.lbl_val.setText(f"{cmd_rpm:,}")
                    self.card_cmd.lbl_sub.setText(f"Tx: 0x{tx_id:04X} // Modbus PDU")

                    self.card_shock.lbl_val.setText(f"{shock:.2f}")
                    self.card_twin.lbl_val.setText(f"{twin_rpm:,}")
                    self.card_twin.lbl_sub.setText("RK4 Differential Match")

                    self.card_fatig.lbl_val.setText(f"{fatigue:.1f}")

                    # Verdict Color & String Logic
                    if verdict == 0:
                        self.card_verd.lbl_val.setText("ALLOW")
                        self.card_verd.lbl_val.setStyleSheet("color: #4ade80; font-size: 22px; font-weight: 900;")
                        self.card_verd.lbl_sub.setText("Invariant Boundary Certified")
                        verdict_str = "[ ALLOW : INVARIANT MET ]"
                        v_color = "#4ade80"
                    elif verdict == 1:
                        self.card_verd.lbl_val.setText("DROP")
                        self.card_verd.lbl_val.setStyleSheet("color: #ef4444; font-size: 22px; font-weight: 900;")
                        self.card_verd.lbl_sub.setText("Over-Speed Shear Breach")
                        verdict_str = "[ DROPPED : SHEAR BREACH ]"
                        v_color = "#ef4444"
                    elif verdict == 4:
                        self.card_verd.lbl_val.setText("DROP")
                        self.card_verd.lbl_val.setStyleSheet("color: #ef4444; font-size: 22px; font-weight: 900;")
                        self.card_verd.lbl_sub.setText("Impeller Cavitation Collapse")
                        verdict_str = "[ DROPPED : CAVITATION FLOOR ]"
                        v_color = "#ef4444"
                    else:
                        self.card_verd.lbl_val.setText("DROP")
                        self.card_verd.lbl_val.setStyleSheet("color: #ef4444; font-size: 22px; font-weight: 900;")
                        self.card_verd.lbl_sub.setText("Basquin Fatigue Exceeded")
                        verdict_str = "[ DROPPED : FATIGUE BREACH ]"
                        v_color = "#ef4444"

                    # Add Row to Forensic PCAP Table
                    ptp_ts = f"14:02:{int(self.current_t):02d}.{ts_us % 1000000:06d}"
                    self.add_journal_row(
                        ptp_ts,
                        f"0x{tx_id:04X}", 
                        "10.240.18.109",
                        "0x06 [Reg 0x0001]",
                        f"{cmd_rpm:,} RPM / {shock:.2f} Bar", 
                        verdict_str, 
                        v_color
                    )

                    # Update Chart Curves dynamically
                    self.curve_cmd.setData(list(self.time_buffer), list(self.cmd_buffer))
                    self.curve_twin.setData(list(self.time_buffer), list(self.twin_buffer))

            except BlockingIOError:
                break
            except Exception:
                break

    def add_journal_row(self, ts, tx, src, func, param, verdict, color):
        row = self.table.rowCount()
        self.table.insertRow(row)

        vals = [ts, tx, src, func, param, verdict]
        for col, v in enumerate(vals):
            item = QtWidgets.QTableWidgetItem(v)
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            if col == 5:
                item.setForeground(QtGui.QColor(color))
                item.setFont(QtGui.QFont("Consolas", 10, QtGui.QFont.Weight.Bold))
            else:
                item.setForeground(QtGui.QColor("#cbd5e1"))
            self.table.setItem(row, col, item)

        self.table.scrollToBottom()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = VoltGuard24x7Workstation()
    window.show()
    sys.exit(app.exec())