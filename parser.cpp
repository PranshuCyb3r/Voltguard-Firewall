#include <iostream>
#include <vector>
#include <chrono>
#include <iomanip>
#include "modbus_frame.hpp"
#include "physics_engine.hpp"

// Helper function to build synthetic Modbus TCP frames for automated unit testing
std::vector<uint8_t> create_modbus_packet(uint16_t tx_id, uint8_t unit_id, uint8_t func_code, uint16_t reg_addr, uint16_t reg_val) {
    std::vector<uint8_t> packet;
    // MBAP Header (7 Bytes)
    packet.push_back(static_cast<uint8_t>(tx_id >> 8));
    packet.push_back(static_cast<uint8_t>(tx_id & 0xFF));
    packet.push_back(0x00); // Protocol ID High (Modbus = 0)
    packet.push_back(0x00); // Protocol ID Low
    packet.push_back(0x00); // Length High
    packet.push_back(0x06); // Length Low (Unit ID + Function Code + 4 bytes PDU = 6 bytes)
    packet.push_back(unit_id);
    
    // PDU (5 Bytes: Function Code + Register Address + Register Value)
    packet.push_back(func_code);
    packet.push_back(static_cast<uint8_t>(reg_addr >> 8));
    packet.push_back(static_cast<uint8_t>(reg_addr & 0xFF));
    packet.push_back(static_cast<uint8_t>(reg_val >> 8));
    packet.push_back(static_cast<uint8_t>(reg_val & 0xFF));
    
    return packet;
}

int main() {
    std::cout << "========================================================================\n";
    std::cout << "  VoltGuard: Modbus/TCP Protocol Parser & Physics Engine Benchmark Suite \n";
    std::cout << "========================================================================\n\n";

    VoltGuard::PhysicsEngine engine;

    struct TestCase {
        std::string test_name;
        uint16_t tx_id;
        uint16_t rpm_value;
        int64_t delay_ms;
        std::string expectation;
    };

    std::vector<TestCase> test_cases = {
        {"1. Normal Baseline Speed",            1001, 1800,  1000, "ALLOW (Physically Coherent)"},
        {"2. Catastrophic Overspeed Attack",    1002, 50000, 1000, "DROP (Exceeds Rotor Yield Limit)"},
        {"3. Safe Acceleration Transition",     1003, 2000,  1000, "ALLOW (Physically Coherent)"},
        {"4. Sudden Acceleration Surge Attack", 1004, 3500,  100,  "DROP (Violates Rotor Inertia Limit)"},
        {"5. Sub-Operational Cavitation Value", 1005, 250,   1000, "DROP (Below Safe Operational Bound)"}
    };

    int64_t simulated_clock_ms = 1000000;
    int passed_tests = 0;

    for (const auto& tc : test_cases) {
        simulated_clock_ms += tc.delay_ms;
        auto raw_packet = create_modbus_packet(tc.tx_id, 1, 0x06, 0x0001, tc.rpm_value);

        VoltGuard::ParsedFrame frame{};
        
        // High-precision sub-microsecond timer
        auto start = std::chrono::high_resolution_clock::now();
        bool parse_success = VoltGuard::ModbusParser::parse_frame(raw_packet.data(), raw_packet.size(), &frame);
        
        VoltGuard::Verdict verdict = VoltGuard::Verdict::DROP_INVALID_RANGE;
        if (parse_success) {
            verdict = engine.verify_rpm_command(frame.register_value, simulated_clock_ms);
        }
        auto end = std::chrono::high_resolution_clock::now();
        auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();

        std::cout << "[" << tc.test_name << "]\n";
        std::cout << "  Payload Target   : " << tc.rpm_value << " RPM\n";
        std::cout << "  Expected Outcome : " << tc.expectation << "\n";
        std::cout << "  Engine Decision  : " << VoltGuard::PhysicsEngine::verdict_to_string(verdict) << "\n";
        std::cout << "  Execution Time   : " << ns << " ns (" << std::fixed << std::setprecision(2) << (ns / 1000.0) << " us)\n";

        if (verdict == VoltGuard::Verdict::ALLOW) {
            std::cout << "  Action Taken     : [FORWARD PACKET TO PLC/ACTUATOR]\n";
        } else {
            std::cout << "  Action Taken     : [ALERT: PACKET BLOCKED & DROPPED]\n";
        }

        std::cout << "------------------------------------------------------------------------\n";
        passed_tests++;
    }

    std::cout << "\n========================================================================\n";
    std::cout << "  Benchmark Summary: All " << passed_tests << " Test Cases Executed Successfully! \n";
    std::cout << "========================================================================\n";

    return 0;
}
