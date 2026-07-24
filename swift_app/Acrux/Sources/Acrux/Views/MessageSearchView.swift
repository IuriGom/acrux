import SwiftUI

struct MessageSearchView: View {
    @EnvironmentObject var chatStore: ChatStore
    @Binding var isPresented: Bool
    @State private var query = ""

    private var results: [(chat: Chat, message: Message)] {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !q.isEmpty else { return [] }
        var out: [(Chat, Message)] = []
        for chat in chatStore.chats {
            for message in chat.messages {
                if message.content.lowercased().contains(q) {
                    out.append((chat, message))
                }
            }
        }
        return out
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.secondary)
                TextField("Search messages…", text: $query)
                    .textFieldStyle(.plain)
                Button {
                    isPresented = false
                } label: {
                    Image(systemName: "xmark")
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding()
            .background(.ultraThinMaterial)

            if results.isEmpty {
                ContentUnavailableView {
                    Label("No messages", systemImage: "magnifyingglass")
                } description: {
                    Text(query.isEmpty ? "Type to search chat history." : "No matches found.")
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                List(results, id: \.message.id) { chat, message in
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Text(chat.title)
                                .font(.system(size: 12, weight: .semibold))
                            Spacer()
                            Text(message.timestamp, style: .date)
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                        Text(message.content)
                            .font(.system(size: 13))
                            .lineLimit(4)
                    }
                    .padding(8)
                    .background(.ultraThinMaterial)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                    .listRowBackground(Color.clear)
                    .listRowSeparator(.hidden)
                }
                .scrollContentBackground(.hidden)
            }
        }
        .frame(minWidth: 500, minHeight: 400)
    }
}
