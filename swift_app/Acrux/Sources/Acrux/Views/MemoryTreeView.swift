import SwiftUI

struct MemoryTreeView: View {
    let rootId: String
    var project: String = "global"
    @State private var root: FactNode?
    @State private var isLoading = false
    @State private var newChildContent = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Fact tree")
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
            } else if let root {
                ScrollView {
                    VStack(alignment: .leading, spacing: 8) {
                        FactNodeRow(node: root, depth: 0)
                    }
                    .padding()
                }
            } else {
                ContentUnavailableView("No tree", systemImage: "tree", description: Text("Could not load fact hierarchy."))
            }

            HStack(spacing: 10) {
                TextField("New child fact…", text: $newChildContent)
                    .textFieldStyle(.plain)
                    .padding(8)
                    .background(.ultraThinMaterial)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                Button("Add child") {
                    Task { await addChild() }
                }
                .buttonStyle(GraphitePrimaryButtonStyle())
                .disabled(newChildContent.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
            .padding()
        }
        .frame(minWidth: 360, minHeight: 400)
        .task { await load() }
    }

    private func load() async {
        guard let service = AcruxServiceReference.shared else { return }
        isLoading = true
        root = await service.fetchFactTree(id: rootId, project: project)
        isLoading = false
    }

    private func addChild() async {
        guard let service = AcruxServiceReference.shared else { return }
        let content = newChildContent.trimmingCharacters(in: .whitespacesAndNewlines)
        guard await service.createChildFact(parentId: rootId, content: content, project: project) else { return }
        newChildContent = ""
        await load()
    }
}

struct FactNodeRow: View {
    let node: FactNode
    let depth: Int
    @State private var expanded = true

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 6) {
                if !node.children.isEmpty {
                    Button {
                        withAnimation { expanded.toggle() }
                    } label: {
                        Image(systemName: expanded ? "chevron.down" : "chevron.right")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundStyle(.secondary)
                    }
                    .buttonStyle(.plain)
                } else {
                    Rectangle()
                        .fill(Color.clear)
                        .frame(width: 14, height: 14)
                }
                Text(node.content)
                    .font(.system(size: 13))
                Spacer()
                if node.factType?.lowercased() == "negative" {
                    Text("NEGATIVE")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundStyle(.red)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.red.opacity(0.12))
                        .clipShape(Capsule())
                }
                DecayDot(score: node.decayScore)
            }
            .padding(.leading, CGFloat(depth * 16))

            if expanded {
                ForEach(node.children) { child in
                    FactNodeRow(node: child, depth: depth + 1)
                }
            }
        }
    }
}

struct DecayDot: View {
    let score: Double?

    var color: Color {
        guard let score else { return .green }
        if score < 0.3 { return .green }
        if score < 0.7 { return .yellow }
        return .red
    }

    var body: some View {
        Circle()
            .fill(color)
            .frame(width: 8, height: 8)
            .help("Decay: \(score.map { String(format: "%.2f", $0) } ?? "—")")
    }
}

@MainActor
final class AcruxServiceReference {
    static weak var shared: AcruxService?
}
