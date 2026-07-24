import SwiftUI

struct ChatWorkspaceView: View {
    let layout: ChatLayout
    let visibleChatIds: [UUID]
    @Binding var activeChatId: UUID?
    @EnvironmentObject var chatStore: ChatStore

    var body: some View {
        switch layout {
        case .single:
            singlePane
        case .dual:
            dualPane
        case .quad:
            quadPane
        }
    }

    @ViewBuilder
    private var singlePane: some View {
        if let id = activeChatId ?? visibleChatIds.first,
           let chat = chatStore.chat(id: id) {
            ChatView(chat: chat)
                .transition(.asymmetric(
                    insertion: .opacity.combined(with: .scale(scale: 0.96)),
                    removal: .opacity
                ))
        } else {
            emptyPane
        }
    }

    @ViewBuilder
    private var dualPane: some View {
        let ids = Array(visibleChatIds.prefix(2))
        HStack(spacing: 1) {
            ForEach(ids, id: \.self) { id in
                if let chat = chatStore.chat(id: id) {
                    ChatView(chat: chat)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .overlay(activeBorder(id: id))
                } else {
                    emptyPane
                }
            }
        }
        .background(Color.acruxSubtleBorder.opacity(0.5))
        .transition(.asymmetric(
            insertion: .opacity.combined(with: .scale(scale: 0.96)),
            removal: .opacity
        ))
    }

    @ViewBuilder
    private var quadPane: some View {
        let ids = Array(visibleChatIds.prefix(4))
        VStack(spacing: 1) {
            HStack(spacing: 1) {
                pane(for: ids[safe: 0])
                pane(for: ids[safe: 1])
            }
            HStack(spacing: 1) {
                pane(for: ids[safe: 2])
                pane(for: ids[safe: 3])
            }
        }
        .background(Color.acruxSubtleBorder.opacity(0.5))
        .transition(.asymmetric(
            insertion: .opacity.combined(with: .scale(scale: 0.96)),
            removal: .opacity
        ))
    }

    @ViewBuilder
    private func pane(for id: UUID?) -> some View {
        if let id, let chat = chatStore.chat(id: id) {
            ChatView(chat: chat)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .overlay(activeBorder(id: id))
        } else {
            emptyPane
        }
    }

    @ViewBuilder
    private var emptyPane: some View {
        ContentUnavailableView {
            Label("No chat", systemImage: "bubble.left")
        } description: {
            Text("Open a chat to see it here.")
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.acruxBg)
    }

    private func activeBorder(id: UUID) -> some View {
        RoundedRectangle(cornerRadius: 0)
            .stroke(activeChatId == id ? Color.acruxAccent : Color.clear, lineWidth: 2)
            .animation(Theme.easeQuick, value: activeChatId)
    }
}

private extension Array {
    subscript(safe index: Int) -> Element? {
        indices.contains(index) ? self[index] : nil
    }
}
