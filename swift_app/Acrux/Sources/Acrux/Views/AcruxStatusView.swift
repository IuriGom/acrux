import SwiftUI

struct AcruxStatusView: View {
    @EnvironmentObject var acrux: AcruxService
    @State private var knowledgeSummary = ""
    @State private var showKnowledge = false
    @State private var isLoadingKnowledge = false
    @State private var isReverifying = false
    @State private var reverifyMessage: String?
    @State private var passRate = "—"

    private var storagePercent: Double { acrux.status?.storagePercent ?? 0 }
    private var storageUsed: Int { acrux.status?.storageUsedBytes ?? 0 }
    private var storageLimit: Int { acrux.status?.storageLimitBytes ?? 0 }

    @State private var appeared = false
    @State private var isRefreshing = false
    @State private var refreshHovering = false
    @State private var refreshRotation: Double = 0

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                Text("Acrux Status")
                    .font(.system(size: 32, weight: .bold))
                    .opacity(appeared ? 1 : 0)
                    .offset(y: appeared ? 0 : 18)

                HStack {
                    StatusCard(title: "Status", value: acrux.status?.running == true ? "Running" : (acrux.isConnected ? "Online" : "Offline"), color: acrux.isConnected ? .green : .red)
                    StatusCard(title: "Profile", value: acrux.status?.profile ?? "—", color: .primary)
                    StatusCard(title: "Reflection", value: acrux.status?.reflectionModel ?? "—", color: .primary)
                    StatusCard(title: "Embedding", value: acrux.status?.embeddingModel ?? "—", color: .primary)
                }
                .opacity(appeared ? 1 : 0)
                .offset(y: appeared ? 0 : 24)

                HStack {
                    StatusCard(title: "Facts", value: "\(acrux.status?.facts ?? 0)", color: .primary, numeric: true)
                    StatusCard(title: "Skills", value: "\(acrux.status?.skills ?? 0)", color: .primary, numeric: true)
                    StatusCard(title: "Episodes", value: "\(acrux.status?.episodes ?? 0)", color: .primary, numeric: true)
                    StatusCard(title: "Tests", value: passRate, color: .primary, numeric: true)
                }
                .opacity(appeared ? 1 : 0)
                .offset(y: appeared ? 0 : 24)

                if storageLimit > 0 {
                    storageBar
                        .opacity(appeared ? 1 : 0)
                        .offset(y: appeared ? 0 : 18)
                }

                HStack(spacing: 12) {
                    CleanAcruxButton(
                        isOn: acrux.isBackendRunning,
                        isLoading: acrux.isTogglingBackend,
                        action: {
                            if acrux.isBackendRunning {
                                acrux.stopBackend()
                            } else {
                                acrux.startBackend()
                            }
                        }
                    )
                    .disabled(acrux.isTogglingBackend)
                    .opacity(acrux.isTogglingBackend ? 0.6 : 1.0)

                    Button {
                        isRefreshing = true
                        Task {
                            await refresh()
                            isRefreshing = false
                        }
                    } label: {
                        HStack(spacing: 6) {
                            Image(systemName: "arrow.clockwise")
                                .font(.system(size: 14, weight: .semibold))
                                .rotationEffect(.degrees(refreshRotation))
                            Text("Refresh")
                        }
                    }
                    .buttonStyle(WiggleButtonStyle())
                    .onHover { refreshHovering = $0 }
                    .onChange(of: isRefreshing || refreshHovering) { _, spinning in
                        if spinning {
                            withAnimation(.linear(duration: 0.7).repeatForever(autoreverses: false)) {
                                refreshRotation += 360
                            }
                        } else {
                            withAnimation(.default) {
                                refreshRotation = 0
                            }
                        }
                    }

                    Button {
                        reverifyFacts()
                    } label: {
                        HStack(spacing: 6) {
                            if isReverifying {
                                ProgressView()
                                    .controlSize(.small)
                            }
                            Text("Re-verify facts")
                        }
                    }
                    .buttonStyle(FlipButtonStyle())
                    .disabled(isReverifying)
                }
                .opacity(appeared ? 1 : 0)
                .offset(y: appeared ? 0 : 18)

