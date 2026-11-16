import sys
import socket
import struct
from collections import deque
from PyQt6 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

# High-Clarity Industrial Visualization Theme
pg.setConfigOption('background', '#0b0f19')
pg.setConfigOption('foreground', '#94a3b8')
pg.setConfigOptions(antialias=True)

class VoltGuardWorkstation(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoltGuard // Multi-Page OT Physics Firewall & Digital Twin Workstation")
        self.resize(1720, 980)
        self.setMinimumSize(1400, 860)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #070a12;
                color: #f8fafc;
                font-family: 'Segoe UI', 'Consolas', sans-serif;
            }
            QTableWidget {
                gridline-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #0b0f19;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: #1e293b;
                min-height: 20px;
                border-radius: 4px;
            }
        """)

        # Clean Ring Buffers
        self.history_len = 80
        self.time_buffer = deque(maxlen=self.history_len)
        self.cmd_buffer  = deque(maxlen=self.history_len)
        self.twin_buffer = deque(maxlen=self.history_len)
        self.shock_buffer = deque(maxlen=self.history_len)
        self.current_t   = 0.0
        self.packet_count = 0

        self.init_ui()
        self.init_udp_socket()

    def init_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root_layout = QtWidgets.QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ---------------- 1. TACTICAL SIDEBAR ----------------
        sidebar = QtWidgets.QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("background-color: #0c101b; border-right: 1px solid #1a2234;")
        sb_layout = QtWidgets.QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(14, 18, 14, 18)
        sb_layout.setSpacing(10)

        lbl_brand = QtWidgets.QLabel("VOLTGUARD")
        lbl_brand.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 900; letter-spacing: 2px;")
        lbl_role = QtWidgets.QLabel("// OT PHYSICS FIREWALL")
        lbl_role.setStyleSheet("color: #ef4444; font-size: 10px; font-weight: 800; letter-spacing: 1px;")
        sb_layout.addWidget(lbl_brand)
        sb_layout.addWidget(lbl_role)

        sb_layout.addSpacing(15)

        self.nav_buttons = []
        self.nav_buttons.append(self.create_nav_btn("01. MAIN COMMAND HUB", "Physical Health & Topology", 0))
        self.nav_buttons.append(self.create_nav_btn("02. KINEMATIC SCOPE", "Live Wave & Joukowsky Scope", 1))
        self.nav_buttons.append(self.create_nav_btn("03. FORENSIC PCAP", "Zero-Copy Wire Journal & Lab", 2))

        for btn in self.nav_buttons:
            sb_layout.addWidget(btn)

        sb_layout.addStretch()

        # Enclave Status Tag
        enc_box = QtWidgets.QFrame()
        enc_box.setStyleSheet("background-color: #080c14; border: 1px solid #1e2638; border-radius: 6px; padding: 8px;")
        enc_l = QtWidgets.QVBoxLayout(enc_box)
        enc_t = QtWidgets.QLabel("ENCLAVE BOUNDARY")
        enc_t.setStyleSheet("color: #64748b; font-size: 9px; font-weight: bold;")
        enc_s = QtWidgets.QLabel("● AIR-GAP LOCKED [24V]")
        enc_s.setStyleSheet("color: #22c55e; font-size: 10px; font-weight: 900;")
        enc_l.addWidget(enc_t)
        enc_l.addWidget(enc_s)
        sb_layout.addWidget(enc_box)

        root_layout.addWidget(sidebar)

        # ---------------- 2. MAIN VIEWPORT ----------------
        viewport = QtWidgets.QWidget()
        vp_layout = QtWidgets.QVBoxLayout(viewport)
        vp_layout.setContentsMargins(18, 14, 18, 14)
        vp_layout.setSpacing(12)

        # Top Bar
        top_bar = QtWidgets.QFrame()
        top_bar.setStyleSheet("background-color: #0f1422; border: 1px solid #1e2638; border-radius: 6px;")
        top_l = QtWidgets.QHBoxLayout(top_bar)
        top_l.setContentsMargins(16, 10, 16, 10)

        lbl_st = QtWidgets.QLabel("STATION: KINETIC-ENCLAVE-09   |   NODE: 10.240.18.4   |   KERNEL INTERFACE: AF_XDP (eth0 <-> eth1)")
        lbl_st.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        top_l.addWidget(lbl_st)
        top_l.addStretch()

        top_l.addWidget(self.create_badge("DUAL-NIC:", "IN-LINE ACTIVE", "#38bdf8", "#082f49"))
        top_l.addWidget(self.create_badge("PTP SYNC:", "0.428 µs PTP", "#4ade80", "#052e16"))
        top_l.addWidget(self.create_badge("OPTOCOUPLER:", "LATCHED [24V]", "#f59e0b", "#451a03"))
        top_l.addWidget(self.create_badge("ENCLAVE:", "AIR-GAP LOCKED", "#ef4444", "#450a0a"))

        vp_layout.addWidget(top_bar)

        # Stacked Pages
        self.stack = QtWidgets.QStackedWidget()
        self.stack.addWidget(self.build_page_hub())
        self.stack.addWidget(self.build_page_scope())
        self.stack.addWidget(self.build_page_pcap())

        vp_layout.addWidget(self.stack)
        root_layout.addWidget(viewport)

        self.switch_tab(0)

    # ---------------- PAGE BUILDERS ----------------
    def build_page_hub(self):
        page = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        # 4 Metric Cards (Clean, Bold, Large Numbers)
        m_lay = QtWidgets.QHBoxLayout()
        m_lay.setSpacing(12)
        self.hub_cmd   = self.create_metric_card("COMMANDED SETPOINT", "--", "RPM", "Ingress Telemetry", "#ffffff")
        self.hub_twin  = self.create_metric_card("RK4 TWIN ESTIMATE", "--", "RPM", "Differential ODE Match", "#38bdf8")
        self.hub_shock = self.create_metric_card("JOUKOWSKY SURGE (ΔP)", "--", "BAR", "Baseline Head: 7.75 Bar", "#ffffff")
        self.hub_verd  = self.create_metric_card("PHYSICAL IPS VERDICT", "ARMED", "", "Zero-Copy Wire Ingress Active", "#38bdf8")
        m_lay.addWidget(self.hub_cmd)
        m_lay.addWidget(self.hub_twin)
        m_lay.addWidget(self.hub_shock)
        m_lay.addWidget(self.hub_verd)
        lay.addLayout(m_lay)

        # Middle Intercept Topology & Interlocks
        mid_lay = QtWidgets.QHBoxLayout()
        mid_lay.setSpacing(12)

        topol_card = QtWidgets.QFrame()
        topol_card.setStyleSheet("background-color: #0f1422; border: 1px solid #1e2638; border-radius: 6px; padding: 14px;")
        t_lay = QtWidgets.QVBoxLayout(topol_card)
        t_title = QtWidgets.QLabel("CYBER-PHYSICAL INTERCEPT TOPOLOGY [BUMP-IN-THE-WIRE]")
        t_title.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 900; margin-bottom: 8px;")
        t_lay.addWidget(t_title)

        steps = [
            ("01. INGRESS (TCP:5502)", "Modbus MBAP FC06 Write Reg wire ingestion"),
            ("02. TAP RING (AF_XDP)", "Zero-copy in-line shunt buffer eth0 <-> eth1 (< 0.84 µs)"),
            ("03. INVARIANT CORE", "Joukowsky shock + RK4 digital twin + Basquin fatigue model"),
            ("04. 24V SHUNT ISOLATION", "Galvanic disconnect opto-tripped in sub-microsecond"),
            ("05. 480V VFD MOTOR", "Centrifugal slurry impeller and high-pressure steam duct")
        ]
        for name, desc in steps:
            r = QtWidgets.QHBoxLayout()
            lbl_n = QtWidgets.QLabel(name)
            lbl_n.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: bold; width: 150px;")
            lbl_d = QtWidgets.QLabel(desc)
            lbl_d.setStyleSheet("color: #94a3b8; font-size: 10px;")
            r.addWidget(lbl_n)
            r.addWidget(lbl_d)
            t_lay.addLayout(r)

        mid_lay.addWidget(topol_card, stretch=6)

        emerg_card = QtWidgets.QFrame()
        emerg_card.setStyleSheet("background-color: #0f1422; border: 1px solid #1e2638; border-radius: 6px; padding: 14px;")
        em_lay = QtWidgets.QVBoxLayout(emerg_card)
        em_title = QtWidgets.QLabel("TACTICAL HARDWARE INTERLOCKS")
        em_title.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 900;")
        em_lay.addWidget(em_title)

        em_lay.addWidget(self.create_toggle_row("Synchronous In-line Rejection", "Hold packets until physics evaluates", True))
        em_lay.addWidget(self.create_toggle_row("24V Optocoupler Shunt Trip", "Disconnect control circuit on shock", True))
        em_lay.addWidget(self.create_toggle_row("2-Man Authorization Rule", "Require dual keys for parameter bypass", False))

        em_lay.addStretch()

        btn_cut = QtWidgets.QPushButton("ASSERT EMERGENCY AIR-GAP ISOLATION CUT")
        btn_cut.setFixedHeight(44)
        btn_cut.setStyleSheet("""
            QPushButton {
                background-color: #7f1d1d;
                border: 2px solid #ef4444;
                border-radius: 6px;
                color: #ffffff;
                font-size: 11px;
                font-weight: 900;
                letter-spacing: 1px;
            }
            QPushButton:hover { background-color: #991b1b; }
        """)
        btn_cut.clicked.connect(self.trigger_emergency_cut)
        em_lay.addWidget(btn_cut)

        mid_lay.addWidget(emerg_card, stretch=4)
        lay.addLayout(mid_lay, stretch=6)

        # Bottom Invariant Bounds
        inv_frame = QtWidgets.QFrame()
        inv_frame.setStyleSheet("background-color: #0f1422; border: 1px solid #1e2638; border-radius: 6px; padding: 10px;")
        inv_lay = QtWidgets.QHBoxLayout(inv_frame)
        inv_lay.addWidget(self.create_cert_box("PIPE RUPTURE LIMIT", "≤ 16.00 Bar", "Acoustic Joukowsky Ceiling"))
        inv_lay.addWidget(self.create_cert_box("CAVITATION FLOOR", "≥ 500 RPM", "Vacuum Implosion Protection"))
        inv_lay.addWidget(self.create_cert_box("MAX ROTOR SLEW", "≤ 140 RPM/s", "Inertial Slew Ceiling"))
        inv_lay.addWidget(self.create_cert_box("DETERMINISTIC LATENCY", "< 1.0 µs Wire Gate", "Zero-Buffer Hold"))
        lay.addWidget(inv_frame, stretch=2)

        return page

    def build_page_scope(self):
        page = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        # Main Kinematic Scope
        p_frame = QtWidgets.QFrame()
        p_frame.setStyleSheet("background-color: #0b0f19; border: 1px solid #1e2638; border-radius: 6px; padding: 12px;")
        p_lay = QtWidgets.QVBoxLayout(p_frame)

        head = QtWidgets.QHBoxLayout()
        t1 = QtWidgets.QLabel("PRIMARY DUAL-TRACE KINEMATIC WAVEFORM MONITOR")
        t1.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 900; letter-spacing: 1px;")
        t2 = QtWidgets.QLabel("SHAFT VELOCITY (RPM) VS RK4 DIGITAL TWIN")
        t2.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        head.addWidget(t1)
        head.addSpacing(12)
        head.addWidget(t2)
        head.addStretch()

        lbl_c = QtWidgets.QLabel("— Commanded Ingress (Wire)")
        lbl_c.setStyleSheet("color: #ffffff; font-size: 10px; font-weight: bold;")
        lbl_t = QtWidgets.QLabel("- - RK4 Digital Twin")
        lbl_t.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: bold;")
        head.addWidget(lbl_c)
        head.addSpacing(10)
        head.addWidget(lbl_t)
        p_lay.addLayout(head)

        self.scope_plot = pg.PlotWidget()
        # Clean Grid with minimal clutter
        self.scope_plot.showGrid(x=True, y=True, alpha=0.10)
        self.scope_plot.setLabel('left', 'Shaft Velocity (RPM)', color='#94a3b8', size='10pt')
        self.scope_plot.setLabel('bottom', 'Relative Telemetry Time (Seconds)', color='#94a3b8', size='10pt')
        self.scope_plot.setYRange(0, 55000)

        # Tripwire Threshold Lines
        self.scope_plot.addItem(pg.InfiniteLine(pos=3600, angle=0, pen=pg.mkPen(color='#ef4444', width=2, style=QtCore.Qt.PenStyle.DashLine)))
        self.scope_plot.addItem(pg.InfiniteLine(pos=500, angle=0, pen=pg.mkPen(color='#eab308', width=1.5, style=QtCore.Qt.PenStyle.DotLine)))

        # Clean, Non-Clipping Threshold Tags
        txt_ceil = pg.TextItem("ROTOR SHEAR CEILING: 3,600 RPM", color='#ef4444', anchor=(1, 1))
        txt_ceil.setPos(5.0, 5400)
        txt_floor = pg.TextItem("CAVITATION FLOOR: 500 RPM", color='#eab308', anchor=(1, 0))
        txt_floor.setPos(5.0, 100)
        self.scope_plot.addItem(txt_ceil)
        self.scope_plot.addItem(txt_floor)

        self.curve_cmd = self.scope_plot.plot(pen=pg.mkPen(color='#ffffff', width=2.5), symbol='o', symbolSize=7, symbolBrush='#ef4444')
        self.curve_twin = self.scope_plot.plot(pen=pg.mkPen(color='#38bdf8', width=2.0, style=QtCore.Qt.PenStyle.DashLine))

        p_lay.addWidget(self.scope_plot)
        lay.addWidget(p_frame, stretch=7)

        # Secondary Joukowsky Transient Shock Sub-Scope
        sh_frame = QtWidgets.QFrame()
        sh_frame.setStyleSheet("background-color: #0b0f19; border: 1px solid #1e2638; border-radius: 6px; padding: 10px;")
        sh_lay = QtWidgets.QVBoxLayout(sh_frame)

        sh_head = QtWidgets.QHBoxLayout()
        sh_title = QtWidgets.QLabel("JOUKOWSKY TRANSIENT SHOCK SUB-SCOPE (ΔP IN BAR)")
        sh_title.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: 900;")
        sh_sub = QtWidgets.QLabel("EQUATION: ΔP = ρ · a · |Δv|   |   RUPTURE CEILING: 16.00 BAR")
        sh_sub.setStyleSheet("color: #ef4444; font-size: 10px; font-weight: bold;")
        sh_head.addWidget(sh_title)
        sh_head.addStretch()
        sh_head.addWidget(sh_sub)
        sh_lay.addLayout(sh_head)

        self.shock_plot = pg.PlotWidget()
        self.shock_plot.showGrid(x=True, y=True, alpha=0.10)
        self.shock_plot.setYRange(0, 60)
        self.shock_plot.addItem(pg.InfiniteLine(pos=16.0, angle=0, pen=pg.mkPen(color='#ef4444', width=2, style=QtCore.Qt.PenStyle.DashLine)))
        self.curve_shock = self.shock_plot.plot(pen=pg.mkPen(color='#ef4444', width=2.0), symbol='s', symbolSize=6, symbolBrush='#ffffff')
        sh_lay.addWidget(self.shock_plot)

        lay.addWidget(sh_frame, stretch=3)
        return page

    def build_page_pcap(self):
        page = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        # Left: Live Forensic PCAP Table
        left_tbl = QtWidgets.QFrame()
        left_tbl.setStyleSheet("background-color: #0f1422; border: 1px solid #1e2638; border-radius: 6px; padding: 12px;")
        t_lay = QtWidgets.QVBoxLayout(left_tbl)

        th = QtWidgets.QHBoxLayout()
        t_title = QtWidgets.QLabel("FORENSIC INGRESS PCAP JOURNAL [ZERO-COPY BUFFER]")
        t_title.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 900;")
        self.lbl_ring_count = QtWidgets.QLabel("RING BUFFER: 0 / 65,536 [ARMED]")
        self.lbl_ring_count.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        th.addWidget(t_title)
        th.addStretch()
        th.addWidget(self.lbl_ring_count)
        t_lay.addLayout(th)

        self.table = QtWidgets.QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["TIMESTAMP (PTP)", "TX ID", "SRC IP", "FUNCTION / REG", "COMMANDED / SHOCK", "IPS VERDICT"])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0b0f19;
                color: #e2e8f0;
                border: 1px solid #1e2638;
                border-radius: 4px;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #0f1422;
                color: #94a3b8;
                font-weight: 800;
                font-size: 10px;
                border: none;
                padding: 8px;
            }
        """)
        t_lay.addWidget(self.table)
        lay.addWidget(left_tbl, stretch=7)

        # Right: Attack Vector Injector
        right_inj = QtWidgets.QFrame()
        right_inj.setStyleSheet("background-color: #0f1422; border: 1px solid #1e2638; border-radius: 6px; padding: 14px;")
        inj_lay = QtWidgets.QVBoxLayout(right_inj)
        inj_lay.setSpacing(10)

        inj_title = QtWidgets.QLabel("ATTACK VECTOR INJECTOR (TEST HARNESS)")
        inj_title.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 900; letter-spacing: 0.5px;")
        inj_sub = QtWidgets.QLabel("DETERMINISTIC INGRESS SIMULATION VIA TCP:5502")
        inj_sub.setStyleSheet("color: #64748b; font-size: 9px; font-weight: bold; margin-bottom: 8px;")
        inj_lay.addWidget(inj_title)
        inj_lay.addWidget(inj_sub)

        btn1 = self.create_attack_btn("STUXNET-CLASS OVERSPEED", "50,000 RPM (Breaches 3,600 Shear Limit)", "#ef4444")
        btn2 = self.create_attack_btn("CAVITATION COLLAPSE TEST", "300 RPM (Drops under Vapor Floor)", "#f59e0b")
        btn3 = self.create_attack_btn("WATER HAMMER SURGE ATTACK", "+2,800 RPM in < 10ms (ΔP > 16 Bar)", "#ef4444")
        btn4 = self.create_attack_btn("NOMINAL BASELINE STEADY-STATE", "1,800 RPM (Physics Invariant Compliant)", "#22c55e")

        btn1.clicked.connect(lambda: self.inject_modbus(0x0103, 50000))
        btn2.clicked.connect(lambda: self.inject_modbus(0x0104, 300))
        btn3.clicked.connect(lambda: self.inject_modbus(0x0102, 4600))
        btn4.clicked.connect(lambda: self.inject_modbus(0x0101, 1800))

        inj_lay.addWidget(btn1)
        inj_lay.addWidget(btn2)
        inj_lay.addWidget(btn3)
        inj_lay.addWidget(btn4)

        inj_lay.addStretch()

        status_box = QtWidgets.QFrame()
        status_box.setStyleSheet("background-color: #0b0f19; border: 1px solid #1e2638; border-radius: 4px; padding: 8px;")
        sb_l = QtWidgets.QVBoxLayout(status_box)
        lbl_s_info = QtWidgets.QLabel("STAGE MBAP WIRE PACKET:")
        lbl_s_info.setStyleSheet("color: #64748b; font-size: 9px; font-weight: bold;")
        lbl_s_raw = QtWidgets.QLabel("TARGET: 10.240.18.4:5502 (Modbus-TCP)\nPAYLOAD: FC:06 WRITE_REG [0x0001]")
        lbl_s_raw.setStyleSheet("color: #38bdf8; font-size: 10px;")
        sb_l.addWidget(lbl_s_info)
        sb_l.addWidget(lbl_s_raw)
        inj_lay.addWidget(status_box)

        lay.addWidget(right_inj, stretch=3)
        return page

    # ------------------ COMPONENT HELPERS ------------------
    def create_nav_btn(self, title, subtitle, page_index):
        btn = QtWidgets.QPushButton()
        btn.setFixedHeight(54)
        btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        l = QtWidgets.QVBoxLayout(btn)
        l.setContentsMargins(14, 8, 14, 8)
        l.setSpacing(2)

        t = QtWidgets.QLabel(title)
        t.setStyleSheet("font-size: 11px; font-weight: 900; letter-spacing: 0.5px;")
        s = QtWidgets.QLabel(subtitle)
        s.setStyleSheet("font-size: 9px;")
        l.addWidget(t)
        l.addWidget(s)

        btn.t_lbl = t
        btn.s_lbl = s
        btn.page_index = page_index
        btn.clicked.connect(lambda: self.switch_tab(page_index))
        return btn

    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)
        for b in self.nav_buttons:
            if b.page_index == index:
                b.setStyleSheet("""
                    QPushButton {
                        background-color: #dc2626;
                        border: 1px solid #ef4444;
                        border-radius: 6px;
                        text-align: left;
                    }
                """)
                b.t_lbl.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: 900;")
                b.s_lbl.setStyleSheet("color: #fee2e2; font-size: 9px;")
            else:
                b.setStyleSheet("""
                    QPushButton {
                        background-color: #0f1422;
                        border: 1px solid #1e2638;
                        border-radius: 6px;
                        text-align: left;
                    }
                    QPushButton:hover {
                        background-color: #161e31;
                        border: 1px solid #334155;
                    }
                """)
                b.t_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 800;")
                b.s_lbl.setStyleSheet("color: #64748b; font-size: 9px;")

    def create_metric_card(self, title, val, unit, subtext, color):
        frame = QtWidgets.QFrame()
        frame.setStyleSheet("background-color: #0f1422; border: 1px solid #1e2638; border-radius: 6px; padding: 12px;")
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setSpacing(4)

        lbl_t = QtWidgets.QLabel(title)
        lbl_t.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 800; letter-spacing: 0.8px;")
        
        v_box = QtWidgets.QHBoxLayout()
        lbl_v = QtWidgets.QLabel(val)
        lbl_v.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: 900;")
        lbl_u = QtWidgets.QLabel(unit)
        lbl_u.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold; margin-top: 6px;")
        v_box.addWidget(lbl_v)
        v_box.addWidget(lbl_u)
        v_box.addStretch()

        lbl_s = QtWidgets.QLabel(subtext)
        lbl_s.setStyleSheet("color: #64748b; font-size: 9px; font-weight: bold;")
        layout.addWidget(lbl_t)
        layout.addLayout(v_box)
        layout.addWidget(lbl_s)
        frame.lbl_v = lbl_v
        frame.lbl_s = lbl_s
        return frame

    def create_cert_box(self, label, val, sub):
        box = QtWidgets.QFrame()
        box.setStyleSheet("background-color: #0b0f19; border: 1px solid #1e2638; border-radius: 4px; padding: 6px;")
        l = QtWidgets.QVBoxLayout(box)
        l.setContentsMargins(8, 6, 8, 6)
        lbl_k = QtWidgets.QLabel(label)
        lbl_k.setStyleSheet("color: #94a3b8; font-size: 9px; font-weight: bold;")
        lbl_v = QtWidgets.QLabel(val)
        lbl_v.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 900;")
        lbl_s = QtWidgets.QLabel(sub)
        lbl_s.setStyleSheet("color: #64748b; font-size: 9px;")
        l.addWidget(lbl_k)
        l.addWidget(lbl_v)
        l.addWidget(lbl_s)
        return box

    def create_badge(self, label, val, text_color, bg_color):
        b = QtWidgets.QFrame()
        b.setStyleSheet(f"background-color: {bg_color}; border: 1px solid {text_color}44; border-radius: 4px;")
        l = QtWidgets.QHBoxLayout(b)
        l.setContentsMargins(8, 4, 8, 4)
        l1 = QtWidgets.QLabel(label)
        l1.setStyleSheet(f"color: {text_color}; font-size: 9px; font-weight: 800;")
        l2 = QtWidgets.QLabel(val)
        l2.setStyleSheet("color: #f8fafc; font-size: 9px; font-weight: bold;")
        l.addWidget(l1)
        l.addWidget(l2)
        return b

    def create_attack_btn(self, title, subtitle, color):
        btn = QtWidgets.QPushButton()
        btn.setFixedHeight(46)
        btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #0b0f19;
                border: 1px solid {color}55;
                border-radius: 4px;
                text-align: left;
                padding-left: 12px;
            }}
            QPushButton:hover {{
                background-color: {color}15;
                border: 1px solid {color};
            }}
        """)
        l = QtWidgets.QVBoxLayout(btn)
        l.setContentsMargins(0, 4, 0, 4)
        t = QtWidgets.QLabel(title)
        t.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 900;")
        s = QtWidgets.QLabel(subtitle)
        s.setStyleSheet("color: #94a3b8; font-size: 9px;")
        l.addWidget(t)
        l.addWidget(s)
        return btn

    def create_toggle_row(self, title, desc, checked):
        w = QtWidgets.QWidget()
        l = QtWidgets.QHBoxLayout(w)
        l.setContentsMargins(0, 2, 0, 2)
        info = QtWidgets.QVBoxLayout()
        t = QtWidgets.QLabel(title)
        t.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: bold;")
        d = QtWidgets.QLabel(desc)
        d.setStyleSheet("color: #94a3b8; font-size: 9px;")
        info.addWidget(t)
        info.addWidget(d)
        l.addLayout(info)
        l.addStretch()
        chk = QtWidgets.QCheckBox()
        chk.setChecked(checked)
        l.addWidget(chk)
        return w

    def trigger_emergency_cut(self):
        self.hub_verd.lbl_v.setText("AIR-GAP CUT")
        self.hub_verd.lbl_v.setStyleSheet("color: #ef4444; font-size: 22px; font-weight: 900;")
        self.hub_verd.lbl_s.setText("Optocoupler Circuit Shunted [24V]")
        self.add_journal_row("00:00:00.000000", "0xFFFF", "10.240.18.109", "0x00 [EMERGENCY]", "0 RPM / 0.00 Bar", "[ AIR-GAP TRIPPED ]", "#ef4444")

    # ------------------ TELEMETRY STREAM & LOGIC ------------------
    def init_udp_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 5555))
        self.sock.setblocking(False)

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
        while True:
            try:
                data, _ = self.sock.recvfrom(1024)
                if len(data) == 32:
                    ts_us, tx_id, cmd_rpm, shock, twin_rpm, fatigue, verdict, _ = struct.unpack("<IHHfHfB13s", data)
                    self.packet_count += 1
                    self.lbl_ring_count.setText(f"RING BUFFER: {self.packet_count:,} / 65,536 [ACTIVE]")

                    self.current_t += 0.8
                    self.time_buffer.append(self.current_t)
                    self.cmd_buffer.append(cmd_rpm)
                    self.twin_buffer.append(twin_rpm)
                    self.shock_buffer.append(shock)

                    # Update Main Hub Annunciators
                    self.hub_cmd.lbl_v.setText(f"{cmd_rpm:,}")
                    self.hub_cmd.lbl_s.setText(f"Tx: 0x{tx_id:04X} // MBAP FC:06")
                    self.hub_shock.lbl_v.setText(f"{shock:.2f}")
                    self.hub_twin.lbl_v.setText(f"{twin_rpm:,}")

                    # Crisp Verdict Logic
                    if verdict == 0:
                        v_str = "[ ALLOW : INVARIANT MET ]"
                        v_color = "#4ade80"
                        self.hub_verd.lbl_v.setText("ALLOW")
                        self.hub_verd.lbl_v.setStyleSheet("color: #4ade80; font-size: 24px; font-weight: 900;")
                        self.hub_verd.lbl_s.setText("Physics Invariant Certified")
                    elif verdict == 1:
                        v_str = "[ DROPPED : SHEAR CEILING ]"
                        v_color = "#ef4444"
                        self.hub_verd.lbl_v.setText("DROP")
                        self.hub_verd.lbl_v.setStyleSheet("color: #ef4444; font-size: 24px; font-weight: 900;")
                        self.hub_verd.lbl_s.setText("Catastrophic Rotor Overspeed")
                    elif verdict == 4:
                        v_str = "[ DROPPED : CAVITATION FLOOR ]"
                        v_color = "#ef4444"
                        self.hub_verd.lbl_v.setText("DROP")
                        self.hub_verd.lbl_v.setStyleSheet("color: #ef4444; font-size: 24px; font-weight: 900;")
                        self.hub_verd.lbl_s.setText("Impeller Vapor Collapse")
                    else:
                        v_str = "[ DROPPED : SURGE RATE ]"
                        v_color = "#ef4444"
                        self.hub_verd.lbl_v.setText("DROP")
                        self.hub_verd.lbl_v.setStyleSheet("color: #ef4444; font-size: 24px; font-weight: 900;")
                        self.hub_verd.lbl_s.setText("Acoustic Shockwave Limit Exceeded")

                    # Add Row to Forensic Table
                    ptp_ts = f"14:02:{int(self.current_t):02d}.{ts_us % 1000000:06d}"
                    self.add_journal_row(
                        ptp_ts,
                        f"0x{tx_id:04X}", 
                        "10.240.18.109",
                        "0x06 [Reg 0x0001]",
                        f"{cmd_rpm:,} RPM / {shock:.2f} Bar", 
                        v_str, 
                        v_color
                    )

                    # Update Plots on Scope Page
                    self.curve_cmd.setData(list(self.time_buffer), list(self.cmd_buffer))
                    self.curve_twin.setData(list(self.time_buffer), list(self.twin_buffer))
                    self.curve_shock.setData(list(self.time_buffer), list(self.shock_buffer))

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
                item.setForeground(QtGui.QColor("#e2e8f0"))
            self.table.setItem(row, col, item)
        self.table.scrollToBottom()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = VoltGuardWorkstation()
    window.show()
    sys.exit(app.exec())