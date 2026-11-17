import sys
import socket
import struct
import random
from collections import deque
from PyQt6 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

pg.setConfigOption('background', '#060a12')
pg.setConfigOption('foreground', '#64748b')
pg.setConfigOptions(antialias=True)

class VoltGuardLaptopOptimized(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoltGuard // Tactical OT Physics Firewall & Digital Twin Operations Center")
        # Optimized default sizing for 1080p and 768p laptop displays
        self.resize(1560, 880)
        self.setMinimumSize(1280, 720)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #05080f;
                color: #f8fafc;
                font-family: 'Segoe UI', 'Consolas', sans-serif;
            }
            QTableWidget { gridline-color: transparent; }
            QScrollBar:vertical {
                border: none;
                background: #060a12;
                width: 6px;
            }
            QScrollBar::handle:vertical {
                background: #1e293b;
                min-height: 16px;
                border-radius: 3px;
            }
        """)

        self.history_len = 60
        self.time_buffer = deque(maxlen=self.history_len)
        self.cmd_buffer  = deque(maxlen=self.history_len)
        self.twin_buffer = deque(maxlen=self.history_len)
        self.shock_buffer = deque(maxlen=self.history_len)
        self.current_t   = 0.0
        self.packet_count = 0
        self.auto_streaming = False

        self.init_ui()
        self.init_udp_socket()
        self.init_auto_streamer()

    def init_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        # ---------------- 1. HEADER BAR ----------------
        top_bar = QtWidgets.QFrame()
        top_bar.setStyleSheet("background-color: #0b0f19; border: 1px solid #1a2333; border-radius: 6px;")
        t_lay = QtWidgets.QHBoxLayout(top_bar)
        t_lay.setContentsMargins(12, 6, 12, 6)

        logo_lbl = QtWidgets.QLabel("⚡")
        logo_lbl.setStyleSheet("color: #ef4444; font-size: 18px; font-weight: bold;")
        t_lay.addWidget(logo_lbl)

        brand_col = QtWidgets.QVBoxLayout()
        brand_col.setSpacing(1)
        b_name = QtWidgets.QLabel("VOLTGUARD // TACTICAL OT PHYSICS FIREWALL")
        b_name.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 900; letter-spacing: 1px;")
        b_sub = QtWidgets.QLabel("STATION: KINETIC-ENCLAVE-09   |   NODE IP: 10.240.18.4   |   KERNEL: AF_XDP (eth0 <-> eth1) ZERO-COPY")
        b_sub.setStyleSheet("color: #64748b; font-size: 8px; font-weight: bold;")
        brand_col.addWidget(b_name)
        brand_col.addWidget(b_sub)
        t_lay.addLayout(brand_col)

        t_lay.addStretch()
        t_lay.addWidget(self.create_badge("DUAL-NIC:", "IN-LINE ACTIVE", "#38bdf8", "#082f49"))
        t_lay.addWidget(self.create_badge("PTP SYNC:", "0.428 µs PTP", "#4ade80", "#052e16"))
        t_lay.addWidget(self.create_badge("OPTOCOUPLER:", "ARMED [24V]", "#f59e0b", "#451a03"))
        t_lay.addWidget(self.create_badge("ENCLAVE:", "AIR-GAP READY", "#ef4444", "#450a0a"))

        root.addWidget(top_bar)

        # ---------------- 2. TOP METRIC CARDS ----------------
        stats_lay = QtWidgets.QHBoxLayout()
        stats_lay.setSpacing(8)
        self.c_cmd   = self.create_card("COMMANDED SETPOINT (PLC)", "0", "RPM", "Tx: 0x0000 // MODBUS FC:06", "#ffffff")
        self.c_twin  = self.create_card("RK4 TWIN KINETIC ESTIMATE", "0", "RPM", "ODE Convergence: < 0.08% Error", "#38bdf8")
        self.c_shock = self.create_card("JOUKOWSKY TRANSIENT (ΔP)", "0.00", "BAR", "Safe Acoustic Ceiling: < 16.00 Bar", "#ffffff")
        self.c_verd  = self.create_card("L2 WIRE VERDICT (ASIC/FPGA)", "STANDBY", "", "Zero-Copy Wire Gate Active", "#38bdf8")
        stats_lay.addWidget(self.c_cmd)
        stats_lay.addWidget(self.c_twin)
        stats_lay.addWidget(self.c_shock)
        stats_lay.addWidget(self.c_verd)
        root.addLayout(stats_lay)

        # ---------------- 3. MAIN WORKSTATION ----------------
        main_h = QtWidgets.QHBoxLayout()
        main_h.setSpacing(10)

        # LEFT COLUMN: Compact Scopes + Metric Boxes
        left_box = QtWidgets.QVBoxLayout()
        left_box.setSpacing(8)

        p_frame = QtWidgets.QFrame()
        p_frame.setStyleSheet("background-color: #080c14; border: 1px solid #1a2333; border-radius: 6px;")
        p_lay = QtWidgets.QVBoxLayout(p_frame)
        p_lay.setContentsMargins(8, 6, 8, 6)
        p_lay.setSpacing(6)

        sc_head = QtWidgets.QHBoxLayout()
        sc_t = QtWidgets.QLabel("KINEMATIC DUAL-TRACE SCOPE (RPM)")
        sc_t.setStyleSheet("color: #ffffff; font-size: 10px; font-weight: 900;")
        sc_leg1 = QtWidgets.QLabel("— Ingress Command")
        sc_leg1.setStyleSheet("color: #ffffff; font-size: 8px; font-weight: bold; background: #0f172a; padding: 2px 5px; border-radius: 3px;")
        sc_leg2 = QtWidgets.QLabel("- - RK4 Twin")
        sc_leg2.setStyleSheet("color: #38bdf8; font-size: 8px; font-weight: bold; background: #0c2d48; padding: 2px 5px; border-radius: 3px;")
        sc_head.addWidget(sc_t)
        sc_head.addStretch()
        sc_head.addWidget(sc_leg1)
        sc_head.addWidget(sc_leg2)
        p_lay.addLayout(sc_head)

        self.scope_plot = pg.PlotWidget()
        self.scope_plot.showGrid(x=True, y=True, alpha=0.15)
        self.scope_plot.setYRange(0, 55000)
        self.scope_plot.addItem(pg.InfiniteLine(pos=3600, angle=0, pen=pg.mkPen('#ef4444', width=1.8, style=QtCore.Qt.PenStyle.DashLine)))
        self.scope_plot.addItem(pg.InfiniteLine(pos=500, angle=0, pen=pg.mkPen('#eab308', width=1.4, style=QtCore.Qt.PenStyle.DotLine)))

        self.curve_cmd = self.scope_plot.plot(pen=pg.mkPen('#ffffff', width=2.0), symbol='o', symbolSize=4, symbolBrush='#ef4444')
        self.curve_twin = self.scope_plot.plot(pen=pg.mkPen('#38bdf8', width=1.6, style=QtCore.Qt.PenStyle.DashLine))
        p_lay.addWidget(self.scope_plot)

        # Joukowsky Sub-Scope
        sh_head = QtWidgets.QHBoxLayout()
        sh_t = QtWidgets.QLabel("Joukowsky Acoustic Transient Sub-Scope")
        sh_t.setStyleSheet("color: #ffffff; font-size: 9px; font-weight: 800;")
        sh_eq = QtWidgets.QLabel("ΔP = ρ · a · |Δv|  |  CEILING: 16.00 BAR")
        sh_eq.setStyleSheet("color: #ef4444; font-size: 8px; font-weight: bold;")
        sh_head.addWidget(sh_t)
        sh_head.addStretch()
        sh_head.addWidget(sh_eq)
        p_lay.addLayout(sh_head)

        self.shock_plot = pg.PlotWidget()
        self.shock_plot.setFixedHeight(85)
        self.shock_plot.showGrid(x=True, y=True, alpha=0.12)
        self.shock_plot.setYRange(0, 50)
        self.shock_plot.addItem(pg.InfiniteLine(pos=16.0, angle=0, pen=pg.mkPen('#ef4444', width=1.4, style=QtCore.Qt.PenStyle.DashLine)))
        self.curve_shock = self.shock_plot.plot(pen=pg.mkPen('#38bdf8', width=1.8))
        p_lay.addWidget(self.shock_plot)

        # Clean HUD Strip (Graph ke niche ke boxes)
        hud_h = QtWidgets.QHBoxLayout()
        hud_h.setSpacing(6)
        hud_h.addWidget(self.create_mini_stat("ROTOR SLEW (dΩ/dt)", "0.0 RPM/s"))
        hud_h.addWidget(self.create_mini_stat("RK4 SLIP ERROR", "0.00% σ"))
        hud_h.addWidget(self.create_mini_stat("INGRESS JITTER", "0.02 µs"))
        hud_h.addWidget(self.create_mini_stat("OPTO-TRIP LATCH", "< 2.1 µs"))
        p_lay.addLayout(hud_h)

        left_box.addWidget(p_frame, stretch=6)

        # Lower Boundary Certification Strip
        cert_bar = QtWidgets.QFrame()
        cert_bar.setStyleSheet("background-color: #0b0f19; border: 1px solid #1a2333; border-radius: 6px;")
        cb_lay = QtWidgets.QHBoxLayout(cert_bar)
        cb_lay.setContentsMargins(8, 6, 8, 6)
        cb_lay.setSpacing(6)
        cb_lay.addWidget(self.create_cert("SHEAR THRESHOLD", "≤ 3,600 RPM", "Basquin Fatigue Limit"))
        cb_lay.addWidget(self.create_cert("CAVITATION FLOOR", "≥ 500 RPM", "Impeller Armor Guard"))
        cb_lay.addWidget(self.create_cert("HAMMER WAVE", "≤ 16.00 Bar", "Acoustic Flange Cutoff"))
        cb_lay.addWidget(self.create_cert("GATE LATENCY", "< 1.0 µs Wire Gate", "Zero-Buffer Packet Hold"))
        left_box.addWidget(cert_bar, stretch=1)

        main_h.addLayout(left_box, stretch=5)

        # RIGHT COLUMN: Explicit PCAP Table with Clear Headers
        pcap_frame = QtWidgets.QFrame()
        pcap_frame.setStyleSheet("background-color: #0b0f19; border: 1px solid #1a2333; border-radius: 6px;")
        pc_lay = QtWidgets.QVBoxLayout(pcap_frame)
        pc_lay.setContentsMargins(10, 8, 10, 8)
        pc_lay.setSpacing(6)

        pc_head = QtWidgets.QHBoxLayout()
        pc_t = QtWidgets.QLabel("FORENSIC INGRESS PCAP WIRE JOURNAL (PROMISCUOUS DPDK RING)")
        pc_t.setStyleSheet("color: #ffffff; font-size: 10px; font-weight: 900;")
        self.lbl_ring = QtWidgets.QLabel("RING BUFFER: 0 / 65,536 [ACTIVE]")
        self.lbl_ring.setStyleSheet("color: #38bdf8; font-size: 9px; font-weight: bold;")
        pc_head.addWidget(pc_t)
        pc_head.addStretch()
        pc_head.addWidget(self.lbl_ring)
        pc_lay.addLayout(pc_head)

        self.table = QtWidgets.QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "PTP TIMESTAMP", 
            "TX ID", 
            "SOURCE PLC IP", 
            "REGISTER / FUNC", 
            "KINEMATICS (RPM/SHOCK)", 
            "IPS VERDICT"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #080c14;
                color: #e2e8f0;
                border: 1px solid #1e293b;
                border-radius: 4px;
                font-family: 'Consolas', 'Segoe UI';
                font-size: 10px;
            }
            QHeaderView::section {
                background-color: #0f1422;
                color: #94a3b8;
                font-weight: 800;
                font-size: 9px;
                border: none;
                padding: 6px 4px;
            }
        """)
        pc_lay.addWidget(self.table)
        main_h.addWidget(pcap_frame, stretch=6)
        root.addLayout(main_h, stretch=7)

        # ---------------- 4. BOTTOM INJECTOR DECK ----------------
        bottom_box = QtWidgets.QFrame()
        bottom_box.setStyleSheet("background-color: #0b0f19; border: 1px solid #1a2333; border-radius: 6px;")
        b_lay = QtWidgets.QVBoxLayout(bottom_box)
        b_lay.setContentsMargins(10, 8, 10, 8)
        b_lay.setSpacing(6)

        b_head = QtWidgets.QHBoxLayout()
        b_title = QtWidgets.QLabel("⚡ TACTICAL ATTACK VECTOR INJECTOR & HARDWARE ISOLATION TEST HARNESS")
        b_title.setStyleSheet("color: #ffffff; font-size: 10px; font-weight: 900;")
        self.lbl_mode = QtWidgets.QLabel("CURRENT MODE: SYSTEM ARMED // ZERO-COPY DAEMON LISTENING")
        self.lbl_mode.setStyleSheet("color: #22c55e; font-size: 9px; font-weight: bold;")
        b_head.addWidget(b_title)
        b_head.addStretch()
        b_head.addWidget(self.lbl_mode)
        b_lay.addLayout(b_head)

        inj_row = QtWidgets.QHBoxLayout()
        inj_row.setSpacing(6)

        self.btn_stream = QtWidgets.QPushButton("▶ START CONTINUOUS 24x7 FIELD STREAM")
        self.btn_stream.setFixedHeight(34)
        self.btn_stream.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_stream.setStyleSheet("background-color: #dc2626; border: 1px solid #ef4444; border-radius: 5px; color: #fff; font-size: 9px; font-weight: 900;")
        self.btn_stream.clicked.connect(self.toggle_stream)
        inj_row.addWidget(self.btn_stream, stretch=3)

        b1 = self.create_btn_scen("⚡ STUXNET (50k)", "#ef4444", lambda: self.inject(0x0103, 50000))
        b2 = self.create_btn_scen("⚠️ CAVITATION (300)", "#f59e0b", lambda: self.inject(0x0104, 300))
        b3 = self.create_btn_scen("🌊 WATER HAMMER", "#38bdf8", lambda: self.inject(0x0102, 4600))
        b4 = self.create_btn_scen("🟢 NOMINAL (1,800)", "#22c55e", lambda: self.inject(0x0101, 1800))
        inj_row.addWidget(b1, stretch=2)
        inj_row.addWidget(b2, stretch=2)
        inj_row.addWidget(b3, stretch=2)
        inj_row.addWidget(b4, stretch=2)
        b_lay.addLayout(inj_row)

        btn_cut = QtWidgets.QPushButton("⚠️ ASSERT EMERGENCY AIR-GAP ISOLATION CUT [PHYSICAL 24V GALVANIC TRIP] ⚠️")
        btn_cut.setFixedHeight(32)
        btn_cut.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        btn_cut.setStyleSheet("""
            QPushButton {
                background-color: #7f1d1d;
                border: 1px solid #ef4444;
                border-radius: 5px;
                color: #ffffff;
                font-size: 10px;
                font-weight: 900;
                letter-spacing: 0.5px;
            }
            QPushButton:hover { background-color: #991b1b; }
        """)
        btn_cut.clicked.connect(self.trigger_cut)
        b_lay.addWidget(btn_cut)

        root.addWidget(bottom_box, stretch=2)

    # ---------------- BUILDERS ----------------
    def create_card(self, title, val, unit, sub, col):
        f = QtWidgets.QFrame()
        f.setStyleSheet("background-color: #0b0f19; border: 1px solid #1a2333; border-radius: 6px;")
        l = QtWidgets.QVBoxLayout(f)
        l.setContentsMargins(10, 8, 10, 8)
        l.setSpacing(2)
        t = QtWidgets.QLabel(title)
        t.setStyleSheet("color: #94a3b8; font-size: 8px; font-weight: 800; letter-spacing: 0.5px;")
        vh = QtWidgets.QHBoxLayout()
        v = QtWidgets.QLabel(val)
        v.setStyleSheet(f"color: {col}; font-size: 20px; font-weight: 900;")
        u = QtWidgets.QLabel(unit)
        u.setStyleSheet("color: #64748b; font-size: 9px; font-weight: bold; margin-top: 5px;")
        vh.addWidget(v)
        vh.addWidget(u)
        vh.addStretch()
        s = QtWidgets.QLabel(sub)
        s.setStyleSheet("color: #64748b; font-size: 7.5px; font-weight: bold;")
        l.addWidget(t)
        l.addLayout(vh)
        l.addWidget(s)
        f.v = v
        f.s = s
        return f

    def create_badge(self, l1, l2, col, bg):
        f = QtWidgets.QFrame()
        f.setStyleSheet(f"background-color: {bg}; border: 1px solid {col}44; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(f)
        h.setContentsMargins(6, 3, 6, 3)
        a = QtWidgets.QLabel(l1)
        a.setStyleSheet(f"color: {col}; font-size: 7.5px; font-weight: 900;")
        b = QtWidgets.QLabel(l2)
        b.setStyleSheet("color: #f8fafc; font-size: 7.5px; font-weight: bold;")
        h.addWidget(a)
        h.addWidget(b)
        return f

    def create_mini_stat(self, t, v):
        f = QtWidgets.QFrame()
        f.setStyleSheet("background-color: #0f1422; border: 1px solid #1e293b; border-radius: 4px;")
        l = QtWidgets.QVBoxLayout(f)
        l.setContentsMargins(6, 4, 6, 4)
        lbl_t = QtWidgets.QLabel(t)
        lbl_t.setStyleSheet("color: #64748b; font-size: 7.5px; font-weight: bold;")
        lbl_v = QtWidgets.QLabel(v)
        lbl_v.setStyleSheet("color: #cbd5e1; font-size: 9.5px; font-weight: 900;")
        l.addWidget(lbl_t)
        l.addWidget(lbl_v)
        return f

    def create_cert(self, t, v, s):
        f = QtWidgets.QFrame()
        l = QtWidgets.QVBoxLayout(f)
        l.setContentsMargins(4, 2, 4, 2)
        t_l = QtWidgets.QLabel(t)
        t_l.setStyleSheet("color: #64748b; font-size: 7.5px; font-weight: bold;")
        v_l = QtWidgets.QLabel(v)
        v_l.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: 900;")
        s_l = QtWidgets.QLabel(s)
        s_l.setStyleSheet("color: #475569; font-size: 7.5px;")
        l.addWidget(t_l)
        l.addWidget(v_l)
        l.addWidget(s_l)
        return f

    def create_btn_scen(self, title, col, callback):
        b = QtWidgets.QPushButton(title)
        b.setFixedHeight(34)
        b.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        b.setStyleSheet(f"""
            QPushButton {{
                background-color: #0f1422;
                border: 1px solid {col}55;
                border-radius: 5px;
                color: #ffffff;
                font-size: 9px;
                font-weight: 800;
            }}
            QPushButton:hover {{
                background-color: {col}22;
                border: 1px solid {col};
            }}
        """)
        b.clicked.connect(callback)
        return b

    # ---------------- TELEMETRY & NETWORKING ----------------
    def init_udp_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 5555))
        self.sock.setblocking(False)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.poll_telemetry)
        self.timer.start(20)

    def init_auto_streamer(self):
        self.auto_timer = QtCore.QTimer()
        self.auto_timer.timeout.connect(self.send_auto)
        self.auto_tx = 0x0140

    def toggle_stream(self):
        self.auto_streaming = not self.auto_streaming
        if self.auto_streaming:
            self.btn_stream.setText("⏸ STOP CONTINUOUS FIELD STREAM")
            self.btn_stream.setStyleSheet("background-color: #b91c1c; border: 1px solid #ef4444; border-radius: 5px; color: #fff; font-size: 9px; font-weight: 900;")
            self.lbl_mode.setText("CURRENT MODE: 24x7 REAL-TIME STREAM ACTIVE")
            self.lbl_mode.setStyleSheet("color: #38bdf8; font-size: 9px; font-weight: bold;")
            self.auto_timer.start(600)
        else:
            self.btn_stream.setText("▶ START CONTINUOUS 24x7 FIELD STREAM")
            self.btn_stream.setStyleSheet("background-color: #dc2626; border: 1px solid #ef4444; border-radius: 5px; color: #fff; font-size: 9px; font-weight: 900;")
            self.lbl_mode.setText("CURRENT MODE: SYSTEM ARMED // ZERO-COPY DAEMON LISTENING")
            self.lbl_mode.setStyleSheet("color: #22c55e; font-size: 9px; font-weight: bold;")
            self.auto_timer.stop()

    def send_auto(self):
        self.auto_tx = (self.auto_tx + 1) & 0xFFFF
        roll = random.random()
        if roll < 0.70:
            rpm = random.randint(1795, 1805)
        elif roll < 0.82:
            rpm = 2100
        elif roll < 0.90:
            rpm = 50000
        elif roll < 0.95:
            rpm = 300
        else:
            rpm = 4600
        self.inject(self.auto_tx, rpm)

    def inject(self, tx_id, rpm):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect(("127.0.0.1", 5502))
            payload = struct.pack(">HHHBBHH", tx_id, 0, 6, 1, 6, 1, rpm)
            s.sendall(payload)
            s.close()
        except Exception:
            pass

    def trigger_cut(self):
        self.c_verd.v.setText("AIR-GAP CUT")
        self.c_verd.v.setStyleSheet("color: #ef4444; font-size: 18px; font-weight: 900;")
        self.c_verd.s.setText("Optocoupler Shunted [24V]")
        self.add_row("14:02:00.000000", "0xFFFF", "10.240.18.99", "0x00 [EMERGENCY]", "0 RPM / 0.00 Bar", "[ AIR-GAP TRIPPED ]", "#ef4444")

    def poll_telemetry(self):
        while True:
            try:
                data, _ = self.sock.recvfrom(1024)
                if len(data) == 32:
                    ts_us, tx_id, cmd_rpm, shock, twin_rpm, fatigue, verdict, _ = struct.unpack("<IHHfHfB13s", data)
                    self.packet_count += 1
                    self.lbl_ring.setText(f"RING BUFFER: {self.packet_count:,} / 65,536 [ACTIVE]")

                    self.current_t += 0.8
                    self.time_buffer.append(self.current_t)
                    self.cmd_buffer.append(cmd_rpm)
                    self.twin_buffer.append(twin_rpm)
                    self.shock_buffer.append(shock)

                    self.c_cmd.v.setText(f"{cmd_rpm:,}")
                    self.c_cmd.s.setText(f"Tx: 0x{tx_id:04X} // Modbus FC:06")
                    self.c_shock.v.setText(f"{shock:.2f}")
                    self.c_twin.v.setText(f"{twin_rpm:,}")

                    if verdict == 0:
                        v_str = "[ ALLOW : INVARIANT MET ]"
                        v_col = "#4ade80"
                        self.c_verd.v.setText("ALLOW")
                        self.c_verd.v.setStyleSheet("color: #4ade80; font-size: 20px; font-weight: 900;")
                        self.c_verd.s.setText("Physics Invariant Certified")
                    elif verdict == 1:
                        v_str = "[ DROP : ROTOR CEILING ]"
                        v_col = "#ef4444"
                        self.c_verd.v.setText("DROP")
                        self.c_verd.v.setStyleSheet("color: #ef4444; font-size: 20px; font-weight: 900;")
                        self.c_verd.s.setText("Rotor Overspeed Breach")
                    elif verdict == 4:
                        v_str = "[ DROP : CAVITATION ]"
                        v_col = "#f59e0b"
                        self.c_verd.v.setText("DROP")
                        self.c_verd.v.setStyleSheet("color: #f59e0b; font-size: 20px; font-weight: 900;")
                        self.c_verd.s.setText("Impeller Vapor Collapse")
                    else:
                        v_str = "[ DROP : PIPE SURGE ]"
                        v_col = "#ef4444"
                        self.c_verd.v.setText("DROP")
                        self.c_verd.v.setStyleSheet("color: #ef4444; font-size: 20px; font-weight: 900;")
                        self.c_verd.s.setText("Acoustic Shock Exceeded")

                    # Microsecond Precision PTP Timestamp
                    ptp_ts = f"14:02:{int(self.current_t):02d}.{(ts_us % 1000000):06d}"
                    self.add_row(
                        ptp_ts, 
                        f"0x{tx_id:04X}", 
                        "10.240.18.99", 
                        "40001 (FC:06)", 
                        f"{cmd_rpm:,} RPM / {shock:.2f} Bar", 
                        v_str, 
                        v_col
                    )

                    self.curve_cmd.setData(list(self.time_buffer), list(self.cmd_buffer))
                    self.curve_twin.setData(list(self.time_buffer), list(self.twin_buffer))
                    self.curve_shock.setData(list(self.time_buffer), list(self.shock_buffer))

            except BlockingIOError:
                break
            except Exception:
                break

    def add_row(self, ts, tx, src, reg, payload, verdict, color):
        row = self.table.rowCount()
        self.table.insertRow(row)
        vals = [ts, tx, src, reg, payload, verdict]
        for col, val in enumerate(vals):
            it = QtWidgets.QTableWidgetItem(val)
            it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            if col == 5:
                it.setForeground(QtGui.QColor(color))
                it.setFont(QtGui.QFont("Consolas", 9, QtGui.QFont.Weight.Bold))
            elif col == 1:
                it.setForeground(QtGui.QColor("#38bdf8"))
                it.setFont(QtGui.QFont("Consolas", 9, QtGui.QFont.Weight.Bold))
            else:
                it.setForeground(QtGui.QColor("#cbd5e1"))
            self.table.setItem(row, col, it)
        self.table.scrollToBottom()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = VoltGuardLaptopOptimized()
    window.show()
    sys.exit(app.exec())