                VStack(alignment: .leading, spacing: 0) {
                    Button {
                        withAnimation(Theme.springSnappy) {
                            showKnowledge.toggle()
                        }
                    } label: {
                        HStack {
                            Text("What it knows")
                                .font(.headline)
                            Spacer()
                            Image(systemName: "chevron.down")
                                .font(.system(size: 12, weight: .semibold))
                                .foregroundStyle(Color.acruxTextSecondary)
                                .rotationEffect(.degrees(showKnowledge ? 180 : 0))
                                .animation(Theme.springSnappy, value: showKnowledge)
                        }
                        .padding()
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)

                    if showKnowledge {
                        Group {
                            if knowledgeSummary.isEmpty {
                                if isLoadingKnowledge {
                                    SkeletonRow()
                                        .padding()
                                } else {
                                    Button("Generate summary") {
                                        loadKnowledge()
                                    }
                                    .buttonStyle(GraphiteButtonStyle())
                                    .frame(maxWidth: .infinity)
                                    .contentShape(Rectangle())
                                    .padding()
                                }
                            } else {
                                Text(knowledgeSummary)
                                    .font(.system(size: 14))
                                    .foregroundStyle(.secondary)
                                    .lineSpacing(4)
                                    .padding()
                            }
                        }
                        .transition(.graphiteAppear)
                    }
                }
                .background(.ultraThinMaterial)
                .clipShape(RoundedRectangle(cornerRadius: 16))
                .opacity(appeared ? 1 : 0)
                .offset(y: appeared ? 0 : 18)
                .animation(Theme.springEntrance, value: appeared)

                if let reverifyMessage {
                    HStack {
                        AnimatedCheckmark()
                        Text(reverifyMessage)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Spacer()
                    }
                    .padding()
                    .background(.ultraThinMaterial)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .transition(.graphiteAppear)
                }

                Spacer()
            }
            .padding(40)
            .animation(Theme.springEntrance, value: appeared)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.acruxBg)
        .task {
            await refresh()
        }
        .onAppear {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                appeared = true
            }
        }
        .onChange(of: showKnowledge) { _, isExpanded in
            if isExpanded && knowledgeSummary.isEmpty && !isLoadingKnowledge {
                loadKnowledge()
            }
        }
    }

    private var storageBar: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Storage")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                Spacer()
                Text("\(formatBytes(storageUsed)) / \(formatBytes(storageLimit)) (\(String(format: "%.0f", storagePercent * 100))%)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .monospacedDigit()
            }
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.acruxSubtleBorder)
                    RoundedRectangle(cornerRadius: 4)
                        .fill(storageColor)
                        .frame(width: max(0, min(geo.size.width, geo.size.width * CGFloat(storagePercent / 100.0))))
                        .animation(.spring(response: 0.6, dampingFraction: 0.75), value: storagePercent)
                }
            }
            .frame(height: 8)
        }
        .padding()
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private func refresh() async {
        await acrux.fetchStatus()
        await loadTestRate()
    }

    private func loadTestRate() async {
        guard let service = AcruxServiceReference.shared else { return }
        let tests = await service.fetchTestResults(project: "")
        let passed = tests.filter(\.passed).count
        passRate = tests.isEmpty ? "—" : "\(passed)/\(tests.count)"
    }

    private func loadKnowledge() {
        isLoadingKnowledge = true
        Task {
            do {
                knowledgeSummary = try await acrux.fetchKnowledgeSummary()
            } catch {
                knowledgeSummary = "Could not generate summary: \(error.localizedDescription)"
            }
            isLoadingKnowledge = false
        }
    }

    private func reverifyFacts() {
        isReverifying = true
        reverifyMessage = nil
        Task {
            let success = await acrux.reverifyFacts()
            await MainActor.run {
                isReverifying = false
                reverifyMessage = success ? "Facts queued for re-verification." : "Re-verification request failed."
                if success {
                    Task {
                        try? await Task.sleep(nanoseconds: 1_000_000_000)
                        await acrux.fetchStatus()
                    }
                }
            }
        }
    }

    private var storageColor: Color {
        let fraction = storagePercent / 100.0
        switch fraction {
        case 0..<0.8: return .green
        case 0.8..<0.95: return .yellow
        default: return .red
        }
    }
}

