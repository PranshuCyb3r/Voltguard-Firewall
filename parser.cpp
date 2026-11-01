#include <iostream>
#include <iomanip>
#include "modbus_frame.hpp"
#include "physics_engine.hpp"

int main() {
    std::cout << "========================================================================\n";
    std::cout << "  VOLTGUARD :: L2 ZERO-COPY PROTOCOL & INLINE PHYSICS PARSER DEMO       \n";
    std::cout << "========================================================================\n\n";

    VoltGuard::PhysicsEngine engine(1800.0f);

    uint8_t normal_packet[12] = {
        0x01, 0x01, 0x00, 0x00, 0x00, 0x06, 0x01, 0x06, 0x00, 0x01, 0x07, 0x08
    };

    const auto* modbus = reinterpret_cast<const VoltGuard::ModbusTCPHeader*>(normal_packet);
    uint16_t tx_id = VoltGuard::byteswap16(modbus->transaction_id);
    uint16_t reg_addr = VoltGuard::byteswap16(modbus->register_address);
    uint16_t rpm = VoltGuard::byteswap16(modbus->register_value);

    float shock = 0.0f;
    VoltGuard::Verdict verdict = engine.evaluate(rpm, shock);

    std::cout << "[INGRESS 1 - NORMAL LAMINAR]\n";
    std::cout << "  Transaction ID : 0x" << std::hex << std::setw(4) << std::setfill('0') << tx_id << std::dec << "\n";
    std::cout << "  Target Register: 0x" << std::hex << std::setw(4) << std::setfill('0') << reg_addr << std::dec << "\n";
    std::cout << "  Commanded RPM  : " << rpm << " RPM\n";
    std::cout << "  Joukowsky Shock: " << std::fixed << std::setprecision(2) << shock << " Bar\n";
    std::cout << "  Firewall Rule  : " << (verdict == VoltGuard::Verdict::ALLOW ? "[ ALLOW: INVARIANT PASSED ]" : "[ DROP: BREACH ]") << "\n\n";

    uint8_t attack_packet[12] = {
        0x01, 0x03, 0x00, 0x00, 0x00, 0x06, 0x01, 0x06, 0x00, 0x01, 0xC3, 0x50
    };

    const auto* atk_modbus = reinterpret_cast<const VoltGuard::ModbusTCPHeader*>(attack_packet);
    uint16_t atk_tx = VoltGuard::byteswap16(atk_modbus->transaction_id);
    uint16_t atk_rpm = VoltGuard::byteswap16(atk_modbus->register_value);

    float atk_shock = 0.0f;
    VoltGuard::Verdict atk_verdict = engine.evaluate(atk_rpm, atk_shock);

    std::cout << "[INGRESS 2 - OVERPRESSURE CYBER ATTACK INJECTION]\n";
    std::cout << "  Transaction ID : 0x" << std::hex << std::setw(4) << std::setfill('0') << atk_tx << std::dec << "\n";
    std::cout << "  Commanded RPM  : " << atk_rpm << " RPM (MALICIOUS)\n";
    std::cout << "  Joukowsky Shock: " << std::fixed << std::setprecision(2) << atk_shock << " Bar (Limit: 16.0 Bar)\n";
    std::cout << "  Firewall Rule  : " << (atk_verdict == VoltGuard::Verdict::ALLOW ? "[ ALLOW ]" : "[ DROP: CATASTROPHIC INVARIANT BREACH INTERCEPTED ]") << "\n\n";

    float stall_shock = 0.0f;
    VoltGuard::Verdict stall_v = engine.evaluate(300, stall_shock);
    std::cout << "[INGRESS 3 - IMPELLER CAVITATION VACUUM TEST]\n";
    std::cout << "  Commanded RPM  : 300 RPM\n";
    std::cout << "  Joukowsky Shock: " << std::fixed << std::setprecision(2) << stall_shock << " Bar\n";
    std::cout << "  Firewall Rule  : " << (stall_v == VoltGuard::Verdict::ALLOW ? "[ ALLOW ]" : "[ DROP: CAVITATION VACUUM FLOOR BREACH ]") << "\n";

    std::cout << "========================================================================\n";
    return 0;
}