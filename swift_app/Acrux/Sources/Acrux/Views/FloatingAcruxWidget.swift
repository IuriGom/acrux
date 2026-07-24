import SwiftUI
import AppKit

struct FloatingAcruxWidget: View {
    @State private var query = ""
    @State private var results: [MemorySearchResult] = []
    @State private var newFact = ""

    var body: some View {
        VStack(spacing: 12) {
            HStack {
                Text("Acrux")
                    .font(.system(size: 14, weight: .bold))
                Spacer()
                Button {
                    FloatingPanelController.shared?.close()
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }

            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.secondary)
                TextField("Search memory…", text: $query)
                    .textFieldStyle(.plain)
                    .onSubmit {
                        Task { await search() }
                    }
                Button {
                    Task { await search() }
                } label: {
                    Image(systemName: "arrow.right")
                }
                .buttonStyle(.plain)
                .foregroundStyle(Color.acruxAccent)
            }
            .padding(8)
            .background(.ultraThinMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 10))

            if !results.isEmpty {
                ScrollView {
                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(results.prefix(5)) { result in
                            Text(result.content)
                                .font(.system(size: 12))
                                .lineLimit(3)
                                .padding(8)
                                .background(.ultraThinMaterial)
                                .clipShape(RoundedRectangle(cornerRadius: 8))
                        }
                    }
                }
                .frame(maxHeight: 180)
            }

            HStack {
                TextField("Remember a fact…", text: $newFact)
                    .textFieldStyle(.plain)
                    .padding(8)
                    .background(.ultraThinMaterial)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                Button {
                    Task { await remember() }
                } label: {
                    Image(systemName: "plus")
                }
                .buttonStyle(.plain)
                .foregroundStyle(Color.acruxAccent)
                .disabled(newFact.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
        }
        .padding(14)
        .frame(width: 320)
        .background(Color.acruxCard)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(Color.acruxSubtleBorder, lineWidth: 1)
        )
    }

    private func search() async {
        guard let service = AcruxServiceReference.shared else { return }
        results = await service.searchMemory(query: query)
    }

    private func remember() async {
        guard let service = AcruxServiceReference.shared else { return }
        let content = newFact.trimmingCharacters(in: .whitespacesAndNewlines)
        // Note: backend does not have a direct remember endpoint in this scope; this is a placeholder.
        _ = await service.createChildFact(parentId: "0", content: content)
        newFact = ""
    }
}

final class FloatingPanelController: NSPanel {
    static weak var shared: FloatingPanelController?

    convenience init() {
        let contentViewController = NSHostingController(rootView: FloatingAcruxWidget())
        self.init(contentRect: NSRect(x: 200, y: 200, width: 320, height: 360),
                  styleMask: [.nonactivatingPanel, .titled, .resizable, .closable, .fullSizeContentView],
                  backing: .buffered, defer: false)
        self.contentViewController = contentViewController
        self.titleVisibility = .hidden
        self.titlebarAppearsTransparent = true
        self.isMovableByWindowBackground = true
        self.level = .floating
        self.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        self.backgroundColor = .clear
        self.isOpaque = false
        FloatingPanelController.shared = self
    }
}
