import sys
import socket
import struct
import random
from collections import deque
from PyQt6 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

# Configure pure industrial dark canvas
pg.setConfigOption('background', '#03060c')
pg.setConfigOption('foreground', '#475569')
pg.setConfigOptions(antialias=True)

class VoltGuardZeroStateConsole(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoltGuard // Tactical OT Physics Firewall Command Center")
        self.resize(1640, 920)
        self.setMinimumSize(1280, 740)

        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #05080f, stop:0.5 #080d18, stop:1 #03060c);
                color: #f8fafc;
                font-family: 'Segoe UI', 'Consolas', sans-serif;
            }
            QTableWidget { gridline-color: transparent; }
            QScrollBar:vertical {
                border: 1px solid #111827;
                background: #04070e;
                width: 7px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e293b, stop:1 #334155);
                min-height: 20px;
                border-radius: 3px;
                border-top: 1px solid #475569;
            }
        """)

        # Buffers are strictly empty at startup - ZERO DATA
        self.history_len = 65
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
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        # ---------------- 1. 3D CHISELED HEADER ----------------
        top_bar = QtWidgets.QFrame()
        top_bar.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #131b2c, stop:1 #080d16);
            border: 1px solid #23314a;
            border-top: 1px solid #3b4e72;
            border-bottom: 2px solid #020509;
            border-radius: 8px;
        """)
        t_lay = QtWidgets.QHBoxLayout(top_bar)
        t_lay.setContentsMargins(14, 8, 14, 8)

        logo_lbl = QtWidgets.QLabel("⚡")
        logo_lbl.setStyleSheet("color: #ef4444; font-size: 22px; font-weight: bold;")
        t_lay.addWidget(logo_lbl)

        brand_col = QtWidgets.QVBoxLayout()
        brand_col.setSpacing(1)
        b_name = QtWidgets.QLabel("VOLTGUARD // TACTICAL OT PHYSICS FIREWALL")
        b_name.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 900; letter-spacing: 1.5px;")
        b_sub = QtWidgets.QLabel("STATION: KINETIC-ENCLAVE-09   |   NODE IP: 10.240.18.4   |   INTERFACE: AF_XDP (eth0 <-> eth1) ZERO-COPY")
        b_sub.setStyleSheet("color: #64748b; font-size: 8.5px; font-weight: bold;")
        brand_col.addWidget(b_name)
        brand_col.addWidget(b_sub)
        t_lay.addLayout(brand_col)

        t_lay.addStretch()
        t_lay.addWidget(self.create_badge("DUAL-NIC:", "IN-LINE ACTIVE", "#00f0ff", "#042f40"))
        t_lay.addWidget(self.create_badge("IEEE 1588 PTP:", "0.428 µs PTP-SYNC", "#00ff88", "#03351d"))
        t_lay.addWidget(self.create_badge("OPTO-COUPLER:", "ARMED [24V LATCH]", "#fbbf24", "#3b2304"))
        t_lay.addWidget(self.create_badge("ENCLAVE:", "AIR-GAP READY", "#ff3366", "#3d0815"))

        root.addWidget(top_bar)

        # ---------------- 2. STANDBY ZERO-STATE TOP METRICS ----------------
        stats_lay = QtWidgets.QHBoxLayout()
        stats_lay.setSpacing(10)
        self.c_cmd   = self.create_card("COMMANDED SETPOINT (PLC)", "0", "RPM", "Awaiting Modbus TCP/IP Ingress...", "#00f0ff")
        self.c_twin  = self.create_card("RK4 TWIN KINETIC ESTIMATE", "0", "RPM", "Inertia Model: Quiescent / Synchronized", "#c084fc")
        self.c_shock = self.create_card("JOUKOWSKY TRANSIENT (ΔP)", "0.00", "BAR", "Baseline Acoustic Head: 0.00 Bar", "#34d399")
        self.c_verd  = self.create_card("L2 WIRE VERDICT (ASIC / FPGA)", "STANDBY : LISTENING", "", "Zero-Copy FPGA Wire Tap Active", "#38bdf8")
        stats_lay.addWidget(self.c_cmd)
        stats_lay.addWidget(self.c_twin)
        stats_lay.addWidget(self.c_shock)
        stats_lay.addWidget(self.c_verd)
        root.addLayout(stats_lay)

        # ---------------- 3. MAIN WORKBENCH ----------------
        main_h = QtWidgets.QHBoxLayout()
        main_h.setSpacing(12)

        # LEFT: Scope Bay
        left_box = QtWidgets.QVBoxLayout()
        left_box.setSpacing(8)

        p_frame = QtWidgets.QFrame()
        p_frame.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0d1422, stop:1 #060912);
            border: 1px solid #1a273e;
            border-top: 1px solid #2e446d;
            border-bottom: 2px solid #020509;
            border-radius: 8px;
        """)
        p_lay = QtWidgets.QVBoxLayout(p_frame)
        p_lay.setContentsMargins(10, 8, 10, 8)
        p_lay.setSpacing(6)

        sc_head = QtWidgets.QHBoxLayout()
        sc_t = QtWidgets.QLabel("● KINEMATIC DUAL-TRACE SCOPE (RPM)")
        sc_t.setStyleSheet("color: #00f0ff; font-size: 10.5px; font-weight: 900; letter-spacing: 0.5px;")
        self.sc_tag = QtWidgets.QLabel("STANDBY : AWAITING INGRESS")
        self.sc_tag.setStyleSheet("color: #64748b; font-size: 8px; font-weight: bold; background: #08111e; border: 1px solid #1e293b; padding: 2px 5px; border-radius: 3px;")
        sc_leg1 = QtWidgets.QLabel("— Ingress Command")
        sc_leg1.setStyleSheet("color: #00f0ff; font-size: 8px; font-weight: bold; background: #082f49; padding: 2px 6px; border-radius: 3px; border: 1px solid #0284c7;")
        sc_leg2 = QtWidgets.QLabel("- - RK4 Twin")
        sc_leg2.setStyleSheet("color: #c084fc; font-size: 8px; font-weight: bold; background: #2e1065; padding: 2px 6px; border-radius: 3px; border: 1px solid #9333ea;")
        sc_head.addWidget(sc_t)
        sc_head.addWidget(self.sc_tag)
        sc_head.addStretch()
        sc_head.addWidget(sc_leg1)
        sc_head.addWidget(sc_leg2)
        p_lay.addLayout(sc_head)

        # Plot Widget
        self.scope_plot = pg.PlotWidget()
        self.scope_plot.setStyleSheet("border: 1px solid #141e30; border-radius: 4px; background: #03060c;")
        self.scope_plot.showGrid(x=True, y=True, alpha=0.15)
        self.scope_plot.setYRange(0, 55000)

        # Physical limit tripwires (structural guides, not data)
        line_shear = pg.InfiniteLine(pos=3600, angle=0, pen=pg.mkPen('#ff2255', width=1.8, style=QtCore.Qt.PenStyle.DashLine))
        line_cavit = pg.InfiniteLine(pos=500, angle=0, pen=pg.mkPen('#f59e0b', width=1.4, style=QtCore.Qt.PenStyle.DotLine))
        self.scope_plot.addItem(line_shear)
        self.scope_plot.addItem(line_cavit)

        # Curves start with empty data lists []
        self.curve_cmd = self.scope_plot.plot(
            pen=pg.mkPen('#00f0ff', width=2.2), 
            symbol='o', 
            symbolSize=5, 
            symbolBrush='#ff3366'
        )
        self.curve_twin = self.scope_plot.plot(
            pen=pg.mkPen('#c084fc', width=1.8, style=QtCore.Qt.PenStyle.DashLine),
            fillLevel=0,
            brush=pg.mkBrush(192, 132, 252, 25)
        )
        p_lay.addWidget(self.scope_plot)

        # Joukowsky Sub-Scope
        sh_head = QtWidgets.QHBoxLayout()
        sh_t = QtWidgets.QLabel("● Joukowsky Acoustic Transient Sub-Scope")
        sh_t.setStyleSheet("color: #ff3366; font-size: 9px; font-weight: 800;")
        sh_eq = QtWidgets.QLabel("ΔP = ρ · a · |Δv|   |   RUPTURE CEILING: 16.00 BAR")
        sh_eq.setStyleSheet("color: #fb7185; font-size: 8px; font-weight: bold;")
        sh_head.addWidget(sh_t)
        sh_head.addStretch()
        sh_head.addWidget(sh_eq)
        p_lay.addLayout(sh_head)

        self.shock_plot = pg.PlotWidget()
        self.shock_plot.setFixedHeight(85)
        self.shock_plot.setStyleSheet("border: 1px solid #141e30; border-radius: 4px; background: #03060c;")
        self.shock_plot.showGrid(x=True, y=True, alpha=0.12)
        self.shock_plot.setYRange(0, 50)
        self.shock_plot.addItem(pg.InfiniteLine(pos=16.0, angle=0, pen=pg.mkPen('#ff2255', width=1.4, style=QtCore.Qt.PenStyle.DashLine)))
        self.curve_shock = self.shock_plot.plot(
            pen=pg.mkPen('#00f0ff', width=1.8),
            fillLevel=0,
            brush=pg.mkBrush(0, 240, 255, 25)
        )
        p_lay.addWidget(self.shock_plot)

        # Mini HUD
        hud_h = QtWidgets.QHBoxLayout()
        hud_h.setSpacing(6)
        hud_h.addWidget(self.create_mini_stat("ROTOR SLEW (dΩ/dt)", "0.0 RPM/s", "#38bdf8"))
        hud_h.addWidget(self.create_mini_stat("RK4 SLIP ERROR", "0.00% σ", "#c084fc"))
        hud_h.addWidget(self.create_mini_stat("INGRESS JITTER", "0.00 µs", "#34d399"))
        hud_h.addWidget(self.create_mini_stat("HARDWARE TRIP LATCH", "ARMED [STANDBY]", "#00ff88"))
        p_lay.addLayout(hud_h)

        left_box.addWidget(p_frame, stretch=6)

        # Lower Cert Strip
        cert_bar = QtWidgets.QFrame()
        cert_bar.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #101624, stop:1 #070b13);
            border: 1px solid #1a273d;
            border-top: 1px solid #283a5a;
            border-radius: 6px;
        """)
        cb_lay = QtWidgets.QHBoxLayout(cert_bar)
        cb_lay.setContentsMargins(8, 6, 8, 6)
        cb_lay.setSpacing(6)
        cb_lay.addWidget(self.create_cert("SHEAR THRESHOLD", "≤ 3,600 RPM", "#ff3366"))
        cb_lay.addWidget(self.create_cert("CAVITATION FLOOR", "≥ 500 RPM", "#f59e0b"))
        cb_lay.addWidget(self.create_cert("HAMMER WAVE", "≤ 16.00 Bar", "#00f0ff"))
        cb_lay.addWidget(self.create_cert("GATE LATENCY", "< 1.0 µs Wire Gate", "#00ff88"))
        left_box.addWidget(cert_bar, stretch=1)

        main_h.addLayout(left_box, stretch=5)

        # RIGHT: Forensic PCAP Wire Bay
        pcap_frame = QtWidgets.QFrame()
        pcap_frame.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0d1422, stop:1 #060912);
            border: 1px solid #1a273e;
            border-top: 1px solid #2e446d;
            border-bottom: 2px solid #020509;
            border-radius: 8px;
        """)
        pc_lay = QtWidgets.QVBoxLayout(pcap_frame)
        pc_lay.setContentsMargins(10, 8, 10, 8)
        pc_lay.setSpacing(6)

        pc_head = QtWidgets.QHBoxLayout()
        pc_t = QtWidgets.QLabel("● FORENSIC INGRESS PCAP WIRE JOURNAL (PROMISCUOUS DPDK RING)")
        pc_t.setStyleSheet("color: #ffffff; font-size: 10px; font-weight: 900;")
        self.lbl_ring = QtWidgets.QLabel("RING BUFFER: 0 / 65,536 [STANDBY]")
        self.lbl_ring.setStyleSheet("color: #64748b; font-size: 9px; font-weight: bold; background: #08111e; border: 1px solid #1e293b; padding: 2px 6px; border-radius: 4px;")
        pc_head.addWidget(pc_t)
        pc_head.addStretch()
        pc_head.addWidget(self.lbl_ring)
        pc_lay.addLayout(pc_head)

        # Table starts with 0 rows
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
                background-color: #03060c;
                color: #e2e8f0;
                border: 1px solid #141e30;
                border-radius: 4px;
                font-family: 'Consolas', 'Segoe UI';
                font-size: 10px;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #141e30, stop:1 #0c121e);
                color: #94a3b8;
                font-weight: 800;
                font-size: 8.5px;
                border: none;
                border-bottom: 1px solid #1e293b;
                padding: 6px 4px;
            }
        """)
        pc_lay.addWidget(self.table)
        main_h.addWidget(pcap_frame, stretch=6)
        root.addLayout(main_h, stretch=7)

        # ---------------- 4. ATTACK TEST DECK ----------------
        bottom_box = QtWidgets.QFrame()
        bottom_box.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #121927, stop:1 #070a12);
            border: 1px solid #1f2c42;
            border-top: 1px solid #364c72;
            border-bottom: 2px solid #020408;
            border-radius: 8px;
        """)
        b_lay = QtWidgets.QVBoxLayout(bottom_box)
        b_lay.setContentsMargins(10, 8, 10, 8)
        b_lay.setSpacing(6)

        b_head = QtWidgets.QHBoxLayout()
        b_title = QtWidgets.QLabel("⚡ TACTICAL ATTACK VECTOR INJECTOR & HARDWARE ISOLATION TEST HARNESS")
        b_title.setStyleSheet("color: #ffffff; font-size: 10px; font-weight: 900; letter-spacing: 0.5px;")
        self.lbl_mode = QtWidgets.QLabel("CURRENT MODE: STANDBY // WAITING FOR PACKET INGESTION")
        self.lbl_mode.setStyleSheet("color: #38bdf8; font-size: 9px; font-weight: bold;")
        b_head.addWidget(b_title)
        b_head.addStretch()
        b_head.addWidget(self.lbl_mode)
        b_lay.addLayout(b_head)

        inj_row = QtWidgets.QHBoxLayout()
        inj_row.setSpacing(8)

        self.btn_stream = QtWidgets.QPushButton("▶ START CONTINUOUS 24x7 STREAM")
        self.btn_stream.setFixedHeight(36)
        self.btn_stream.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_stream.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ef4444, stop:1 #b91c1c);
                border: 1px solid #f87171;
                border-top: 1px solid #fca5a5;
                border-bottom: 3px solid #450a0a;
                border-radius: 6px;
                color: #ffffff;
                font-size: 9.5px;
                font-weight: 900;
                letter-spacing: 0.5px;
            }
            QPushButton:hover { background: #dc2626; }
        """)
        self.btn_stream.clicked.connect(self.toggle_stream)
        inj_row.addWidget(self.btn_stream, stretch=3)

        b1 = self.create_btn("⚡ STUXNET (50k)", "#ef4444", "#7f1d1d", lambda: self.inject(0x0103, 50000))
        b2 = self.create_btn("⚠️ CAVITATION (300)", "#f59e0b", "#78350f", lambda: self.inject(0x0104, 300))
        b3 = self.create_btn("🌊 WATER HAMMER", "#00f0ff", "#0369a1", lambda: self.inject(0x0102, 4600))
        b4 = self.create_btn("🟢 NOMINAL (1,800)", "#00ff88", "#065f46", lambda: self.inject(0x0101, 1800))
        inj_row.addWidget(b1, stretch=2)
        inj_row.addWidget(b2, stretch=2)
        inj_row.addWidget(b3, stretch=2)
        inj_row.addWidget(b4, stretch=2)
        b_lay.addLayout(inj_row)

        btn_cut = QtWidgets.QPushButton("⚠️ ASSERT EMERGENCY AIR-GAP ISOLATION CUT [PHYSICAL 24V GALVANIC TRIP] ⚠️")
        btn_cut.setFixedHeight(34)
        btn_cut.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        btn_cut.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #991b1b, stop:1 #450a0a);
                border: 1px solid #ef4444;
                border-top: 1px solid #f87171;
                border-bottom: 3px solid #1a0505;
                border-radius: 6px;
                color: #ffffff;
                font-size: 10px;
                font-weight: 900;
                letter-spacing: 0.8px;
            }
            QPushButton:hover { background: #b91c1c; }
        """)
        btn_cut.clicked.connect(self.trigger_cut)
        b_lay.addWidget(btn_cut)

        root.addWidget(bottom_box, stretch=2)

    # ---------------- BUILDER FACTORIES ----------------
    def create_card(self, title, val, unit, sub, col):
        f = QtWidgets.QFrame()
        f.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0f1624, stop:1 #060912);
                border: 1px solid {col}44;
                border-top: 1px solid {col}aa;
                border-bottom: 2px solid #020408;
                border-radius: 8px;
            }}
        """)
        l = QtWidgets.QVBoxLayout(f)
        l.setContentsMargins(10, 8, 10, 8)
        l.setSpacing(2)
        t = QtWidgets.QLabel(title)
        t.setStyleSheet("color: #94a3b8; font-size: 8px; font-weight: 800; letter-spacing: 0.5px;")
        vh = QtWidgets.QHBoxLayout()
        v = QtWidgets.QLabel(val)
        v.setStyleSheet(f"color: {col}; font-size: 20px; font-weight: 900;")
        u = QtWidgets.QLabel(unit)
        u.setStyleSheet(f"color: {col}bb; font-size: 9px; font-weight: bold; margin-top: 5px;")
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
        f.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {col}66;
                border-top: 1px solid {col}aa;
                border-bottom: 2px solid #020509;
                border-radius: 5px;
            }}
        """)
        h = QtWidgets.QHBoxLayout(f)
        h.setContentsMargins(7, 3, 7, 3)
        a = QtWidgets.QLabel(l1)
        a.setStyleSheet(f"color: {col}; font-size: 7.5px; font-weight: 900;")
        b = QtWidgets.QLabel(l2)
        b.setStyleSheet("color: #f8fafc; font-size: 7.5px; font-weight: bold;")
        h.addWidget(a)
        h.addWidget(b)
        return f

    def create_mini_stat(self, t, v, col):
        f = QtWidgets.QFrame()
        f.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #121a28, stop:1 #080c14);
                border: 1px solid #1a263c;
                border-top: 1px solid #283a5b;
                border-radius: 4px;
            }
        """)
        l = QtWidgets.QVBoxLayout(f)
        l.setContentsMargins(6, 4, 6, 4)
        lbl_t = QtWidgets.QLabel(t)
        lbl_t.setStyleSheet("color: #64748b; font-size: 7.5px; font-weight: bold;")
        lbl_v = QtWidgets.QLabel(v)
        lbl_v.setStyleSheet(f"color: {col}; font-size: 9.5px; font-weight: 900;")
        l.addWidget(lbl_t)
        l.addWidget(lbl_v)
        return f

    def create_cert(self, t, v, col):
        f = QtWidgets.QFrame()
        l = QtWidgets.QVBoxLayout(f)
        l.setContentsMargins(4, 2, 4, 2)
        t_l = QtWidgets.QLabel(t)
        t_l.setStyleSheet("color: #64748b; font-size: 7.5px; font-weight: bold;")
        v_l = QtWidgets.QLabel(v)
        v_l.setStyleSheet(f"color: {col}; font-size: 11px; font-weight: 900;")
        l.addWidget(t_l)
        l.addWidget(v_l)
        return f

    def create_btn(self, title, col, bg_dark, callback):
        b = QtWidgets.QPushButton(title)
        b.setFixedHeight(34)
        b.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        b.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {col}33, stop:1 {bg_dark});
                border: 1px solid {col}88;
                border-top: 1px solid {col};
                border-bottom: 3px solid #03060a;
                border-radius: 6px;
                color: #ffffff;
                font-size: 9px;
                font-weight: 900;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {col}66, stop:1 {bg_dark});
            }}
            QPushButton:pressed {{
                border-bottom: 1px solid #03060a;
                margin-top: 2px;
            }}
        """)
        b.clicked.connect(callback)
        return b

    # ---------------- NETWORK / UDP RECEIVER ----------------
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
            self.btn_stream.setText("⏸ STOP CONTINUOUS STREAM")
            self.btn_stream.setStyleSheet("background: #b91c1c; border: 1px solid #ef4444; border-radius: 6px; color: #fff; font-size: 9.5px; font-weight: 900;")
            self.lbl_mode.setText("CURRENT MODE: 24x7 REAL-TIME STREAM ACTIVE")
            self.lbl_mode.setStyleSheet("color: #00f0ff; font-size: 9px; font-weight: bold;")
            self.sc_tag.setText("ACTIVE : REAL-TIME MONITORING")
            self.sc_tag.setStyleSheet("color: #00f0ff; font-size: 8px; font-weight: bold; background: #082438; border: 1px solid #0284c7; padding: 2px 5px; border-radius: 3px;")
            self.auto_timer.start(600)
        else:
            self.btn_stream.setText("▶ START CONTINUOUS 24x7 STREAM")
            self.btn_stream.setStyleSheet("background: #ef4444; border: 1px solid #f87171; border-radius: 6px; color: #fff; font-size: 9.5px; font-weight: 900;")
            self.lbl_mode.setText("CURRENT MODE: SYSTEM ARMED // ZERO-COPY DAEMON LISTENING")
            self.lbl_mode.setStyleSheet("color: #00ff88; font-size: 9px; font-weight: bold;")
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
        self.c_verd.v.setStyleSheet("color: #ff3366; font-size: 19px; font-weight: 900;")
        self.c_verd.s.setText("Optocoupler Shunted [24V]")
        self.add_row("14:02:00.000000", "0xFFFF", "10.240.18.99", "0x00 [EMERGENCY]", "0 RPM / 0.00 Bar", "[ AIR-GAP TRIPPED ]", "#ff3366")

    def poll_telemetry(self):
        while True:
            try:
                data, _ = self.sock.recvfrom(1024)
                if len(data) == 32:
                    ts_us, tx_id, cmd_rpm, shock, twin_rpm, fatigue, verdict, _ = struct.unpack("<IHHfHfB13s", data)
                    self.packet_count += 1
                    self.lbl_ring.setText(f"RING BUFFER: {self.packet_count:,} / 65,536 [ACTIVE]")
                    self.lbl_ring.setStyleSheet("color: #00f0ff; font-size: 9px; font-weight: bold; background: #042f40; border: 1px solid #00f0ff; padding: 2px 6px; border-radius: 4px;")

                    self.sc_tag.setText("ACTIVE : REAL-TIME MONITORING")
                    self.sc_tag.setStyleSheet("color: #00f0ff; font-size: 8px; font-weight: bold; background: #082438; border: 1px solid #0284c7; padding: 2px 5px; border-radius: 3px;")

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
                        v_col = "#00ff88"
                        self.c_verd.v.setText("ALLOW : NOMINAL")
                        self.c_verd.v.setStyleSheet("color: #00ff88; font-size: 19px; font-weight: 900;")
                        self.c_verd.s.setText("Kinetic Slew & Acoustic Barrier Met")
                    elif verdict == 1:
                        v_str = "[ DROP : ROTOR CEILING ]"
                        v_col = "#ff3366"
                        self.c_verd.v.setText("DROP : ROTOR CEILING")
                        self.c_verd.v.setStyleSheet("color: #ff3366; font-size: 19px; font-weight: 900;")
                        self.c_verd.s.setText("Rotor Overspeed Breach")
                    elif verdict == 4:
                        v_str = "[ DROP : CAVITATION ]"
                        v_col = "#f59e0b"
                        self.c_verd.v.setText("DROP : CAVITATION")
                        self.c_verd.v.setStyleSheet("color: #f59e0b; font-size: 19px; font-weight: 900;")
                        self.c_verd.s.setText("Impeller Vapor Collapse")
                    else:
                        v_str = "[ DROP : PIPE SURGE ]"
                        v_col = "#ff3366"
                        self.c_verd.v.setText("DROP : PIPE SURGE")
                        self.c_verd.v.setStyleSheet("color: #ff3366; font-size: 19px; font-weight: 900;")
                        self.c_verd.s.setText("Acoustic Shockwave Limit Exceeded")

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

                    # Update plot ONLY when actual packet is received
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
                it.setForeground(QtGui.QColor("#00f0ff"))
                it.setFont(QtGui.QFont("Consolas", 9, QtGui.QFont.Weight.Bold))
            else:
                it.setForeground(QtGui.QColor("#cbd5e1"))
            self.table.setItem(row, col, it)
        self.table.scrollToBottom()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = VoltGuardZeroStateConsole()
    window.show()
    sys.exit(app.exec())