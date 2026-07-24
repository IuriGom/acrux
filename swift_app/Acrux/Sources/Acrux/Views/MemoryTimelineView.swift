import SwiftUI

struct MemoryTimelineView: View {
    let project: String
    @State private var since = Calendar.current.date(byAdding: .day, value: -7, to: Date()) ?? Date()
    @State private var until = Date()
    @State private var events: [TimelineEvent] = []
    @State private var isLoading = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Timeline")
                    .font(.system(size: 18, weight: .bold))
                Spacer()
                DatePicker("Since", selection: $since, displayedComponents: .date)
                    .datePickerStyle(.compact)
                DatePicker("Until", selection: $until, displayedComponents: .date)
                    .datePickerStyle(.compact)
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
            } else if events.isEmpty {
                ContentUnavailableView("No events", systemImage: "timeline.selection", description: Text("Nothing changed in this window."))
            } else {
                List(events) { event in
                    HStack(alignment: .top, spacing: 12) {
                        Circle()
                            .fill(color(for: event.type))
                            .frame(width: 8, height: 8)
                            .padding(.top, 6)
                        VStack(alignment: .leading, spacing: 4) {
                            Text(event.type.uppercased())
                                .font(.system(size: 10, weight: .bold))
                                .foregroundStyle(.secondary)
                            Text(event.content)
                                .font(.system(size: 13))
                            Text(event.timestamp, style: .date)
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
    }

    private func load() async {
        guard let service = AcruxServiceReference.shared else { return }
        isLoading = true
        events = await service.fetchTimeline(project: project, since: since, until: until)
        isLoading = false
    }

    private func color(for type: String) -> Color {
        // Graphite ramp: brightness distinguishes event types, no chroma.
        switch type.lowercased() {
        case "fact": return .acruxAccent
        case "episode": return Color(red: 0.62, green: 0.65, blue: 0.69)
        case "version": return Color(red: 0.48, green: 0.51, blue: 0.55)
        case "skill": return Color(red: 0.36, green: 0.39, blue: 0.43)
        default: return .acruxTextSecondary
        }
    }
}
