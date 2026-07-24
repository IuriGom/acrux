import SwiftUI
import EventKit

struct MessageRow: View {
    let message: Message
    let chat: Chat?
    let onApprove: (String) -> Void
    let onDeny: (String) -> Void
    let onPin: (() -> Void)?
    let onRunCode: ((String) -> Void)?
    @StateObject private var eventKit = EventKitManager()
    @State private var showRollback = false

    init(message: Message, chat: Chat? = nil, onApprove: @escaping (String) -> Void, onDeny: @escaping (String) -> Void, onPin: (() -> Void)? = nil, onRunCode: ((String) -> Void)? = nil) {
        self.message = message
        self.chat = chat
        self.onApprove = onApprove
        self.onDeny = onDeny
        self.onPin = onPin
        self.onRunCode = onRunCode
    }

    @State private var showCopyButton = false

    var isUser: Bool { message.role == "user" }

    var body: some View {
        HStack {
            if isUser { Spacer() }

            VStack(alignment: isUser ? .trailing : .leading, spacing: 8) {
                if let checkpoint = message.checkpoint {
                    CheckpointBanner(checkpoint: checkpoint)
                        .transition(.graphiteAppear)
                }

                if let reasoning = message.reasoning, !reasoning.isEmpty {
                    ReasoningView(reasoning: reasoning, isThinking: message.content.isEmpty && !isUser)
                        .transition(.graphiteAppear)
                }

                if let toolCalls = message.toolCalls {
                    ForEach(toolCalls) { toolCall in
                        ToolCallRow(
                            toolCall: toolCall,
                            result: message.toolResults?.first(where: { $0.id == toolCall.id }),
                            chat: chat,
                            onApprove: { onApprove(toolCall.id) },
                            onDeny: { onDeny(toolCall.id) }
                        )
                        .transition(.graphiteAppear)
                    }
                }

                if let diff = message.content.extractDiff() {
                    InlineDiffView(diff: diff, onAccept: {}, onReject: {})
                }

                let blocks = message.content.extractCodeBlocks()
                if !blocks.isEmpty {
                    CodeBlockView(blocks: blocks, onRun: onRunCode)
                }

                let textOnly = message.content.removingCodeBlocks()
                if !textOnly.isEmpty {
                    messageBubble(text: textOnly)
                }

                if let pinned = message.pinned, pinned {
                    HStack {
                        Image(systemName: "pin.fill")
                            .font(.caption2)
                            .foregroundStyle(Color.acruxAccent)
                        Text("Pinned")
                            .font(.caption2)
                            .foregroundStyle(Color.acruxTextSecondary)
                    }
                }
            }
            .frame(maxWidth: 760, alignment: isUser ? .trailing : .leading)

            if !isUser { Spacer() }
        }
        .transition(isUser ? .graphiteUser : .graphiteAppear)
        .alert("Calendar / Reminders", isPresented: $eventKit.showError, presenting: eventKit.lastError) { _ in
            Button("OK", role: .cancel) {}
        } message: { error in
            Text(error)
        }
    }

    private func messageBubble(text: String) -> some View {
        ZStack(alignment: isUser ? .topLeading : .topTrailing) {
            Text(text)
                .font(.system(size: 14))
                .padding(14)
                .background(isUser ? Color.acruxUserBubble : Color.acruxAssistantBubble)
                .foregroundStyle(.primary)
                .clipShape(RoundedRectangle(cornerRadius: 18))
                .contextMenu {
                    Button {
                        copyToClipboard()
                    } label: {
                        Label("Copy", systemImage: "doc.on.doc")
                    }
                    if !isUser {
                        Button {
                            Task { await eventKit.createReminder(title: "Acrux note", notes: message.content) }
                        } label: {
                            Label("Create Reminder", systemImage: "checklist")
                        }
                        Button {
                            Task { await eventKit.createCalendarEvent(title: "Acrux note", notes: message.content) }
                        } label: {
                            Label("Add to Calendar", systemImage: "calendar")
                        }
                        if let onPin {
                            Button {
                                onPin()
                            } label: {
                                Label(message.pinned == true ? "Unpin" : "Pin", systemImage: message.pinned == true ? "pin.slash" : "pin")
                            }
                        }
                    }
                }
                .onHover { hovering in
                    withAnimation(.easeInOut(duration: 0.15)) {
                        showCopyButton = hovering
                    }
                }

            Button {
                copyToClipboard()
            } label: {
                Image(systemName: "doc.on.doc")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(.primary)
                    .padding(6)
                    .background(.ultraThinMaterial)
                    .clipShape(Circle())
                    .shadow(color: .black.opacity(0.35), radius: 6, x: 0, y: 2)
            }
            .buttonStyle(AnimatedIconButtonStyle())
            .offset(x: isUser ? -14 : 14, y: -10)
            .opacity(showCopyButton ? 1 : 0)
            .scaleEffect(showCopyButton ? 1 : 0.6)
            .animation(.spring(response: 0.3, dampingFraction: 0.7), value: showCopyButton)
        }
    }

