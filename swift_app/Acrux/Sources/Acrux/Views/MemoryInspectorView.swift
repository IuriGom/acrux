import SwiftUI

enum MemorySection: String, CaseIterable, Identifiable {
    case facts = "Facts"
    case episodes = "Episodes"
    case skills = "Skills"

    var id: String { rawValue }
    var icon: String {
        switch self {
        case .facts: return "lightbulb"
        case .episodes: return "clock.arrow.circlepath"
        case .skills: return "wrench.adjustable"
        }
    }
}

struct MemoryInspectorView: View {
    @EnvironmentObject var acrux: AcruxService

    @State private var searchQuery = ""
    @State private var tagFilter = ""
    @State private var selectedSection: MemorySection = .facts
    @State private var facts: [MemoryItem] = []
    @State private var episodes: [MemoryItem] = []
    @State private var skills: [MemoryItem] = []
    @State private var clusters: [Cluster] = []
    @State private var selectedClusterId: String? = nil
    @State private var selectedFactType: String? = nil
    @State private var isLoading = false
    @State private var errorMessage: String?

    @State private var selectedFact: MemoryItem?
    @State private var selectedEpisode: MemoryItem?
    @State private var treeRootId: String?
    @State private var treeProject: String = "global"
    @State private var showTree = false
    @State private var showVersions = false
    @State private var showTimeline = false
    @State private var showFileSummaries = false
    @State private var showReviews = false
    @State private var showTests = false
    @State private var showDependencies = false
    @State private var showReplay = false

    @FocusState private var searchFocused: Bool

