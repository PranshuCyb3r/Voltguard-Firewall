#include <iostream>
#include <vector>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <chrono>
#include <cstring>

#include "modbus_frame.hpp"
#include "physics_engine.hpp"
#include "telemetry.hpp"

#pragma comment(lib, "ws2_32.lib")

#define MODBUS_PORT 5502       // Port for Modbus SCADA Traffic (Week 1 matches client_test.py)
#define TELEMETRY_PORT 5555    // UDP Broadcast Port for Qt UI Live Streaming

int main() {
    std::cout << "========================================================================\n";
    std::cout << " [VoltGuard] Week 2: Telemetry Pipeline & Live Daemon Active           \n";
    std::cout << "========================================================================\n";

    // 1. Initialize Winsock
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        std::cerr << "[-] WSAStartup failed.\n";
        return 1;
    }

    // 2. Setup Telemetry UDP Broadcast Socket (For Qt GUI Window)
    SOCKET telemSocket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    sockaddr_in telemAddr{};
    telemAddr.sin_family = AF_INET;
    telemAddr.sin_port = htons(TELEMETRY_PORT);
    telemAddr.sin_addr.s_addr = inet_addr("127.0.0.1");

    // 3. Setup Modbus TCP Listener Socket
    SOCKET listenSocket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (listenSocket == INVALID_SOCKET) {
        std::cerr << "[-] Socket creation failed.\n";
        WSACleanup();
        return 1;
    }

    BOOL optval = TRUE;
    setsockopt(listenSocket, SOL_SOCKET, SO_REUSEADDR, (char*)&optval, sizeof(optval));

    sockaddr_in serverService{};
    serverService.sin_family = AF_INET;
    serverService.sin_addr.s_addr = INADDR_ANY;
    serverService.sin_port = htons(MODBUS_PORT);

    if (bind(listenSocket, (SOCKADDR*)&serverService, sizeof(serverService)) == SOCKET_ERROR) {
        std::cerr << "[-] Bind failed on port " << MODBUS_PORT << "\n";
        closesocket(listenSocket);
        WSACleanup();
        return 1;
    }

    if (listen(listenSocket, SOMAXCONN) == SOCKET_ERROR) {
        std::cerr << "[-] Listen error.\n";
        closesocket(listenSocket);
        WSACleanup();
        return 1;
    }

    std::cout << "[+] Listening for Modbus traffic on port " << MODBUS_PORT << "...\n";
    std::cout << "[+] Telemetry stream active on UDP port " << TELEMETRY_PORT << " (For Qt Dashboard)...\n";
    std::cout << "------------------------------------------------------------------------\n";

    VoltGuard::PhysicsEngine engine;
    uint8_t buffer[1024];

    while (true) {
        sockaddr_in clientAddr{};
        int clientAddrLen = sizeof(clientAddr);
        SOCKET clientSocket = accept(listenSocket, (SOCKADDR*)&clientAddr, &clientAddrLen);
        if (clientSocket == INVALID_SOCKET) {
            continue;
        }

        std::memset(buffer, 0, sizeof(buffer));
        int bytesReceived = recv(clientSocket, (char*)buffer, sizeof(buffer), 0);
        if (bytesReceived > 0) {
            auto now_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count();
            auto now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count();

            VoltGuard::ParsedFrame frame{};
            auto start_time = std::chrono::high_resolution_clock::now();

            // Correct method matching modbus_frame.hpp
            bool parse_ok = VoltGuard::ModbusParser::parse_frame(buffer, bytesReceived, &frame);

            if (parse_ok) {
                // Correct method matching physics_engine.hpp
                VoltGuard::Verdict verdict = engine.verify_rpm_command(frame.register_value, now_ms);
                auto end_time = std::chrono::high_resolution_clock::now();
                auto lat_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end_time - start_time).count();

                // Compute dynamic water hammer pressure shock (Joukowsky baseline)
                float delta_rpm = static_cast<float>(frame.register_value);
                float transient_bar = 4.52f + (delta_rpm / 1000.0f) * 1.8f;

                // Build Week 2 Telemetry Frame (32 bytes)
                TelemetryFrame telemFrame{};
                telemFrame.timestamp_ns   = now_ns;
                telemFrame.transaction_id = frame.transaction_id;
                telemFrame.target_register= frame.register_address;
                telemFrame.injected_rpm   = delta_rpm;
                telemFrame.joukowsky_bar  = transient_bar;
                telemFrame.verdict        = (verdict == VoltGuard::Verdict::ALLOW) ? 0x01 : 0x00;

                // Stream frame to Qt UI via UDP loopback
                sendto(telemSocket, (const char*)&telemFrame, sizeof(telemFrame), 0, 
                       (sockaddr*)&telemAddr, sizeof(telemAddr));

                std::cout << "[STREAM] TxID: 0x" << std::hex << frame.transaction_id << std::dec
                          << " | Reg: " << frame.register_address
                          << " | RPM: " << frame.register_value
                          << " | Shock: " << transient_bar << " Bar"
                          << " | Verdict: " << (telemFrame.verdict ? "ALLOW" : "DROP")
                          << " (" << lat_ns << " ns)\n";

                if (verdict == VoltGuard::Verdict::ALLOW) {
                    const char* resp = "STATUS: ALLOWED\n";
                    send(clientSocket, resp, (int)strlen(resp), 0);
                } else {
                    const char* resp = "STATUS: BLOCKED_BY_VOLTGUARD_PHYSICS_ENGINE\n";
                    send(clientSocket, resp, (int)strlen(resp), 0);
                }
            } else {
                const char* malformed_resp = "STATUS: ERROR_MALFORMED_FRAME\n";
                send(clientSocket, malformed_resp, (int)strlen(malformed_resp), 0);
            }
        }
        closesocket(clientSocket);
    }

    closesocket(listenSocket);
    closesocket(telemSocket);
    WSACleanup();
    return 0;
}