    private func copyToClipboard() {
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(message.content, forType: .string)
    }
}

struct CheckpointBanner: View {
    @EnvironmentObject var acrux: AcruxService
    let checkpoint: MessageCheckpoint
    @State private var pulsing = false

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "pause.circle.fill")
                .foregroundStyle(Color.acruxAccent)
                .scaleEffect(pulsing ? 1.12 : 1.0)
                .animation(.easeInOut(duration: 0.9).repeatForever(autoreverses: true), value: pulsing)
                .onAppear { pulsing = true }
            VStack(alignment: .leading, spacing: 2) {
                Text("Agent checkpoint")
                    .font(.system(size: 13, weight: .semibold))
                if let tool = checkpoint.toolName {
                    Text("Before: \(tool)")
                        .font(.caption)
                        .foregroundStyle(Color.acruxTextSecondary)
                }
                if let msg = checkpoint.message {
                    Text(msg)
                        .font(.caption)
                        .foregroundStyle(Color.acruxTextSecondary)
                        .lineLimit(2)
                }
            }
            Spacer()
            HStack(spacing: 6) {
                Button("Resume") { acrux.resolveCheckpoint(action: "resume") }
                    .buttonStyle(ToolButtonStyle(color: .green))
                Button("Step") { acrux.resolveCheckpoint(action: "step") }
                    .buttonStyle(ToolButtonStyle(color: .acruxAccent))
                Button("Stop") { acrux.resolveCheckpoint(action: "stop") }
                    .buttonStyle(ToolButtonStyle(color: .red))
            }
        }
        .padding()
        .background(Color.acruxCard)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .shadow(color: .black.opacity(0.3), radius: 8, y: 3)
    }
}

struct ReasoningView: View {
    let reasoning: String
    let isThinking: Bool
    @State private var isExpanded: Bool

