import SwiftUI

struct DependencyGraphView: View {
    let project: String
    @State private var dependencies: [Dependency] = []
    @State private var filter = ""
    @State private var isLoading = false

    private var filtered: [Dependency] {
        let q = filter.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        if q.isEmpty { return dependencies }
        return dependencies.filter {
            $0.sourceRef.lowercased().contains(q) || $0.targetRef.lowercased().contains(q)
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Dependencies")
                    .font(.system(size: 18, weight: .bold))
                Spacer()
                HStack {
                    Image(systemName: "magnifyingglass")
                        .foregroundStyle(.secondary)
                    TextField("Filter…", text: $filter)
                        .textFieldStyle(.plain)
                        .frame(width: 160)
                }
                .padding(8)
                .background(.ultraThinMaterial)
                .clipShape(RoundedRectangle(cornerRadius: 10))
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
            } else if filtered.isEmpty {
                ContentUnavailableView("No dependencies", systemImage: "arrow.triangle.branch", description: Text("No recorded dependencies for this project."))
            } else {
                List(filtered) { dep in
                    HStack(spacing: 12) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(dep.sourceRef)
                                .font(.system(size: 13, weight: .semibold))
                            Text("\(dep.sourceType) → \(dep.targetType)")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        Text(dep.dependencyType)
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(Color.acruxAccent)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(Color.acruxAccent.opacity(0.12))
                            .clipShape(Capsule())
                        VStack(alignment: .trailing, spacing: 2) {
                            Text(dep.targetRef)
                                .font(.system(size: 13))
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
        .frame(minWidth: 500, minHeight: 400)
        .task { await load() }
    }

    private func load() async {
        guard let service = AcruxServiceReference.shared else { return }
        isLoading = true
        dependencies = await service.fetchDependencies(project: project)
        isLoading = false
    }
}
