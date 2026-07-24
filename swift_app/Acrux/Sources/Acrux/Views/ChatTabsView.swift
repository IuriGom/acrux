import SwiftUI

struct ChatTabsView: View {
    @EnvironmentObject var chatStore: ChatStore
    @Binding var activeChatId: UUID?
    var openChats: [Chat]
    var visibleChatIds: [UUID]
    var layout: ChatLayout
    var onClose: (Chat) -> Void
    var onLayoutChange: (ChatLayout) -> Void
    var onToggleVisible: (UUID) -> Void
    @Namespace private var tabNamespace

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 0) {
                ForEach(openChats) { chat in
                    tab(for: chat)
                        .transition(.opacity.combined(with: .move(edge: .leading)))
                }
            }
            .animation(Theme.springSnappy, value: openChats.count)
        }
        .frame(height: 40)
        .background(Color.acruxSidebar)
        .overlay(
            Rectangle()
                .frame(height: 1)
                .foregroundColor(Color.acruxSubtleBorder.opacity(0.5))
            , alignment: .bottom
        )
    }

    private func tab(for chat: Chat) -> some View {
        let isActive = activeChatId == chat.id
        let isVisible = visibleChatIds.contains(chat.id)
        return HStack(spacing: 0) {
            Text(chat.title)
                .font(.system(size: 12, weight: isActive ? .semibold : .medium))
                .lineLimit(1)
                .frame(maxWidth: 180, alignment: .leading)
                .contentShape(Rectangle())
                .onTapGesture {
                    withAnimation(Theme.springSnappy) {
                        activeChatId = chat.id
                    }
                }
                .padding(.leading, 12)

            Button {
                onClose(chat)
            } label: {
                Image(systemName: "xmark")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(isActive ? .primary : Color.acruxTextTertiary)
                    .frame(width: 24, height: 24)
            }
            .buttonStyle(AnimatedIconButtonStyle())
            .padding(.trailing, 4)
        }
        .frame(height: 39)
        .background(isActive ? Color.acruxBg : Color.clear)
        .foregroundStyle(isActive ? .primary : Color.acruxTextSecondary)
        .overlay(alignment: .bottom) {
            if isActive {
                Rectangle()
                    .frame(height: 2)
                    .foregroundColor(.acruxAccent)
                    .matchedGeometryEffect(id: "active-chat-tab", in: tabNamespace)
            }
        }
        .overlay(
            Rectangle()
                .frame(width: 1)
                .foregroundColor(Color.acruxSubtleBorder.opacity(0.5))
            , alignment: .trailing
        )
        .contextMenu {
            Button {
                activeChatId = chat.id
                onLayoutChange(.single)
            } label: {
                Label("Focus", systemImage: "arrow.up.left.and.arrow.down.right")
            }

            Button {
                onToggleVisible(chat.id)
            } label: {
                Label(isVisible ? "Remove from split" : "Add to split", systemImage: isVisible ? "rectangle.split.1x2" : "rectangle.split.2x2")
            }

            Divider()

            ForEach(ChatLayout.allCases, id: \.self) { mode in
                Button {
                    onLayoutChange(mode)
                } label: {
                    Label(mode.menuTitle, systemImage: layout == mode ? "checkmark" : "square")
                }
            }
        }
    }
}
