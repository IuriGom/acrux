import SwiftUI

struct HealthCheckView: View {
    @State private var checks: [HealthCheck] = []
    @State private var checksums: [ChecksumStatus] = []
    @State private var isLoading = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Health checks")
                    .font(.system(size: 18, weight: .bold))
                Spacer()
                Button {
                    Task { await runChecks() }
                } label: {
                    Label("Run now", systemImage: "play.fill")
                }
                .buttonStyle(GraphiteButtonStyle())
                Button {
                    Task { await load() }
                } label: {
                    Image(systemName: "arrow.clockwise")
                }
                .buttonStyle(GraphiteButtonStyle())
            }
            .padding()

            if isLoading {
                VStack(spacing: 12) {
                    SkeletonRow()
                    SkeletonRow()
                    SkeletonRow()
                }
                .padding()
            } else {
                List {
                    Section("Checks") {
                        let hasIssues = checks.contains { $0.severity == "error" || $0.severity == "warning" }
                        if !hasIssues {
                            HStack(spacing: 12) {
                                AnimatedCheckmark()
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("ALL GOOD")
                                        .font(.system(size: 10, weight: .bold))
                                        .foregroundStyle(.secondary)
                                    Text("No health issues detected. Acrux is operating normally.")
                                        .font(.system(size: 13))
                                }
                            }
                            .padding(10)
                            .background(.ultraThinMaterial)
                            .clipShape(RoundedRectangle(cornerRadius: 10))
                            .graphiteHoverRow()
                            .listRowBackground(Color.clear)
                            .listRowSeparator(.hidden)
                        }
                        if !checks.isEmpty {
                            ForEach(checks) { check in
                                HStack(spacing: 12) {
                                    Circle()
                                        .fill(color(for: check.severity))
                                        .frame(width: 8, height: 8)
                                    VStack(alignment: .leading, spacing: 4) {
                                        HStack {
                                            Text(check.checkType.uppercased())
                                                .font(.system(size: 10, weight: .bold))
                                                .foregroundStyle(.secondary)
                                            Spacer()
                                            Text(check.createdAt, style: .date)
                                                .font(.caption2)
                                                .foregroundStyle(.secondary)
                                        }
                                        Text(check.message)
                                            .font(.system(size: 13))
                                        if let project = check.project {
                                            Text(project)
                                                .font(.caption2)
                                                .foregroundStyle(.secondary)
                                        }
                                    }
                                }
                                .padding(10)
                                .background(.ultraThinMaterial)
                                .clipShape(RoundedRectangle(cornerRadius: 10))
                                .graphiteHoverRow()
                                .listRowBackground(Color.clear)
                                .listRowSeparator(.hidden)
                            }
                        }
                    }

                    Section("Checksums") {
                        if checksums.isEmpty {
                            Text("No checksums on record.")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        } else {
                            ForEach(checksums) { item in
                                HStack {
                                    Text(item.filePath)
                                        .font(.system(size: 12, design: .monospaced))
                                    Spacer()
                                    Text(item.checksum.prefix(8))
                                        .font(.system(size: 11, design: .monospaced))
                                        .foregroundStyle(.secondary)
                                }
                                .padding(10)
                                .background(.ultraThinMaterial)
                                .clipShape(RoundedRectangle(cornerRadius: 10))
                                .graphiteHoverRow()
                                .listRowBackground(Color.clear)
                                .listRowSeparator(.hidden)
                            }
                        }
                    }
                }
                .scrollContentBackground(.hidden)
            }
        }
        .frame(minWidth: 500, minHeight: 400)
        .task { await load() }
    }

    private func load() async {
        guard let service = AcruxServiceReference.shared else { return }
        isLoading = true
        async let c: [HealthCheck] = service.fetchHealthChecks()
        async let s: [ChecksumStatus] = service.fetchChecksums()
        checks = await c
        checksums = await s
        isLoading = false
    }

    private func runChecks() async {
        guard let service = AcruxServiceReference.shared else { return }
        _ = await service.runHealthChecks()
        await load()
    }

    private func color(for severity: String) -> Color {
        switch severity.lowercased() {
        case "error": return .red
        case "warning": return .yellow
        default: return .green
        }
    }
}
