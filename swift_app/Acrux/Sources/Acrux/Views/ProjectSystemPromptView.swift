import SwiftUI

struct ProjectSystemPromptView: View {
    let project: String
    @Environment(\.dismiss) private var dismiss
    @State private var promptText = ""
    @State private var isLoading = false
    @State private var saved = false
    @State private var errorMessage: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("System prompt")
                    .font(.system(size: 18, weight: .bold))

                Spacer()

                if isLoading {
                    ProgressView()
                        .controlSize(.small)
                }

                Button {
                    Task { await load() }
                } label: {
                    Image(systemName: "arrow.clockwise")
                }
                .buttonStyle(GraphiteButtonStyle())
                .disabled(isLoading)
                .help("Reload from Acrux")

                Button {
                    Task { await save() }
                } label: {
                    Label("Save", systemImage: "checkmark")
                }
                .buttonStyle(GraphitePrimaryButtonStyle())
                .disabled(isLoading)

                Button {
                    dismiss()
                } label: {
                    Image(systemName: "xmark")
                }
                .buttonStyle(GraphiteButtonStyle())
                .help("Close")
            }
            .padding()

            TextEditor(text: $promptText)
                .font(.system(size: 13))
                .scrollContentBackground(.hidden)
                .padding(10)
                .background(.ultraThinMaterial)
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .padding()

            if let errorMessage = errorMessage {
                HStack {
                    Image(systemName: "exclamationmark.triangle")
                        .foregroundStyle(.red)
                    Text(errorMessage)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Spacer()
                }
                .padding(.horizontal)
            }

            if saved {
                HStack {
                    Image(systemName: "checkmark.circle")
                        .foregroundStyle(.green)
                    Text("Saved")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Spacer()
                }
                .padding(.horizontal)
            }

            Spacer()
        }
        .frame(minWidth: 500, minHeight: 360)
        .task { await load() }
    }

    private func load() async {
        isLoading = true
        errorMessage = nil
        saved = false
        defer { isLoading = false }

        guard let service = AcruxServiceReference.shared else {
            errorMessage = "Acrux service not available."
            return
        }

        if let prompt = await service.fetchSystemPrompt(project: project) {
            promptText = prompt.promptText
        } else {
            // No existing prompt is fine; start empty.
            promptText = ""
        }
    }

    private func save() async {
        isLoading = true
        errorMessage = nil
        saved = false
        defer { isLoading = false }

        guard let service = AcruxServiceReference.shared else {
            errorMessage = "Acrux service not available."
            return
        }

        let ok = await service.updateSystemPrompt(project: project, promptText: promptText)
        if ok {
            saved = true
            dismiss()
        } else {
            errorMessage = "Failed to save system prompt."
        }
    }
}
