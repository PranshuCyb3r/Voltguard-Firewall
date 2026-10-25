#include <iostream>
#include <chrono>
#include <winsock2.h>
#include <ws2tcpip.h>
#include "modbus_frame.hpp"
#include "physics_engine.hpp"

#pragma comment(lib, "ws2_32.lib")

#define TCP_PORT 5502
#define UDP_PORT 5555

int main() {
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        std::cerr << "[-] WSAStartup failed.\n";
        return 1;
    }

    // 1. TCP Server Socket for SCADA Ingress Traffic (Port 5502)
    SOCKET server_fd = socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in server_addr{};
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(TCP_PORT);

    BOOL opt = TRUE;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt));

    if (bind(server_fd, (struct sockaddr*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
        std::cerr << "[-] TCP Bind failed on port " << TCP_PORT << "\n";
        return 1;
    }
    listen(server_fd, 5);

    // 2. UDP Client Socket for Broadcasting 32-Byte Telemetry to Qt Dashboard (Port 5555)
    SOCKET udp_sock = socket(AF_INET, SOCK_DGRAM, 0);
    sockaddr_in udp_dest{};
    udp_dest.sin_family = AF_INET;
    udp_dest.sin_port = htons(UDP_PORT);
    inet_pton(AF_INET, "127.0.0.1", &udp_dest.sin_addr);

    std::cout << "========================================================================\n";
    std::cout << " [VoltGuard] Tactical OT Physics Firewall & Live Ingress Daemon Active  \n";
    std::cout << "========================================================================\n";
    std::cout << "[+] Listening for Modbus traffic on TCP port " << TCP_PORT << "...\n";
    std::cout << "[+] Broadcasting Telemetry on UDP port " << UDP_PORT << " (32-Byte Frame)...\n";
    std::cout << "------------------------------------------------------------------------\n";

    while (true) {
        sockaddr_in client_addr{};
        int client_len = sizeof(client_addr);
        SOCKET client_sock = accept(server_fd, (struct sockaddr*)&client_addr, &client_len);
        if (client_sock == INVALID_SOCKET) continue;

        uint8_t buffer[256];
        int bytes_read = recv(client_sock, (char*)buffer, sizeof(buffer), 0);
        if (bytes_read >= static_cast<int>(sizeof(ModbusTcpHeader))) {
            auto start_time = std::chrono::high_resolution_clock::now();

            // Zero-Copy Bitwise Ingress Parse
            const auto* frame = reinterpret_cast<const ModbusTcpHeader*>(buffer);
            uint16_t tx_id = ntohs(frame->transaction_id);
            uint16_t reg = ntohs(frame->register_address);
            uint16_t commanded_rpm = ntohs(frame->register_value);

            // Real-Time Physics Invariance Evaluation
            float shock_bar = 0.0f;
            VoltGuard::Verdict verdict = VoltGuard::PhysicsEngine::evaluate(commanded_rpm, shock_bar);

            auto end_time = std::chrono::high_resolution_clock::now();
            auto latency_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end_time - start_time).count();

            bool is_allowed = (verdict == VoltGuard::Verdict::ALLOW);

            std::cout << "[STREAM] TxID: 0x" << std::hex << tx_id << std::dec
                      << " | Reg: " << reg
                      << " | RPM: " << commanded_rpm
                      << " | Shock: " << shock_bar << " Bar"
                      << " | Verdict: " << (is_allowed ? "ALLOW" : "DROP")
                      << " (" << latency_ns << " ns)\n";

            // Construct Strict 32-Byte Telemetry Frame
            TelemetryFrame telemetry{};
            auto now = std::chrono::system_clock::now().time_since_epoch();
            telemetry.timestamp_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(now).count();
            telemetry.transaction_id = tx_id;
            telemetry.target_register = reg;
            telemetry.injected_rpm = static_cast<float>(commanded_rpm);
            telemetry.joukowsky_bar = shock_bar;
            telemetry.verdict = is_allowed ? 1 : 0;

            // Broadcast to Qt Dashboard over UDP Port 5555
            sendto(udp_sock, (const char*)&telemetry, sizeof(TelemetryFrame), 0,
                   (struct sockaddr*)&udp_dest, sizeof(udp_dest));

            // Return response to client: Echo original packet if ALLOW, or return Modbus Exception 0x86 if DROP
            if (is_allowed) {
                send(client_sock, (const char*)buffer, bytes_read, 0);
            } else {
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