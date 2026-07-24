import SwiftUI
import UniformTypeIdentifiers

struct PastChatsView: View {
    @Binding var selectedTab: SidebarTab
    let onOpenChat: (Chat) -> Void
    @EnvironmentObject var acrux: AcruxService
    @EnvironmentObject var chatStore: ChatStore

    @State private var searchQuery = ""
    @State private var tagFilter = ""
    @State private var searchResults: [MemorySearchResult] = []
    @State private var isSearching = false
    @State private var showSearchResults = false

    @State private var chatToRename: Chat?
    @State private var renameTitle = ""
    @State private var showRenameAlert = false

    @State private var chatToDelete: Chat?
    @State private var showDeleteConfirmation = false

    @State private var importError: String?
    @State private var showImportError = false

    @FocusState private var searchFocused: Bool

    private var sortedChats: [Chat] {
        chatStore.chats.sorted(by: { $0.updatedAt > $1.updatedAt })
    }

    @State private var appeared = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Past Chats")
                    .font(.system(size: 32, weight: .bold))

                Spacer()

                Button {
                    importChat()
                } label: {
                    Image(systemName: "square.and.arrow.down")
                        .font(.system(size: 16))
                }
                .buttonStyle(ElasticButtonStyle())
                .help("Import a chat from JSON")
            }
            .padding(40)
            .padding(.bottom, 0)
            .opacity(appeared ? 1 : 0)
            .offset(y: appeared ? 0 : 16)

            VStack(alignment: .leading, spacing: 10) {
                HStack(spacing: 10) {
                    Image(systemName: "magnifyingglass")
                        .foregroundStyle(.secondary)
                    TextField("Search memory…", text: $searchQuery)
                        .textFieldStyle(.plain)
                        .focused($searchFocused)
                    if isSearching {
                        ProgressView()
                            .controlSize(.small)
                    }
                    Button("Search") {
                        performSearch()
                    }
                    .buttonStyle(WiggleButtonStyle())
                    .disabled(searchQuery.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
                .padding()
                .background(.ultraThinMaterial)
                .clipShape(RoundedRectangle(cornerRadius: 12))

                HStack(spacing: 10) {
                    Image(systemName: "tag")
                        .foregroundStyle(.secondary)
                    TextField("Filter by tags (comma separated)", text: $tagFilter)
                        .textFieldStyle(.plain)
                }
                .padding()
                .background(.ultraThinMaterial)
                .clipShape(RoundedRectangle(cornerRadius: 12))
            }
            .padding(.horizontal, 40)
            .padding(.top, 16)
            .opacity(appeared ? 1 : 0)
            .offset(y: appeared ? 0 : 16)

            if showSearchResults {
                searchResultsView
                    .padding(.horizontal, 40)
                    .padding(.top, 16)
                    .transition(.graphiteAppear)
            }

            if chatStore.chats.isEmpty {
                ContentUnavailableView {
                    Label("No chats yet", systemImage: "bubble.left.and.exclamationmark.bubble.right")
                } description: {
                    Text("Start a new task to begin.")
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                List {
                    ForEach(sortedChats) { chat in
                        ChatRow(
                            chat: chat,
                            onOpen: { onOpenChat(chat) },
                            onRename: {
                                chatToRename = chat
                                renameTitle = chat.title
                                showRenameAlert = true
                            },
                            onDelete: {
                                chatToDelete = chat
                                showDeleteConfirmation = true
                            }
                        )
                        .transition(chatRowTransition)
                    }
                    .onDelete(perform: delete)
                }
                .scrollContentBackground(.hidden)
                .padding(.horizontal, 20)
                .animation(Theme.springSnappy, value: sortedChats.count)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.acruxBg)
        .animation(Theme.springEntrance, value: appeared)
        .onAppear {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
                appeared = true
            }
        }
        .alert("Rename chat", isPresented: $showRenameAlert) {
            TextField("Title", text: $renameTitle)
            Button("Cancel", role: .cancel) {}
            Button("Save") {
                if let chat = chatToRename, !renameTitle.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    var updated = chat
                    updated.title = renameTitle.trimmingCharacters(in: .whitespacesAndNewlines)
                    chatStore.save(updated)
                    if acrux.sessions[updated.id] != nil {
                        acrux.sessions[updated.id]?.chat = updated
                    }
                }
            }
        } message: {
            Text("Enter a new title for this chat.")
        }
        .confirmationDialog("Delete chat?", isPresented: $showDeleteConfirmation, titleVisibility: .visible) {
            Button("Delete", role: .destructive) {
                if let chat = chatToDelete {
                    withAnimation(.spring(response: 0.5, dampingFraction: 0.7)) {
                        chatStore.delete(chat)
                        acrux.closeChat(chat)
                    }
                }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This chat will be permanently removed.")
        }
        .alert("Import failed", isPresented: $showImportError, presenting: importError) { _ in
            Button("OK", role: .cancel) {}
        } message: { error in
            Text(error)
        }
    }

    private var searchResultsView: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Memory Results")
                    .font(.system(size: 14, weight: .bold))
                Spacer()
                Button {
                    withAnimation {
                        showSearchResults = false
                    }
                } label: {
                    Image(systemName: "xmark")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }

            if isSearching {
                ProgressView()
                    .padding()
            } else if searchResults.isEmpty {
                Text("No results found. The search endpoint may not be implemented yet.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .padding(.vertical, 8)
            } else {
                LazyVStack(alignment: .leading, spacing: 8) {
                    ForEach(searchResults) { result in
                        VStack(alignment: .leading, spacing: 6) {
                            HStack(spacing: 8) {
                                ConfidenceBadge(confidence: result.confidence, stale: result.stale)
                                if let gitLabel = result.gitLabel {
                                    GitPill(label: gitLabel)
                                }
                                Spacer()
                                if let score = result.score {
                                    Text(String(format: "Score: %.3f", score))
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                }
                            }
                            Text(result.content)
                                .font(.system(size: 13))
                            TagChips(tags: result.tags ?? [])
                        }
                        .padding(10)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(.ultraThinMaterial)
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                    }
                }
            }
        }
        .padding()
        .background(Color.acruxSurface)
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }

    private func performSearch() {
        let query = searchQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else { return }
        isSearching = true
        showSearchResults = true
        let tags = tagFilter.split(separator: ",").map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty }
        Task {
            let results = await acrux.searchMemory(query: query, tags: tags)
            await MainActor.run {
                searchResults = results
                isSearching = false
            }
        }
    }

    func focusSearch() {
        searchFocused = true
    }

    private func importChat() {
        let panel = NSOpenPanel()
        panel.title = "Import chat"
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        panel.allowedContentTypes = [.json]

        guard panel.runModal() == .OK, let url = panel.url else { return }
        if let chat = chatStore.importChat(from: url) {
            onOpenChat(chat)
        } else {
            importError = "Could not import chat from \(url.lastPathComponent). Make sure it is a valid Acrux chat JSON."
            showImportError = true
        }
    }

    private func delete(at offsets: IndexSet) {
        withAnimation(.spring(response: 0.55, dampingFraction: 0.72)) {
            for index in offsets {
                let chat = sortedChats[index]
                chatStore.delete(chat)
                acrux.closeChat(chat)
            }
        }
    }
}

private var chatRowTransition: AnyTransition {
    .asymmetric(
        insertion: .opacity.combined(with: .offset(x: -40)).combined(with: .scale(scale: 0.9)),
        removal: .opacity.combined(with: .offset(x: 80)).combined(with: .scale(scale: 0.85))
    )
}

struct ChatRow: View {
    let chat: Chat
    let onOpen: () -> Void
    let onRename: () -> Void
    let onDelete: () -> Void

    var body: some View {
        Button {
            withAnimation(Theme.springEntrance) {
                onOpen()
            }
        } label: {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(chat.title)
                        .font(.system(size: 15, weight: .semibold))
                    Text("\(chat.model) · \(chat.workspace)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
                Spacer()
                Text(chat.updatedAt, style: .date)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            .padding(.vertical, 6)
            .padding(.horizontal, 10)
        }
        .buttonStyle(.plain)
        .graphiteHoverRow()
        .contextMenu {
            Button {
                onRename()
            } label: {
                Label("Rename", systemImage: "pencil")
            }

            Button(role: .destructive) {
                onDelete()
            } label: {
                Label("Delete", systemImage: "trash")
            }
        }
    }
}
