import SwiftUI

struct RollbackSuggestionView: View {
    let project: String
    @State private var afterCommand = ""
    @State private var suggestion: RollbackSuggestion?
    @State private var isLoading = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Rollback suggestion")
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

            HStack(spacing: 10) {
                TextField("After command (optional)", text: $afterCommand)
                    .textFieldStyle(.plain)
                    .padding(8)
                    .background(.ultraThinMaterial)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                Button("Suggest") {
                    Task { await load() }
                }
                .buttonStyle(GraphitePrimaryButtonStyle())
            }
            .padding()

            if isLoading {
                ProgressView()
                    .padding()
            } else if let suggestion {
                VStack(alignment: .leading, spacing: 12) {
                    if let desc = suggestion.description {
                        Text(desc)
                            .font(.system(size: 14))
                    }
                    if let command = suggestion.command {
                        HStack {
                            Text(command)
                                .font(.system(size: 12, design: .monospaced))
                                .padding(10)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(Color.acruxCodeBackground)
                                .clipShape(RoundedRectangle(cornerRadius: 8))
                            Button {
                                copy(command)
                            } label: {
                                Image(systemName: "doc.on.doc")
                            }
                            .buttonStyle(.plain)
                            .foregroundStyle(.secondary)
                        }
                    }
                    if let files = suggestion.filesToRevert, !files.isEmpty {
                        Text("Files to revert:")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.secondary)
                        ForEach(files, id: \.self) { file in
                            Text(file)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
                .padding()
            } else {
                ContentUnavailableView("No suggestion", systemImage: "arrow.uturn.backward", description: Text("No rollback suggestion available."))
            }

            Spacer()
        }
        .frame(minWidth: 420, minHeight: 300)
        .task { await load() }
    }

    private func load() async {
        guard let service = AcruxServiceReference.shared else { return }
        isLoading = true
        let cmd = afterCommand.isEmpty ? nil : afterCommand
        suggestion = await service.fetchRollbackSuggestion(project: project, afterCommand: cmd)
        isLoading = false
    }

    private func copy(_ text: String) {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(text, forType: .string)
    }
}