    init(reasoning: String, isThinking: Bool) {
        self.reasoning = reasoning
        self.isThinking = isThinking
        _isExpanded = State(initialValue: false)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Button {
                withAnimation(Theme.springSnappy) { isExpanded.toggle() }
            } label: {
                HStack {
                    HStack(spacing: 6) {
                        Text("REASONING")
                            .font(.caption2.weight(.bold))
                            .foregroundStyle(Color.acruxAccent)
                            .shimmer(active: isThinking)
                        if isThinking {
                            ThinkingDots()
                        }
                    }
                    Spacer()
                    Image(systemName: "chevron.down")
                        .font(.caption2)
                        .foregroundStyle(Color.acruxTextSecondary)
                        .rotationEffect(.degrees(isExpanded ? 0 : 180))
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .contentShape(Rectangle())
            }
            .buttonStyle(ElasticButtonStyle())

            if isExpanded {
                Text(reasoning)
                    .font(.system(size: 13))
                    .foregroundStyle(Color.acruxTextSecondary)
                    .lineSpacing(2)
                    .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
        .padding(12)
        .background(Color.acruxReasoningBackground)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}

struct ThinkingDots: View {
    var body: some View {
        PhaseAnimator([0, 1, 2]) { phase in
            HStack(spacing: 3) {
                ForEach(0..<3) { i in
                    Circle()
                        .fill(Color.acruxAccent)
                        .frame(width: 4, height: 4)
                        .opacity(phase == i ? 1.0 : 0.3)
                        .scaleEffect(phase == i ? 1.2 : 0.9)
                }
            }
        } animation: { _ in
            .easeInOut(duration: 0.25)
        }
    }
}

struct ToolCallRow: View {
    let toolCall: ToolCall
    let result: ToolResult?
    let chat: Chat?
    let onApprove: () -> Void
    let onDeny: () -> Void
    @State private var showRollback = false
    @State private var rollbackSuggestion: RollbackSuggestion?
    @State private var hasResponded = false
    @State private var pendingPulse = false

    private var isPending: Bool { result == nil }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(toolCall.name)
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(Color.acruxAccent)
                if isPending && !hasResponded {
                    TypingDots()
                        .transition(.opacity)
                }
                Spacer()
                if isPending {
                    HStack(spacing: 8) {
                        Button("Approve") {
                            withAnimation(Theme.springSnappy) { hasResponded = true }
                            onApprove()
                        }
                        .disabled(hasResponded)
                        .buttonStyle(ToolButtonStyle(color: .green))
                        Button("Deny") {
                            withAnimation(Theme.springSnappy) { hasResponded = true }
                            onDeny()
                        }
                        .disabled(hasResponded)
                        .buttonStyle(ToolButtonStyle(color: .red))
                    }
                    .transition(.opacity)
                }
            }

            Text(formatArguments(toolCall.arguments))
                .font(.system(size: 12, design: .monospaced))
                .foregroundStyle(Color.acruxTextSecondary)
                .padding(8)
                .background(Color.acruxCodeBackground)
                .clipShape(RoundedRectangle(cornerRadius: 8))

            if let result = result {
                Text(result.output)
                    .font(.system(size: 12, design: .monospaced))
                    .foregroundStyle(Color.acruxTextSecondary)
                    .padding(10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color.acruxCodeBackground)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                    .transition(.graphiteAppear)

                if toolCall.name == "run_command" && looksLikeFailure(result.output) {
                    HStack {
                        Spacer()
                        Button("Suggest rollback") {
                            Task { await loadRollback() }
                        }
                        .buttonStyle(ToolButtonStyle(color: .yellow))
                    }
                    if let suggestion = rollbackSuggestion {
                        RollbackMiniSuggestion(suggestion: suggestion)
                    }
                }
            }
        }
        .padding(14)
        .background(Color.acruxCard)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .shadow(color: .black.opacity(0.3), radius: 6, y: 2)
        .opacity(isPending && hasResponded ? 0.85 : 1.0)
        .scaleEffect(isPending && pendingPulse ? 1.005 : 1.0)
        .animation(.easeInOut(duration: 1.2).repeatForever(autoreverses: true), value: pendingPulse)
        .onAppear { if isPending { pendingPulse = true } }
        .onChange(of: isPending) { _, pending in pendingPulse = pending }
        .animation(Theme.springSnappy, value: hasResponded)
    }

    private func looksLikeFailure(_ output: String) -> Bool {
        let lower = output.lowercased()
        return lower.contains("error") || lower.contains("failed") || lower.contains("fatal")
    }

    private func loadRollback() async {
        guard let service = AcruxServiceReference.shared,
              let chat = chat ?? service.activeSession?.chat else { return }
        rollbackSuggestion = await service.fetchRollbackSuggestion(project: chat.workspace, afterCommand: toolCall.arguments["command"]?.value as? String)
    }

    private func formatArguments(_ args: [String: AnyCodable]) -> String {
        let dict = args.mapValues { $0.value }
        guard let data = try? JSONSerialization.data(withJSONObject: dict, options: .prettyPrinted),
              let text = String(data: data, encoding: .utf8) else { return "{}" }
        return text
    }
}

struct RollbackMiniSuggestion: View {
    let suggestion: RollbackSuggestion

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            if let desc = suggestion.description {
                Text(desc)
                    .font(.caption)
            }
            if let command = suggestion.command {
                Text(command)
                    .font(.system(size: 11, design: .monospaced))
                    .padding(8)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color.acruxReasoningBackground)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }
        }
        .padding(8)
        .background(Color.yellow.opacity(0.08))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color.yellow.opacity(0.25), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}

struct ToolButtonStyle: ButtonStyle {
    let color: Color
    @State private var hovering = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 12, weight: .semibold))
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(color.opacity(hovering ? 0.25 : 0.15))
            .foregroundStyle(color)
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .scaleEffect(configuration.isPressed ? 0.94 : (hovering ? 1.04 : 1.0))
            .animation(Theme.springPop, value: configuration.isPressed)
            .animation(Theme.easeQuick, value: hovering)
            .onHover { hovering = $0 }
    }
}