    @State private var appeared = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            header
                .opacity(appeared ? 1 : 0)
                .offset(y: appeared ? 0 : 16)
            searchBar
                .opacity(appeared ? 1 : 0)
                .offset(y: appeared ? 0 : 16)
            sectionPicker
                .opacity(appeared ? 1 : 0)
                .offset(y: appeared ? 0 : 16)
            timelineStrip
            content
                .id(selectedSection)
                .animation(.spring(response: 0.55, dampingFraction: 0.8), value: selectedSection)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.acruxBg)
        .animation(Theme.springEntrance, value: appeared)
        .task {
            await load()
        }
        .onAppear {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
                appeared = true
            }
        }
        .onChange(of: selectedSection) { _, _ in
            Task { await load() }
        }
        .onChange(of: selectedClusterId) { _, _ in
            Task { await load() }
        }
        .onChange(of: selectedFactType) { _, _ in
            Task { await load() }
        }
        .onReceive(NotificationCenter.default.publisher(for: .focusMemorySearch)) { _ in
            focusSearch()
        }
        .onAppear { applyPendingFactTree() }
        .onChange(of: acrux.pendingFactTree) { _, _ in applyPendingFactTree() }
        .alert("Error", isPresented: .constant(errorMessage != nil), presenting: errorMessage) { _ in
            Button("OK") { errorMessage = nil }
        } message: { message in
            Text(message)
        }
        .dismissablePopup(isPresented: $showTree, onDismiss: { treeRootId = nil }) {
            if let rootId = treeRootId ?? selectedFact?.id {
                MemoryTreeView(rootId: rootId, project: treeProject)
            }
        }
        .dismissablePopup(isPresented: $showVersions) {
            if let fact = selectedFact {
                FactVersionHistoryView(factId: fact.id)
            }
        }
        .dismissablePopup(isPresented: $showTimeline) {
            MemoryTimelineView(project: "")
        }
        .dismissablePopup(isPresented: $showFileSummaries) {
            FileSummaryListView(project: "")
        }
        .dismissablePopup(isPresented: $showReviews) {
            CodeReviewView(project: "")
        }
        .dismissablePopup(isPresented: $showTests) {
            TestResultsView(project: "")
        }
        .dismissablePopup(isPresented: $showDependencies) {
            DependencyGraphView(project: "")
        }
        .dismissablePopup(isPresented: $showReplay) {
            if let episode = selectedEpisode {
                EpisodeReplayView(sessionId: episode.id, workspace: nil)
            }
        }
    }

    private var header: some View {
        HStack {
            Text("Memory")
                .font(.system(size: 32, weight: .bold))
            Spacer()
            HStack(spacing: 8) {
                Button {
                    showTimeline = true
                } label: {
                    Label("Timeline", systemImage: "timeline.selection")
                }
                .buttonStyle(ElasticButtonStyle())
                Button {
                    showFileSummaries = true
                } label: {
                    Label("Files", systemImage: "doc.text")
                }
                .buttonStyle(WiggleButtonStyle())
                Button {
                    showReviews = true
                } label: {
                    Label("Reviews", systemImage: "checkmark.bubble")
                }
                .buttonStyle(FlipButtonStyle())
                Button {
                    showTests = true
                } label: {
                    Label("Tests", systemImage: "checkmark.seal")
                }
                .buttonStyle(GraphitePrimaryButtonStyle())
                Button {
                    showDependencies = true
                } label: {
                    Label("Deps", systemImage: "arrow.triangle.branch")
                }
                .buttonStyle(GraphiteButtonStyle())
                Button {
                    Task { await load() }
                } label: {
                    Image(systemName: "arrow.clockwise")
                        .font(.system(size: 16))
                }
                .buttonStyle(SpinIconButtonStyle())
            }
        }
        .padding(40)
        .padding(.bottom, 0)
    }

    private var searchBar: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 10) {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.secondary)
                TextField("Search memory…", text: $searchQuery)
                    .textFieldStyle(.plain)
                    .focused($searchFocused)
                if isLoading {
                    ProgressView()
                        .controlSize(.small)
                }
                Button("Search") {
                    Task { await load() }
                }
                .buttonStyle(GraphiteButtonStyle())
            }
            .padding()
            .background(.ultraThinMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 12))

            HStack(spacing: 16) {
                HStack(spacing: 8) {
                    Image(systemName: "tag")
                        .foregroundStyle(.secondary)
                    TextField("Filter by tags (comma separated)", text: $tagFilter)
                        .textFieldStyle(.plain)
                        .frame(minWidth: 180)
                }

                if selectedSection == .facts {
                    HStack(spacing: 8) {
                        Text("Type")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(.secondary)
                        Picker("Type", selection: $selectedFactType) {
                            Text("Any").tag(nil as String?)
                            Text("Positive").tag("positive" as String?)
                            Text("Negative").tag("negative" as String?)
                        }
                        .pickerStyle(.segmented)
                        .labelsHidden()
                        .frame(minWidth: 180, idealWidth: 220)
                    }

                    HStack(spacing: 8) {
                        Text("Cluster")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(.secondary)
                        Picker("Cluster", selection: $selectedClusterId) {
                            Text("Any").tag(nil as String?)
                            ForEach(clusters) { cluster in
                                Text(cluster.label ?? "Cluster \(cluster.id)").tag(cluster.id as String?)
                            }
                        }
                        .pickerStyle(.menu)
                        .labelsHidden()
                        .frame(minWidth: 120, idealWidth: 160)
                    }
                }

                Spacer(minLength: 0)
            }
            .padding()
            .background(.ultraThinMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 12))
        }
        .padding(.horizontal, 40)
        .padding(.top, 16)
    }

    private var sectionPicker: some View {
        HStack(spacing: 4) {
            ForEach(MemorySection.allCases) { section in
                let selected = selectedSection == section
                Button {
                    withAnimation(Theme.springSnappy) {
                        selectedSection = section
                    }
                } label: {
                    HStack(spacing: 6) {
                        Image(systemName: section.icon)
                            .symbolEffect(.variableColor, value: selected)
                        Text(section.rawValue)
                            .font(.system(size: 13, weight: selected ? .bold : .medium))
                    }
                    .foregroundStyle(selected ? .primary : Color.acruxTextSecondary)
                    .padding(.vertical, 8)
                    .padding(.horizontal, 14)
                    .background(
                        RoundedRectangle(cornerRadius: 10)
                            .fill(selected ? Color.acruxActive : Color.clear)
                            .shadow(color: selected ? .black.opacity(0.25) : .clear, radius: 6, y: 2)
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 10)
                            .stroke(selected ? Color.acruxAccent.opacity(0.5) : Color.clear, lineWidth: 1.5)
                    )
                }
                .buttonStyle(.plain)
            }
        }
        .padding(4)
        .background(Color.acruxElevated)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .padding(.horizontal, 40)
        .padding(.top, 16)
    }

    @ViewBuilder
    private var timelineStrip: some View {
        if selectedSection == .facts {
            TimelineStripView(project: "")
        }
    }

    @ViewBuilder
    private var content: some View {
        let items = itemsForSelectedSection
        if items.isEmpty && !isLoading {
            ContentUnavailableView {
                Label("No \(selectedSection.rawValue.lowercased())", systemImage: selectedSection.icon)
            } description: {
                Text("Try adjusting your search or tag filters.")
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .transition(.opacity.combined(with: .offset(y: 24)).combined(with: .scale(scale: 0.95)))
        } else if isLoading {
            ScrollView(showsIndicators: false) {
                LazyVStack(spacing: 10) {
                    ForEach(0..<6, id: \.self) { _ in
                        SkeletonRow()
                    }
                }
                .padding(.horizontal, 20)
                .padding(.top, 8)
            }
            .scrollContentBackground(.hidden)
            .transition(.opacity)
        } else {
            ScrollView(showsIndicators: false) {
                LazyVStack(spacing: 10) {
                    ForEach(items) { item in
                        MemoryRow(
                            item: item,
                            section: selectedSection,
                            onDelete: {
                                Task { await delete(item: item) }
                            },
                            onUpdate: { updated in
                                Task { await updateFact(updated) }
                            },
                            onShowTree: {
                                selectedFact = item
                                treeProject = "global"
                                showTree = true
                            },
                            onShowVersions: {
                                selectedFact = item
                                showVersions = true
                            },
                            onReplay: {
                                selectedEpisode = item
                                showReplay = true
                            }
                        )
                    }
                }
                .padding(.horizontal, 20)
                .padding(.top, 8)
            }
            .scrollContentBackground(.hidden)
            .transition(.opacity)
        }
    }

    private var itemsForSelectedSection: [MemoryItem] {
        switch selectedSection {
        case .facts: return facts
        case .episodes: return episodes
        case .skills: return skills
        }
    }

    private func applyPendingFactTree() {
        guard let pending = acrux.pendingFactTree, let id = pending["id"] else { return }
        acrux.pendingFactTree = nil
        treeRootId = id
        treeProject = pending["project"] ?? "global"
        showTree = true
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        let tags = parseTags(tagFilter)
        do {
            switch selectedSection {
            case .facts:
                facts = try await acrux.fetchMemories(
                    endpoint: "facts",
                    query: searchQuery,
                    tags: tags,
                    factType: selectedFactType,
                    clusterId: selectedClusterId,
                    since: nil,
                    until: nil
                )
                clusters = await acrux.fetchClusters(project: "global")
            case .episodes:
                episodes = try await acrux.fetchMemories(endpoint: "episodes", query: searchQuery, tags: tags)
            case .skills:
                skills = try await acrux.fetchMemories(endpoint: "skills", query: searchQuery, tags: tags)
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func delete(item: MemoryItem) async {
        let success = await acrux.deleteMemory(id: item.id, endpoint: selectedSection.endpoint)
        if success {
            await load()
        } else {
            errorMessage = "Could not delete item."
        }
    }

    private func updateFact(_ item: MemoryItem) async {
        let success = await acrux.updateFact(id: item.id, content: item.content, tags: item.tags)
        if success {
            await load()
        } else {
            errorMessage = "Could not update fact."
        }
    }

    private func parseTags(_ text: String) -> [String] {
        text.split(separator: ",")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
    }

    func focusSearch() {
        searchFocused = true
    }
}

private extension MemorySection {
    var endpoint: String {
        switch self {
        case .facts: return "facts"
        case .episodes: return "episodes"
        case .skills: return "skills"
        }
    }
}

struct TimelineStripView: View {
    let project: String
    @State private var events: [TimelineEvent] = []

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 10) {
                if events.isEmpty {
                    Text("No recent timeline events")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 40)
                } else {
                    ForEach(events.prefix(10)) { event in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(event.type.uppercased())
                                .font(.system(size: 9, weight: .bold))
                                .foregroundStyle(.secondary)
                            Text(event.content)
                                .font(.system(size: 11))
                                .lineLimit(2)
                                .frame(width: 140, alignment: .leading)
                        }
                        .padding(8)
                        .background(.ultraThinMaterial)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                    }
                }
            }
            .padding(.horizontal, 40)
            .padding(.vertical, 8)
        }
        .task { await load() }
    }

    private func load() async {
        guard let service = AcruxServiceReference.shared else { return }
        let since = Calendar.current.date(byAdding: .day, value: -7, to: Date())
        events = await service.fetchTimeline(project: project, since: since, until: Date())
    }

    init(project: String) {
        self.project = project
    }
}

