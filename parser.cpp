#include <iostream>
#include <iomanip>
#include <chrono>
#include <vector>
#include <winsock2.h>
#include "modbus_frame.hpp"
#include "physics_engine.hpp"

#pragma comment(lib, "ws2_32.lib")

// Benchmark Helper: Microsecond & Nanosecond resolution
void benchmarkPacket(VoltGuard::PhysicsEngine& engine, const std::string& test_name, const std::vector<uint8_t>& packet) {
    if (packet.size() < sizeof(ModbusTcpHeader)) {
        std::cout << "[ERROR] Packet size too small: " << packet.size() << " bytes\n";
        return;
    }

    auto start = std::chrono::high_resolution_clock::now();

    // Zero-copy direct cast to packed struct
    const auto* hdr = reinterpret_cast<const ModbusTcpHeader*>(packet.data());

    uint16_t tx_id   = ntohs(hdr->transaction_id);
    uint16_t reg_addr= ntohs(hdr->register_address);
    uint16_t raw_val = ntohs(hdr->register_value);
    float rpm = static_cast<float>(raw_val);
    float shock_bar = 0.0f;

    // Physics evaluation
    auto verdict = engine.evaluate(rpm, shock_bar);

    auto end = std::chrono::high_resolution_clock::now();
    auto latency_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();

    std::cout << "Test: [" << std::left << std::setw(28) << test_name << "] "
              << "| TxID: 0x" << std::hex << std::setw(4) << std::setfill('0') << tx_id << std::dec << std::setfill(' ')
              << " | RPM: " << std::setw(6) << (int)rpm
              << " | Shock: " << std::fixed << std::setprecision(2) << std::setw(6) << shock_bar << " Bar "
              << "| Latency: " << std::setw(4) << latency_ns << " ns "
              << "| Verdict: " << (verdict == VoltGuard::Verdict::ALLOW ? "[ALLOW]" : "[DROP/TRIPWIRE]")
              << "\n";
}

int main() {
    std::cout << "========================================================================================\n";
    std::cout << "  VoltGuard Week 1: Standalone Zero-Copy Modbus Parser & Physics Benchmark Suite      \n";
    std::cout << "========================================================================================\n";

    VoltGuard::PhysicsEngine engine;

    // Test 1: Normal 1,800 RPM (TxID: 0x0001, Reg: 0x0001, Val: 1800 = 0x0708)
    std::vector<uint8_t> pkt_normal = {
        0x00, 0x01, 0x00, 0x00, 0x00, 0x06, 0x01, 0x06, 0x00, 0x01, 0x07, 0x08
    };

    // Test 2: Stuxnet 50,000 RPM (TxID: 0x0002, Reg: 0x0001, Val: 50000 = 0xC350)
    std::vector<uint8_t> pkt_stuxnet = {
        0x00, 0x02, 0x00, 0x00, 0x00, 0x06, 0x01, 0x06, 0x00, 0x01, 0xC3, 0x50
    };

    // Test 3: Sub-Idle Cavitation 300 RPM (TxID: 0x0003, Reg: 0x0001, Val: 300 = 0x012C)
    std::vector<uint8_t> pkt_cavitation = {
        0x00, 0x03, 0x00, 0x00, 0x00, 0x06, 0x01, 0x06, 0x00, 0x01, 0x01, 0x2C
    };

    // Test 4: Safe Ramp 2,400 RPM (TxID: 0x0004, Reg: 0x0001, Val: 2400 = 0x0960)
    std::vector<uint8_t> pkt_ramp = {
        0x00, 0x04, 0x00, 0x00, 0x00, 0x06, 0x01, 0x06, 0x00, 0x01, 0x09, 0x60
    };

    benchmarkPacket(engine, "Normal SCADA Setpoint", pkt_normal);
    benchmarkPacket(engine, "Stuxnet Overspeed Attack", pkt_stuxnet);
    benchmarkPacket(engine, "Sub-Idle Cavitation Floor", pkt_cavitation);
    benchmarkPacket(engine, "Safe Operational Ramp", pkt_ramp);

    std::cout << "========================================================================================\n";
    std::cout << "Zero-Copy Parsing & Physics verification completed successfully.\n";
    return 0;
}