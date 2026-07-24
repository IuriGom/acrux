import SwiftUI

struct MemoryDecayView: View {
    let project: String
    @State private var threshold = 0.7
    @State private var facts: [DecayFact] = []
    @State private var isLoading = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Memory decay")
                    .font(.system(size: 18, weight: .bold))
                Spacer()
                HStack {
                    Text("Threshold")
                        .font(.caption)
                    Slider(value: $threshold, in: 0...1, step: 0.05)
                        .frame(width: 120)
                    Text(String(format: "%.0f%%", threshold * 100))
                        .font(.caption)
                        .monospacedDigit()
                }
                Button {
                    Task { await recompute() }
                } label: {
                    Label("Recompute", systemImage: "goforward")
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
                ProgressView()
                    .padding()
            } else if facts.isEmpty {
                ContentUnavailableView("All fresh", systemImage: "sparkles", description: Text("No facts exceed the staleness threshold."))
            } else {
                List(facts) { fact in
                    HStack(spacing: 12) {
                        DecayDot(score: fact.decayScore)
                        VStack(alignment: .leading, spacing: 4) {
                            Text(fact.content)
                                .font(.system(size: 13))
                            Text("Score: \(String(format: "%.2f", fact.decayScore))")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                    }
                    .padding(10)
                    .background(.ultraThinMaterial)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                    .listRowBackground(Color.clear)
                    .listRowSeparator(.hidden)
                }
                .scrollContentBackground(.hidden)
            }
        }
        .frame(minWidth: 420, minHeight: 400)
        .task { await load() }
        .onChange(of: threshold) { _, _ in
            Task { await load() }
        }
    }

    private func load() async {
        guard let service = AcruxServiceReference.shared else { return }
        isLoading = true
        facts = await service.fetchStaleFacts(project: project, threshold: threshold)
        isLoading = false
    }

    private func recompute() async {
        guard let service = AcruxServiceReference.shared else { return }
        _ = await service.recomputeDecay()
        await load()
    }
}
