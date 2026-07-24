import SwiftUI

struct WatcherSettingsView: View {
    let project: String
    @State private var status: WatcherStatus?
    @State private var isLoading = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Workspace watcher")
                    .font(.system(size: 18, weight: .bold))
                Spacer()
                Button {
                    Task { await load() }
                } label: {
                    Image(systemName: "arrow.clockwise")
                }
                .buttonStyle(GraphiteButtonStyle())
            }
            .padding()

            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Circle()
                        .fill(status?.running == true ? .green : .red)
                        .frame(width: 10, height: 10)
                    Text(status?.running == true ? "Running" : "Stopped")
                        .font(.system(size: 16, weight: .semibold))
                    Spacer()
                }

                if let paths = status?.watchedPaths, !paths.isEmpty {
                    Text("Watching:")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                    ForEach(paths, id: \.self) { path in
                        Text(path)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                HStack {
                    Button("Start") {
                        Task { await set(running: true) }
                    }
                    .buttonStyle(GraphitePrimaryButtonStyle())
                    .disabled(status?.running == true)

                    Button("Stop") {
                        Task { await set(running: false) }
                    }
                    .buttonStyle(GraphiteButtonStyle())
                    .disabled(status?.running != true)
                }
            }
            .padding()

            Spacer()
        }
        .frame(minWidth: 360, minHeight: 300)
        .task { await load() }
    }

    private func load() async {
        guard let service = AcruxServiceReference.shared else { return }
        isLoading = true
        status = await service.fetchWatcherStatus(project: project)
        isLoading = false
    }

    private func set(running: Bool) async {
        guard let service = AcruxServiceReference.shared else { return }
        _ = await service.setWatcher(project: project, running: running)
        await load()
    }
}
