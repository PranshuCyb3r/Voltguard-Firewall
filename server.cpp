#include <iostream>
#include <chrono>
#include <winsock2.h>
#include <ws2tcpip.h>
#include "modbus_frame.hpp"
#include "physics_engine.hpp"
#include "telemetry.hpp"

#pragma comment(lib, "ws2_32.lib")

int main() {
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);

    SOCKET server_fd = socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in server_addr{};
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(5502);

    bind(server_fd, (sockaddr*)&server_addr, sizeof(server_addr));
    listen(server_fd, 5);

    std::cout << "========================================================================\n";
    std::cout << " [VoltGuard] Production OT Telemetry Daemon & Physics Firewall Active  \n";
    std::cout << "========================================================================\n";
    std::cout << "[+] Modbus TCP Ingestion Interface : 127.0.0.1:5502\n";
    std::cout << "[+] Real-Time UDP Telemetry Stream  : 127.0.0.1:5555\n";
    std::cout << "------------------------------------------------------------------------\n";

    VoltGuard::PhysicsEngine engine;
    TelemetryPublisher publisher("127.0.0.1", 5555);

    while (true) {
        SOCKET client_fd = accept(server_fd, nullptr, nullptr);
        char buffer[512];
        int bytes_read = recv(client_fd, buffer, sizeof(buffer), 0);

        if (bytes_read >= sizeof(ModbusTcpHeader)) {
            auto start_eval = std::chrono::high_resolution_clock::now();
            auto* hdr = reinterpret_cast<ModbusTcpHeader*>(buffer);

            uint16_t tx_id = ntohs(hdr->transaction_id);
            uint16_t raw_val = ntohs(hdr->register_value);
            float rpm = static_cast<float>(raw_val);
            float shock_bar = 0.0f;

            auto verdict = engine.evaluate(rpm, shock_bar);
            auto end_eval = std::chrono::high_resolution_clock::now();
            auto latency_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end_eval - start_eval).count();

            // Populate binary telemetry frame
            TelemetryFrame frame{};
            frame.timestamp_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
                std::chrono::steady_clock::now().time_since_epoch()).count();
            frame.transaction_id = tx_id;
            frame.target_register = ntohs(hdr->register_address);
            frame.injected_rpm = rpm;
            frame.joukowsky_bar = shock_bar;
            frame.verdict = (verdict == VoltGuard::Verdict::ALLOW) ? 1 : 0;

            // Broadcast to Qt Visualizer
            publisher.publish(frame);

            // Respond back to SCADA PLC
            if (verdict == VoltGuard::Verdict::ALLOW) {
                send(client_fd, "STATUS: ALLOWED\n", 16, 0);
                std::cout << "[STREAM] TxID: 0x" << std::hex << tx_id << std::dec
                          << " | RPM: " << (int)rpm << " | Shock: " << shock_bar
                          << " Bar | Verdict: ALLOW (" << latency_ns << " ns)\n";
            } else {
                send(client_fd, "STATUS: BLOCKED_BY_VOLTGUARD_PHYSICS_ENGINE\n", 44, 0);
                std::cout << "[STREAM] TxID: 0x" << std::hex << tx_id << std::dec
                          << " | RPM: " << (int)rpm << " | Shock: " << shock_bar
                          << " Bar | Verdict: DROP (" << latency_ns << " ns) [TRIPWIRE]\n";
            }
        }
        closesocket(client_fd);
    }

    closesocket(server_fd);
    WSACleanup();
    return 0;
}