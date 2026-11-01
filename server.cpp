#include <iostream>
#include <iomanip>
#include <chrono>
#include <winsock2.h>
#include <ws2tcpip.h>

#include "modbus_frame.hpp"
#include "physics_engine.hpp"
#include "telemetry.hpp"

#pragma comment(lib, "ws2_32.lib")

#define MODBUS_PORT 5502
#define TELEMETRY_PORT 5555

int main() {
    std::cout << "========================================================================\n";
    std::cout << "  VOLTGUARD :: PRODUCTION CYBER-PHYSICAL FIREWALL & TWIN DAEMON       \n";
    std::cout << "  Ingress: TCP 5502 (Modbus/TCP) | Egress: UDP 5555 (32-Byte Telemetry) \n";
    std::cout << "========================================================================\n";

    // 1. Initialize Winsock
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        std::cerr << "[FATAL] Failed to initialize Winsock.\n";
        return 1;
    }

    // 2. Setup UDP Telemetry Socket
    SOCKET udp_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    sockaddr_in udp_dest{};
    udp_dest.sin_family = AF_INET;
    udp_dest.sin_port = htons(TELEMETRY_PORT);
    inet_pton(AF_INET, "127.0.0.1", &udp_dest.sin_addr);

    // 3. Setup TCP Server Socket
    SOCKET listen_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    sockaddr_in server_addr{};
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(MODBUS_PORT);

    int opt = 1;
    setsockopt(listen_sock, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt));

    if (bind(listen_sock, (sockaddr*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
        std::cerr << "[FATAL] Bind failed on port " << MODBUS_PORT << ".\n";
        closesocket(listen_sock);
        WSACleanup();
        return 1;
    }

    listen(listen_sock, SOMAXCONN);
    std::cout << "[LISTENING] Air-gapped enclave active on TCP port " << MODBUS_PORT << "...\n";

    VoltGuard::PhysicsEngine engine(1800.0f);
    auto last_time = std::chrono::steady_clock::now();

    while (true) {
        SOCKET client_sock = accept(listen_sock, nullptr, nullptr);
        if (client_sock == INVALID_SOCKET) continue;

        uint8_t buffer[256];
        int bytes_received = recv(client_sock, (char*)buffer, sizeof(buffer), 0);

        if (bytes_received >= 12) {
            const auto* modbus = reinterpret_cast<const VoltGuard::ModbusTCPHeader*>(buffer);
            uint16_t tx_id = VoltGuard::byteswap16(modbus->transaction_id);
            uint16_t rpm = VoltGuard::byteswap16(modbus->register_value);

            auto now = std::chrono::steady_clock::now();
            float dt = std::chrono::duration<float>(now - last_time).count();
            last_time = now;

            float shock = 0.0f;
            float twin_rpm = 1800.0f;

            VoltGuard::Verdict verdict = engine.evaluate(rpm, dt, shock, twin_rpm);

            const char* verdict_str = "[ALLOW: INVARIANT VALID]";
            if (verdict == VoltGuard::Verdict::DROP_VIOLATION_INERTIA_ANOMALY) {
                verdict_str = "[DROP: INERTIA ANOMALY TRIPWIRE]";
            } else if (verdict != VoltGuard::Verdict::ALLOW) {
                verdict_str = "[DROP: PHYSICAL BOUNDS BREACH]";
            }

            std::cout << "[INGRESS] Tx: 0x" << std::hex << std::setw(4) << std::setfill('0') << tx_id << std::dec
                      << " | RPM: " << std::setw(5) << std::setfill('0') << rpm
                      << " | Shock: " << std::fixed << std::setprecision(2) << std::setw(5) << shock << " Bar"
                      << " | Twin: " << std::setw(5) << std::setfill('0') << static_cast<uint16_t>(twin_rpm) << " RPM"
                      << " -> " << verdict_str << "\n";

            // Broadcast 32-Byte Telemetry Frame over UDP
            VoltGuard::TelemetryFrame frame{};
            frame.magic = 0x5647544D; // "VGTM"
            frame.tx_id = tx_id;
            frame.commanded_rpm = rpm;
            frame.pressure_shock_bar = shock;
            frame.twin_estimated_rpm = twin_rpm;
            frame.verdict = static_cast<uint8_t>(verdict);
            frame.timestamp_us = std::chrono::duration_cast<std::chrono::microseconds>(now.time_since_epoch()).count();

            sendto(udp_sock, (const char*)&frame, sizeof(frame), 0, (sockaddr*)&udp_dest, sizeof(udp_dest));
        }

        closesocket(client_sock);
    }

    closesocket(listen_sock);
    closesocket(udp_sock);
    WSACleanup();
    return 0;
}