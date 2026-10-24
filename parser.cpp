#include <iostream>
#include <chrono>
#include <iomanip>
#include "modbus_frame.hpp"
#include "physics_engine.hpp"

void print_hex(const uint8_t* data, size_t len) {
    for (size_t i = 0; i < len; ++i) {
        std::cout << std::hex << std::uppercase << std::setw(2) << std::setfill('0') << (int)data[i] << " ";
    }
    std::cout << std::dec << "\n";
}

int main() {
    std::cout << "========================================================================\n";
    std::cout << " [VoltGuard] Mid-Project Review: Hexadecimal Wire & Physics Audit Benchmark\n";
    std::cout << "========================================================================\n";

    // Modbus Hex Frame for 50,000 RPM (0xC350) Attack:
    // TxID: 0x0002 | Proto: 0x0000 | Len: 0x0006 | Unit: 0x01 | FC: 0x06 | Reg: 0x0001 | Val: 0xC350
    uint8_t attack_wire[] = {
        0x00, 0x02, 0x00, 0x00, 0x00, 0x06, 0x01, 0x06, 0x00, 0x01, 0xC3, 0x50
    };

    std::cout << "[Mid-Review Audit 1] Raw Wire Hex Ingress:\n  -> ";
    print_hex(attack_wire, sizeof(attack_wire));

    auto t1 = std::chrono::high_resolution_clock::now();
    const auto* hdr = reinterpret_cast<const ModbusTcpHeader*>(attack_wire);

    uint16_t tx_id = (hdr->transaction_id >> 8) | (hdr->transaction_id << 8);
    uint16_t reg = (hdr->register_address >> 8) | (hdr->register_address << 8);
    uint16_t rpm = (hdr->register_value >> 8) | (hdr->register_value << 8);

    float shock = 0.0f;
    VoltGuard::Verdict verdict = VoltGuard::PhysicsEngine::evaluate(rpm, shock);
    auto t2 = std::chrono::high_resolution_clock::now();

    auto elapsed_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(t2 - t1).count();

    std::cout << "[Mid-Review Audit 1] Zero-Copy Ingress Breakdown:\n";
    std::cout << "  - Transaction ID : 0x" << std::hex << tx_id << std::dec << "\n";
    std::cout << "  - Function Code  : 0x06 (Preset Single Register)\n";
    std::cout << "  - Register       : 0x" << std::hex << reg << std::dec << " (Shaft Speed)\n";
    std::cout << "  - Injected RPM   : " << rpm << " RPM\n";
    std::cout << "  - Joukowsky Surge: " << shock << " Bar\n";
    std::cout << "  - Parsing Latency: " << elapsed_ns << " nanoseconds\n";
    std::cout << "  - Engine Verdict : " << (verdict == VoltGuard::Verdict::ALLOW ? "ALLOW" : "DROP [INTERCEPTED]") << "\n";
    std::cout << "------------------------------------------------------------------------\n";
    std::cout << "[Mid-Review Audit 2] Impossible Physics Test (300 RPM Cavitation Stall):\n";
    
    float stall_shock = 0.0f;
    VoltGuard::Verdict stall_v = VoltGuard::PhysicsEngine::evaluate(300, stall_shock);
    std::cout << "  - Injected 300 RPM (Below 500 RPM Floor): " 
              << (stall_v == VoltGuard::Verdict::DROP_INVALID_RANGE ? "TRAPPED & DROPPED (PASS)" : "FAILED") << "\n";
    std::cout << "========================================================================\n";

    return 0;
}
