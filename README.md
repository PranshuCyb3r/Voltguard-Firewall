# Voltguard-Firewall: Physics-Aware ICS/SCADA Firewall & IPS

> **A deterministic, bump-in-the-wire industrial firewall that enforces the fundamental laws of physics on OT control traffic before physical machinery can be damaged.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Standard: IEC-62443](https://img.shields.io/badge/Compliance-IEC--62443--3--3-green.svg)]()
[![Pipeline Latency](https://img.shields.io/badge/SLA-%3C10ms%20Deterministic-brightgreen.svg)]()
[![OT Architecture](https://img.shields.io/badge/Deployment-Purdue%20Level%201%2F2-orange.svg)]()

---

## Project Overview

Standard IT and OT firewalls validate packet headers, checksums, and syntax. However, they are **blind to physical consequences**. If an attacker or compromised workstation issues a perfectly formatted Modbus frame instructing a booster pump to spin at 50,000 RPM or instantly snaps a penstock valve shut, conventional firewalls permit the packet—resulting in catastrophic mechanical damage, pipeline rupture, or plant failure.

**Voltguard-Firewall** operates as an inline, real-time **Physics Firewall** sitting between SCADA supervisory workstations and field PLCs. It deserializes incoming Modbus/TCP, DNP3, and CIP traffic, evaluates the commands against an onboard hydrodynamic/thermodynamic digital twin model, and deterministically drops malicious commands within a strict **sub-10ms latency budget**.

---

## Core Subsystems

* **`01_interceptor` (C++ / DPDK & Scapy):** Kernel-bypass network TAP ingestion for microsecond deserialization of Modbus/TCP (FC01, FC05, FC06, FC16) frames.

* **`02_physics_engine` (Python / SciPy / OpenModelica):** Differential algebraic equation (DAE) state estimator calculating fluid continuity, Bernoulli conservation, and Joukowsky acoustic surge limits ($\Delta P = \rho \cdot a \cdot \Delta v$).

* **`03_decision_engine` (Rust 1.77+):** Zero-allocation deterministic gatekeeper enforcing safety invariants (`RULE_01_SLEW` to `RULE_04_OVERSPEED`) in under 0.2ms.

* **`04_operator_workstation` (Native C++ / Qt6):** Air-gapped, zero-web-runtime desktop HMI for plant operators showing live P&ID mimic schematics and trajectory curves.

* **`hardware_edge`:** Bump-in-the-wire scripts with fail-safe passive relay bypass for industrial single-board computers (Raspberry Pi CM4 / Siemens IPC).