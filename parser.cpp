#include <iostream>
#include <vector>
#include <chrono>
#include "modbus_frame.hpp"
#include "physics_engine.hpp"

int main() {
    std::cout << "========================================================\n";
    std::cout << "  VoltGuard: Physics-Aware Modbus/TCP Zero-Copy Engine  \n";
    std::cout << "========================================================\n\n";

    // Attack Scenario Packet: Modbus TCP Write Single Register (0x06) -> 50,000 RPM (0xC350)
    std::vector<uint8_t> attack_packet = {
        0x00, 0x01,             // Transaction ID: 1
        0x00, 0x00,             // Protocol ID: 0 (Modbus)
        0x00, 0x06,             // Length: 6 bytes following
        0x01,                   // Unit ID: 1 (PLC Controller)
        0x06,                   // Function Code: 0x06 (Write Single Register)
        0x00, 0x01,             // Register Address: 1 (Turbine RPM Reference)
        0xC3, 0x50              // Register Value: 50,000 RPM (Exceeds 3,600 RPM limit!)
    };

    VoltGuard::PhysicsEngine physics_verifier;
    VoltGuard::ParsedFrame parsed_frame;

    // Sub-microsecond Zero-Copy Inspection Benchmark
    auto start_time = std::chrono::high_resolution_clock::now();

    // 1. Zero-Copy Protocol Decode
    bool parse_ok = VoltGuard::ModbusParser::parse_frame(attack_packet.data(), attack_packet.size(), &parsed_frame);

    if (!parse_ok) {
        std::cerr << "[ERROR] Malformed Modbus Frame dropped.\n";
        return 1;
    }

    uint16_t requested_rpm = parsed_frame.register_value;
    uint64_t current_timestamp_ms = 1000; // Simulated timestamp (1 sec)

    // 2. Physics Verification Engine Check
    VoltGuard::Verdict verdict = physics_verifier.verify_rpm_command(requested_rpm, current_timestamp_ms);

    auto end_time = std::chrono::high_resolution_clock::now();
    auto elapsed_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end_time - start_time).count();

    // Display Decoded Telemetry
    std::cout << "[+] Protocol Inspection (Zero-Copy MBAP + PDU):\n";
    std::cout << "    - Transaction ID : " << parsed_frame.transaction_id << "\n";
    std::cout << "    - Protocol ID    : " << parsed_frame.protocol_id << " (Modbus TCP)\n";
    std::cout << "    - Unit ID (PLC)  : " << (int)parsed_frame.unit_id << "\n";
    std::cout << "    - Function Code  : 0x0" << std::hex << (int)parsed_frame.function_code << std::dec 
              << " (" << VoltGuard::ModbusParser::function_name(parsed_frame.function_code) << ")\n";
    std::cout << "    - Register Addr  : 0x000" << parsed_frame.register_address << "\n";
    std::cout << "    - Requested RPM  : " << requested_rpm << " RPM\n\n";

    // Display Physics Enforcement Verdict
    std::cout << "[!] Physics Rules Enforcement:\n";
    std::cout << "    - Rotor Yield Limit    : " << VoltGuard::PhysicsLimits::MAX_SAFE_RPM << " RPM\n";
    std::cout << "    - Verification Verdict : " << VoltGuard::PhysicsEngine::verdict_to_string(verdict) << "\n";
    std::cout << "    - Pipeline Latency     : " << elapsed_ns << " nanoseconds (" << (elapsed_ns / 1000.0) << " microseconds)\n\n";

    if (verdict != VoltGuard::Verdict::ALLOW) {
        std::cout << ">>> [BLOCKED] Malicious OT Payload Successfully Neutralized by VoltGuard! <<<\n";
    } else {
        std::cout << ">>> [FORWARDED] Safe Command Forwarded to Physical Actuator. <<<\n";
    }

    std::cout << "========================================================\n";
    return 0;
}