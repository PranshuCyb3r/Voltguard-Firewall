#include <iostream>
#include <iomanip>
#include <chrono>
#include <string>
#include <winsock2.h>
#include <ws2tcpip.h>

#include "modbus_frame.hpp"
#include "physics_engine.hpp"
#include "telemetry.hpp"

#pragma comment(lib, "ws2_32.lib")

constexpr int MODBUS_PORT = 5502;
constexpr int TELEMETRY_PORT = 5555;
constexpr const char* TELEMETRY_IP = "127.0.0.1";

const char* verdict_to_string(VoltGuard::Verdict v) {
    switch (v) {
        case VoltGuard::Verdict::ALLOW:
            return "[ ALLOW: INVARIANT VALID ]";
        case VoltGuard::Verdict::DROP_VIOLATION_RPM_MAX:
            return "[ DROP: MECHANICAL ROTOR CEILING BREACH ]";
        case VoltGuard::Verdict::DROP_VIOLATION_CAVITATION:
            return "[ DROP: CAVITATION VACUUM FLOOR BREACH ]";
        case VoltGuard::Verdict::DROP_VIOLATION_JOUKOWSKY_SHOCK:
            return "[ DROP: JOUKOWSKY PIPE BURST SURGE ]";
        case VoltGuard::Verdict::DROP_VIOLATION_INERTIA_SLIP:
            return "[ DROP: ROTOR INERTIA STEP JUMP SLIP ]";
        case VoltGuard::Verdict::DROP_CUMULATIVE_FATIGUE:
            return "[ DROP: CUMULATIVE MECHANICAL FATIGUE BREACH ]";
        case VoltGuard::Verdict::DROP_SUSTAINED_OVERLOAD:
            return "[ DROP: SUSTAINED HIGH-STRESS OVERLOAD ]";
        default:
            return "[ DROP: UNKNOWN INVARIANT VIOLATION ]";
    }
}

int main() {
    std::cout << "========================================================================\n";
    std::cout << "  VOLTGUARD :: PRODUCTION CYBER-PHYSICAL OT FIREWALL DAEMON (WEEK 4)\n";
    std::cout << "  L2 Zero-Copy Ingress | State-Space Fatigue & RK4 Multi-Invariant IPS\n";
    std::cout << "========================================================================\n";

    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        std::cerr << "[-] WSAStartup failed\n";
        return 1;
    }

    // 1. Setup UDP Telemetry Socket
    SOCKET udp_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    sockaddr_in udp_dest{};
    udp_dest.sin_family = AF_INET;
    udp_dest.sin_port = htons(TELEMETRY_PORT);
    inet_pton(AF_INET, TELEMETRY_IP, &udp_dest.sin_addr);

    // 2. Setup Modbus TCP Server Socket (Port 5502)
    SOCKET server_fd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    sockaddr_in server_addr{};
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(MODBUS_PORT);

    if (bind(server_fd, (sockaddr*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
        std::cerr << "[-] TCP Bind failed on port " << MODBUS_PORT << "\n";
        closesocket(server_fd);
        WSACleanup();
        return 1;
    }

    listen(server_fd, 5);
    std::cout << "[+] OT Firewall listening on 0.0.0.0:" << MODBUS_PORT << " (Modbus/TCP)\n";
    std::cout << "[+] Live Telemetry Stream broadcast: " << TELEMETRY_IP << ":" << TELEMETRY_PORT << " (UDP)\n";
    std::cout << "------------------------------------------------------------------------\n";

    VoltGuard::PhysicsEngine engine;
    auto start_time = std::chrono::steady_clock::now();

    while (true) {
        sockaddr_in client_addr{};
        int client_len = sizeof(client_addr);
        SOCKET client_sock = accept(server_fd, (sockaddr*)&client_addr, &client_len);
        if (client_sock == INVALID_SOCKET) continue;

        uint8_t buffer[64];
        int bytes_read = recv(client_sock, (char*)buffer, sizeof(buffer), 0);

        if (bytes_read >= 12) {
            auto auto_now = std::chrono::steady_clock::now();
            double current_time_sec = std::chrono::duration<double>(auto_now - start_time).count();
            uint64_t timestamp_us = std::chrono::duration_cast<std::chrono::microseconds>(auto_now.time_since_epoch()).count();

            // Zero-copy parse header & payload
            uint16_t tx_id = (buffer[0] << 8) | buffer[1];
            uint16_t commanded_rpm = (buffer[10] << 8) | buffer[11];

            // Evaluate through Multi-Invariant Physics Engine
            double shock_bar = 0.0;
            double twin_rpm = 0.0;
            VoltGuard::Verdict verdict = engine.evaluate(commanded_rpm, current_time_sec, shock_bar, twin_rpm);
            double fatigue = engine.get_current_fatigue();

            // Emit 32-Byte Telemetry Frame to UDP visualizer
            TelemetryFrame frame{};
            frame.magic = 0x56475544; // "VGUD"
            frame.transaction_id = tx_id;
            frame.commanded_rpm = commanded_rpm;
            frame.joukowsky_shock_bar = static_cast<float>(shock_bar);
            frame.digital_twin_rpm = static_cast<float>(twin_rpm);
            frame.cumulative_fatigue = static_cast<float>(fatigue);
            frame.verdict = static_cast<uint8_t>(verdict);
            frame.timestamp_us = timestamp_us;

            sendto(udp_sock, (const char*)&frame, sizeof(frame), 0, (sockaddr*)&udp_dest, sizeof(udp_dest));

            // Terminal Audit Log
            std::cout << "[INGRESS] Tx: 0x" << std::hex << std::setw(4) << std::setfill('0') << tx_id << std::dec
                      << " | RPM: " << std::setw(5) << commanded_rpm
                      << " | Shock: " << std::fixed << std::setprecision(2) << shock_bar << " Bar"
                      << " | Twin: " << std::setw(5) << static_cast<int>(twin_rpm) << " RPM"
                      << " | Fatigue: " << std::fixed << std::setprecision(1) << fatigue
                      << " -> " << verdict_to_string(verdict) << "\n";

            // Wire IPS Verdict Response
            if (verdict == VoltGuard::Verdict::ALLOW) {
                send(client_sock, (const char*)buffer, bytes_read, 0); // Echo valid packet
            } else {
                // Modbus Exception Response 0x86 (Server Device Failure / Invariant Drop)
                uint8_t err_resp[9] = {
                    buffer[0], buffer[1], 0x00, 0x00, 0x00, 0x03, buffer[6], 0x86, 0x04
                };
                send(client_sock, (const char*)err_resp, sizeof(err_resp), 0);
            }
        }
        closesocket(client_sock);
    }

    closesocket(server_fd);
    closesocket(udp_sock);
    WSACleanup();
    return 0;
}