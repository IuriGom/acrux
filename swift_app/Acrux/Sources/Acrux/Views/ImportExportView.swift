import SwiftUI

struct ImportExportView: View {
    @State private var importPath = ""
    @State private var exportProject = ""
    @State private var isImporting = false
    @State private var isExporting = false
    @State private var message: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            Text("Import / Export")
                .font(.system(size: 24, weight: .bold))

            VStack(alignment: .leading, spacing: 12) {
                Text("Import")
                    .font(.system(size: 16, weight: .semibold))
                HStack {
                    Text(importPath.isEmpty ? "No folder selected" : importPath)
                        .lineLimit(1)
                    Spacer()
                    Button("Choose folder") {
                        if let path = WorkspacePicker.pick() {
                            importPath = path
                        }
                    }
                    .buttonStyle(GraphiteButtonStyle())
                }
                .padding()
                .background(.ultraThinMaterial)
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .graphiteHoverRow()

                HStack(spacing: 12) {
                    Button("Import from Notion") {
                        Task { await importNotion() }
                    }
                    .buttonStyle(AcruxButtonStyle())
                    .disabled(importPath.isEmpty || isImporting)

                    Button("Import from Obsidian") {
                        Task { await importObsidian() }
                    }
                    .buttonStyle(AcruxButtonStyle())
                    .disabled(importPath.isEmpty || isImporting)
                }
            }

            VStack(alignment: .leading, spacing: 12) {
                Text("Export Markdown wiki")
                    .font(.system(size: 16, weight: .semibold))
                HStack {
                    TextField("Project (optional)", text: $exportProject)
                        .textFieldStyle(.plain)
                        .padding(8)
                        .background(.ultraThinMaterial)
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                    Button("Export") {
                        Task { await exportMarkdown() }
                    }
                    .buttonStyle(AcruxButtonStyle())
                    .disabled(isExporting)
                }
                .graphiteHoverRow()
            }

            if let message {
                HStack {
                    Image(systemName: message.contains("failed") || message.contains("Could") ? "exclamationmark.triangle" : "checkmark.circle")
                        .foregroundStyle(message.contains("failed") || message.contains("Could") ? .yellow : .green)
                        .contentTransition(.symbolEffect(.replace))
                    Text(message)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Spacer()
                }
                .padding()
                .background(.ultraThinMaterial)
                .clipShape(RoundedRectangle(cornerRadius: 10))
                .graphiteHoverRow()
                .transition(.graphiteAppear)
            }

            Spacer()
        }
        .padding(40)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.acruxBg)
    }

    private func importNotion() async {
        guard let service = AcruxServiceReference.shared else { return }
        isImporting = true
        message = await service.importNotion(path: importPath) ? "Notion import started." : "Notion import failed."
        isImporting = false
    }

    private func importObsidian() async {
        guard let service = AcruxServiceReference.shared else { return }
        isImporting = true
        message = await service.importObsidian(path: importPath) ? "Obsidian import started." : "Obsidian import failed."
        isImporting = false
    }

    private func exportMarkdown() async {
        guard let service = AcruxServiceReference.shared else { return }
        isExporting = true
        if let data = await service.exportMarkdown(project: exportProject) {
            let panel = NSSavePanel()
            panel.title = "Export Markdown wiki"
            panel.nameFieldStringValue = exportProject.isEmpty ? "acrux-wiki.md" : "\(exportProject)-wiki.md"
            panel.allowedContentTypes = [.plainText]
            if panel.runModal() == .OK, let url = panel.url {
                try? data.write(to: url)
                message = "Exported to \(url.lastPathComponent)."
            } else {
                message = "Export cancelled."
            }
        } else {
            message = "Export failed."
        }
        isExporting = false
    }
}
