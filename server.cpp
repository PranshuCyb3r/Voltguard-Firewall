#include <iostream>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <chrono>
#include <iomanip>
#include "modbus_frame.hpp"
#include "telemetry.hpp"
#include "physics_engine.hpp"

#pragma comment(lib, "ws2_32.lib")

inline uint16_t swap_endian16(uint16_t val) {
    return (val << 8) | (val >> 8);
}

int main() {
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        std::cerr << "[ERROR] WSAStartup failed\n";
        return 1;
    }

    std::cout << "========================================================================\n";
    std::cout << "  VOLTGUARD :: PRODUCTION CYBER-PHYSICAL FIREWALL & TWIN DAEMON       \n";
    std::cout << "  Ingress: TCP 5502 (Modbus/TCP) | Egress: UDP 5555 (32-Byte Telemetry) \n";
    std::cout << "========================================================================\n";

    // 1. Setup UDP Telemetry Egress Socket (Port 5555)
    SOCKET udp_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    sockaddr_in udp_dest{};
    udp_dest.sin_family = AF_INET;
    udp_dest.sin_port = htons(5555);
    inet_pton(AF_INET, "127.0.0.1", &udp_dest.sin_addr);

    // 2. Setup Ingress TCP Server Socket (Port 5502)
    SOCKET server_fd = socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in server_addr{};
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(5502);
    server_addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(server_fd, (struct sockaddr*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
        std::cerr << "[ERROR] TCP Bind failed on 5502\n";
        closesocket(server_fd);
        WSACleanup();
        return 1;
    }

    listen(server_fd, 5);
    std::cout << "[LISTENING] Air-gapped enclave active on TCP port 5502...\n";

    VoltGuard::PhysicsEngine engine;
    auto start_epoch = std::chrono::steady_clock::now();

    while (true) {
        SOCKET client_sock = accept(server_fd, nullptr, nullptr);
        if (client_sock == INVALID_SOCKET) continue;

        char buffer[128];
        int bytes_read = recv(client_sock, buffer, sizeof(buffer), 0);

        if (bytes_read >= 12) {
            auto* mb = reinterpret_cast<ModbusTcpHeader*>(buffer);
            uint16_t tx_id = swap_endian16(mb->transaction_id);
            uint16_t raw_rpm = swap_endian16(mb->register_value);

            auto now = std::chrono::steady_clock::now();
            double cur_time = std::chrono::duration<double>(now - start_epoch).count();

            float shock_bar = 0.0f;
            float twin_rpm = 0.0f;
            VoltGuard::Verdict verdict = engine.evaluate(raw_rpm, cur_time, shock_bar, twin_rpm);

            // Construct 32-Byte Telemetry Frame
            TelemetryFrame frame{};
            frame.magic_header = 0x56475458; // "VGTX"
            frame.transaction_id = tx_id;
            frame.commanded_rpm = raw_rpm;
            frame.joukowsky_shock_bar = shock_bar;
            frame.twin_predicted_rpm = twin_rpm;
            frame.verdict = (verdict == VoltGuard::Verdict::ALLOW) ? 0 : 1;
            frame.timestamp_us = std::chrono::duration_cast<std::chrono::microseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count();

            // Broadcast to UDP Visualizer
            sendto(udp_sock, reinterpret_cast<const char*>(&frame), sizeof(frame), 0,
                   reinterpret_cast<sockaddr*>(&udp_dest), sizeof(udp_dest));

            // Terminal Journal Output
            std::cout << "[INGRESS] Tx: 0x" << std::hex << std::setw(4) << std::setfill('0') << tx_id << std::dec
                      << " | RPM: " << std::setw(5) << std::setfill('0') << raw_rpm
                      << " | Shock: " << std::fixed << std::setprecision(2) << std::setw(5) << shock_bar << " Bar"
                      << " | Twin: " << std::setw(5) << std::setfill('0') << static_cast<int>(twin_rpm) << " RPM -> ";

            if (verdict == VoltGuard::Verdict::ALLOW) {
                std::cout << "[ALLOW: INVARIANT VALID]\n";
                send(client_sock, buffer, bytes_read, 0); // Echo packet forward
            } else {
                std::cout << "[DROP: ";
                if (verdict == VoltGuard::Verdict::DROP_VIOLATION_INERTIA_SLIP) {
                    std::cout << "INERTIA ANOMALY TRIPWIRE]\n";
                } else {
                    std::cout << "PHYSICAL BOUNDS BREACH]\n";
                }
                uint8_t err_resp[9] = { buffer[0], buffer[1], 0x00, 0x00, 0x00, 0x03, buffer[6], 0x86, 0x04 };
                send(client_sock, reinterpret_cast<const char*>(err_resp), sizeof(err_resp), 0);
            }
        }
        closesocket(client_sock);
    }

    closesocket(server_fd);
    closesocket(udp_sock);
    WSACleanup();
    return 0;
}