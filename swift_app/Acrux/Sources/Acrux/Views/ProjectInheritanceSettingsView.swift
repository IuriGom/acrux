import SwiftUI

struct ProjectInheritanceSettingsView: View {
    let project: String
    @State private var layers: [InheritanceLayer] = []
    @State private var baseProject = ""
    @State private var isLoading = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Inheritance")
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
                TextField("Base project", text: $baseProject)
                    .textFieldStyle(.plain)
                    .padding(8)
                    .background(.ultraThinMaterial)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                Button("Inherit") {
                    Task { await add() }
                }
                .buttonStyle(GraphitePrimaryButtonStyle())
                .disabled(baseProject.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
            .padding()

            if isLoading {
                ProgressView()
                    .padding()
            } else if layers.isEmpty {
                ContentUnavailableView("No layers", systemImage: "square.stack.3d.down.forward", description: Text("This project does not inherit from any base layer."))
            } else {
                List(layers) { layer in
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(layer.baseProject)
                                .font(.system(size: 14, weight: .semibold))
                            Text("Order: \(layer.layerOrder)")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        Button(role: .destructive) {
                            Task { await remove(layer) }
                        } label: {
                            Image(systemName: "trash")
                        }
                        .buttonStyle(.plain)
                        .foregroundStyle(.red)
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
        .frame(minWidth: 360, minHeight: 300)
        .task { await load() }
    }

    private func load() async {
        guard let service = AcruxServiceReference.shared else { return }
        isLoading = true
        layers = await service.fetchInheritance(project: project)
        isLoading = false
    }

    private func add() async {
        guard let service = AcruxServiceReference.shared else { return }
        let base = baseProject.trimmingCharacters(in: .whitespacesAndNewlines)
        if await service.addInheritance(project: project, baseProject: base) {
            baseProject = ""
            await load()
        }
    }

    private func remove(_ layer: InheritanceLayer) async {
        guard let service = AcruxServiceReference.shared else { return }
        if await service.removeInheritance(project: project, baseProject: layer.baseProject) {
            await load()
        }
    }
}