struct FileSummaryListView: View {
    let project: String
    @State private var summaries: [FileSummary] = []
    @State private var newPath = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("File summaries")
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
                TextField("File path to summarize", text: $newPath)
                    .textFieldStyle(.plain)
                    .padding(8)
                    .background(.ultraThinMaterial)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                Button("Summarize") {
                    Task { await summarize() }
                }
                .buttonStyle(GraphitePrimaryButtonStyle())
                .disabled(newPath.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
            .padding()

            if summaries.isEmpty {
                ContentUnavailableView("No summaries", systemImage: "doc.text", description: Text("No file summaries indexed yet."))
            } else {
                List(summaries) { summary in
                    VStack(alignment: .leading, spacing: 6) {
                        Text(summary.path)
                            .font(.system(size: 13, weight: .semibold))
                        Text(summary.summary)
                            .font(.system(size: 12))
                            .foregroundStyle(.secondary)
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
        summaries = await service.fetchFileSummaries(project: project)
    }

    private func summarize() async {
        guard let service = AcruxServiceReference.shared else { return }
        let path = newPath.trimmingCharacters(in: .whitespacesAndNewlines)
        if await service.summarizeFile(project: project, path: path) {
            newPath = ""
            await load()
        }
    }
}

struct MemoryRow: View {
    let item: MemoryItem
    let section: MemorySection
    let onDelete: () -> Void
    let onUpdate: (MemoryItem) -> Void
    let onShowTree: () -> Void
    let onShowVersions: () -> Void
    let onReplay: () -> Void

    @State private var isEditing = false
    @State private var editedContent = ""
    @State private var editedTags = ""
    @State private var showDeleteConfirmation = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                ConfidenceBadge(confidence: item.confidence, stale: item.stale)
                if item.isNegative {
                    Text("NEGATIVE")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundStyle(.red)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.red.opacity(0.12))
                        .clipShape(Capsule())
                        .overlay(Capsule().stroke(Color.red.opacity(0.25), lineWidth: 1))
                }
                if let clusterId = item.clusterId {
                    Text("cluster \(clusterId)")
                        .font(.system(size: 9, weight: .semibold))
                        .foregroundStyle(Color.acruxAccent)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.acruxAccent.opacity(0.12))
                        .clipShape(Capsule())
                }
                DecayDot(score: item.decayScore)
                if let gitLabel = item.gitLabel {
                    GitPill(label: gitLabel)
                }
                Spacer()
                if let timestamp = item.timestamp {
                    Text(timestamp, style: .date)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }

            if isEditing && section == .facts {
                VStack(alignment: .leading, spacing: 8) {
                    TextEditor(text: $editedContent)
                        .font(.system(size: 13))
                        .scrollContentBackground(.hidden)
                        .padding(8)
                        .frame(minHeight: 60)
                        .background(.ultraThinMaterial)
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                    TextField("Tags (comma separated)", text: $editedTags)
                        .textFieldStyle(.plain)
                        .padding(8)
                        .background(.ultraThinMaterial)
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                    HStack {
                        Button("Cancel", role: .cancel) {
                            isEditing = false
                        }
                        .buttonStyle(GraphiteButtonStyle())
                        Spacer()
                        Button("Save") {
                            var updated = item
                            updated.content = editedContent
                            updated.tags = editedTags.split(separator: ",").map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty }
                            onUpdate(updated)
                            isEditing = false
                        }
                        .buttonStyle(GraphitePrimaryButtonStyle())
                    }
                }
            } else {
                Text(item.content)
                    .font(.system(size: 13))
                    .lineLimit(nil)

                if let source = item.source, !source.isEmpty {
                    Text("Source: \(source)")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }

                TagChips(tags: item.tags)

                HStack {
                    Spacer()
                    if section == .facts {
                        Button {
                            onShowTree()
                        } label: {
                            Label("Tree", systemImage: "tree")
                                .font(.caption)
                        }
                        .buttonStyle(MemoryActionButtonStyle())
                        .foregroundStyle(.secondary)

                        Button {
                            onShowVersions()
                        } label: {
                            Label("History", systemImage: "clock.arrow.circlepath")
                                .font(.caption)
                        }
                        .buttonStyle(MemoryActionButtonStyle())
                        .foregroundStyle(.secondary)

                        Button {
                            editedContent = item.content
                            editedTags = item.tags.joined(separator: ", ")
                            isEditing = true
                        } label: {
                            Label("Edit", systemImage: "pencil")
                                .font(.caption)
                        }
                        .buttonStyle(MemoryActionButtonStyle())
                        .foregroundStyle(.secondary)
                    }
                    if section == .episodes {
                        Button {
                            onReplay()
                        } label: {
                            Label("Replay", systemImage: "play.circle")
                                .font(.caption)
                        }
                        .buttonStyle(MemoryActionButtonStyle())
                        .foregroundStyle(.secondary)
                    }
                    Button {
                        showDeleteConfirmation = true
                    } label: {
                        Label("Delete", systemImage: "trash")
                            .font(.caption)
                    }
                    .buttonStyle(MemoryActionButtonStyle())
                    .foregroundStyle(.red)
                }
            }
        }
        .padding(12)
        .background(Color.acruxCard)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .drawingGroup()
        .confirmationDialog("Delete this \(section.rawValue.lowercased())?", isPresented: $showDeleteConfirmation, titleVisibility: .visible) {
            Button("Delete", role: .destructive, action: onDelete)
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This action cannot be undone.")
        }
    }
}