struct StatusCard: View {
    let title: String
    let value: String
    let color: Color
    let numeric: Bool
    @State private var appeared = false

    init(title: String, value: String, color: Color, numeric: Bool = false) {
        self.title = title
        self.value = value
        self.color = color
        self.numeric = numeric
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title.uppercased())
                .font(.caption2.weight(.semibold))
                .foregroundStyle(.secondary)
            Text(value)
                .font(.system(size: 18, weight: .bold))
                .foregroundStyle(color)
                .contentTransition(numeric ? .numericText() : .opacity)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .graphiteHoverRow()
        .scaleEffect(appeared ? 1 : 0.92)
        .opacity(appeared ? 1 : 0)
        .animation(Theme.springEntrance, value: appeared)
        .onAppear { appeared = true }
    }
}

private func formatBytes(_ bytes: Int) -> String {
    let units = ["B", "KB", "MB", "GB", "TB"]
    var value = Double(bytes)
    var idx = 0
    while value >= 1024 && idx < units.count - 1 {
        value /= 1024
        idx += 1
    }
    return String(format: "%.1f %@", value, units[idx])
}

/// Clean animated Start/Stop button with a spinning icon + ripple on tap.
struct CleanAcruxButton: View {
    let isOn: Bool
    let isLoading: Bool
    let action: () -> Void
    @State private var hovering = false
    @State private var pressing = false
    @State private var ripple = false
    @State private var iconRotation: Double = 0

    var body: some View {
        Button {
            handleTap()
        } label: {
            ZStack {
                RoundedRectangle(cornerRadius: 12)
                    .fill(isOn ? Color.acruxAccent.opacity(0.12) : Color.acruxCard)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(isOn ? Color.acruxAccent.opacity(0.6) : Color.acruxSubtleBorder, lineWidth: 2)
                    )

                if ripple {
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(isOn ? Color.acruxAccent : Color.acruxTextSecondary, lineWidth: 2)
                        .scaleEffect(ripple ? 1.35 : 0.95)
                        .opacity(ripple ? 0 : 1)
                }

                HStack(spacing: 10) {
                    if isLoading {
                        ProgressView()
                            .controlSize(.small)
                            .scaleEffect(0.8)
                    } else {
                        Image(systemName: "power")
                            .font(.system(size: 16, weight: .black))
                            .foregroundStyle(isOn ? Color.acruxAccent : Color.acruxTextSecondary)
                            .rotationEffect(.degrees(iconRotation))
                        Text(isOn ? "Stop Acrux" : "Start Acrux")
                            .font(.system(size: 13, weight: .bold))
                            .foregroundStyle(isOn ? Color.acruxAccent : .primary)
                    }
                    Spacer()
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 12)
            }
            .frame(width: 150, height: 46)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .scaleEffect(pressing ? 0.95 : (hovering ? 1.04 : 1.0))
        .shadow(color: .black.opacity(hovering ? 0.45 : 0.25), radius: hovering ? 14 : 8, y: hovering ? 5 : 3)
        .animation(Theme.springPop, value: pressing)
        .animation(Theme.springSnappy, value: hovering)
        .onHover { hovering = $0 }
        .disabled(isLoading)
    }

    private func handleTap() {
        withAnimation(Theme.springPop) {
            pressing = true
            iconRotation += 360
        }
        withAnimation(Theme.springSnappy) {
            ripple = true
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.12) {
            pressing = false
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
            ripple = false
        }
        action()
    }
}
