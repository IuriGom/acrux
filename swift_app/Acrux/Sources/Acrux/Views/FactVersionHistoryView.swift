import SwiftUI

struct FactVersionHistoryView: View {
    let factId: String
    @State private var versions: [FactVersion] = []
    @State private var isLoading = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Version history")
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

            if isLoading {
                ProgressView()
                    .padding()
            } else if versions.isEmpty {
                ContentUnavailableView("No versions", systemImage: "clock.arrow.circlepath", description: Text("This fact has no saved versions."))
            } else {
                List(versions) { version in
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text(version.editedBy?.capitalized ?? "Edit")
                                .font(.caption.weight(.semibold))
                            Spacer()
                            Text(version.editedAt, style: .date)
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                        Text(version.content)
                            .font(.system(size: 13))
                        TagChips(tags: version.tags ?? [])
                        HStack {
                            Spacer()
                            Button("Restore") {
                                Task { await restore(version) }
                            }
                            .buttonStyle(GraphitePrimaryButtonStyle())
                        }
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
        .frame(minWidth: 360, minHeight: 400)
        .task { await load() }
    }

    private func load() async {
        guard let service = AcruxServiceReference.shared else { return }
        isLoading = true
        versions = await service.fetchFactVersions(id: factId)
        isLoading = false
    }

    private func restore(_ version: FactVersion) async {
        guard let service = AcruxServiceReference.shared else { return }
        if await service.restoreFactVersion(factId: factId, versionId: version.id) {
            await load()
        }
    }
}
