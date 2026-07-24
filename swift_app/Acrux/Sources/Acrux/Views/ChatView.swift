import SwiftUI
import UniformTypeIdentifiers
import AVFoundation

struct ChatView: View {
    let chat: Chat
    @EnvironmentObject var acrux: AcruxService
    @EnvironmentObject var chatStore: ChatStore

    @State private var input = ""
    @State private var autoAccept: Bool
    @State private var useMemory: Bool
    @State private var isConnecting = false
    @State private var skillSuggestion: SkillSuggestion?
    @StateObject private var speech = SpeechSynthesizer()

    init(chat: Chat) {
        self.chat = chat
        _autoAccept = State(initialValue: chat.autoAccept)
        _useMemory = State(initialValue: chat.useMemory)
    }

    private var currentChat: Chat? { chatStore.chat(id: chat.id) }

    private var messages: [Message] {
        currentChat?.messages ?? chat.messages
    }

    private var pinnedMessages: [Message] {
        messages.filter { $0.pinned == true }
    }

    private var unpinnedMessages: [Message] {
        messages.filter { !($0.pinned == true) }
    }

    private var isGenerating: Bool {
        acrux.generatingChatIds.contains(chat.id)
    }

    var body: some View {
        VStack(spacing: 0) {
            ChatHeader(chat: chat, autoAccept: $autoAccept, useMemory: $useMemory, speech: speech)

            if let checkpoint = acrux.sessions[chat.id]?.pendingCheckpoint {
                CheckpointBanner(checkpoint: checkpoint)
            }

            if let suggestion = skillSuggestion {
                SkillSuggestionBanner(suggestion: suggestion, onRun: {
                    runSkillSuggestion(suggestion)
                }, onDismiss: {
                    skillSuggestion = nil
                })
            }

            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 16) {
                        if !pinnedMessages.isEmpty {
                            HStack {
                                Image(systemName: "pin.fill")
                                    .font(.caption2)
                                    .foregroundStyle(Color.acruxAccent)
                                Text("Pinned")
                                    .font(.caption2.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                Spacer()
                            }
                            ForEach(pinnedMessages) { message in
                                messageRow(message: message, proxy: proxy)
                            }
                            Divider()
                                .padding(.vertical, 8)
                        }
                        ForEach(unpinnedMessages) { message in
                            messageRow(message: message, proxy: proxy)
                        }
                        if isGenerating, messages.last?.content.isEmpty ?? true {
                            HStack(spacing: 10) {
                                TypingDots()
                                Text("Thinking")
                                    .font(.caption)
                                    .foregroundStyle(Color.acruxTextTertiary)
                                    .shimmer(active: true)
                                Spacer()
                            }
                            .padding(.leading, 4)
                            .transition(.graphiteAppear)
                        }
                    }
                    .padding()
                    .animation(Theme.springEntrance, value: messages.count)
                    .animation(Theme.springSnappy, value: isGenerating)
                }
                .dropDestination(for: URL.self) { urls, _ in
                    handleDropped(urls)
                    return true
                }
                .onChange(of: messages.count) { _, _ in
                    if let last = messages.last {
                        withAnimation {
                            proxy.scrollTo(last.id, anchor: .bottom)
                        }
                    }
                }
                .onChange(of: messages.last?.id) { _, _ in
                    DispatchQueue.main.async {
                        if let last = messages.last {
                            proxy.scrollTo(last.id, anchor: .bottom)
                        }
                    }
                }
            }

            ChatInputBar(
                input: $input,
                isGenerating: isGenerating,
                onSend: sendMessage,
                onAttach: attachFile,
                onStop: { acrux.stop(chat: chat) }
            )
        }
        .frame(minWidth: 900, minHeight: 600)
        .onAppear {
            acrux.connect(to: chat)
            isConnecting = true
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                isConnecting = false
            }
        }
        .onDisappear {
            if let current = currentChat {
                chatStore.save(current)
            }
            speech.stop()
        }
        .onChange(of: autoAccept) { _, newValue in
            if var current = currentChat {
                current.autoAccept = newValue
                chatStore.save(current)
            }
        }
        .onChange(of: useMemory) { _, newValue in
            if var current = currentChat {
                current.useMemory = newValue
                chatStore.save(current)
            }
        }
    }

    @ViewBuilder
    private func messageRow(message: Message, proxy: ScrollViewProxy) -> some View {
        MessageRow(
            message: message,
            chat: chat,
            onApprove: { id in
                acrux.approveTool(id: id, approve: true, in: chat)
            },
            onDeny: { id in
                acrux.approveTool(id: id, approve: false, in: chat)
            },
            onPin: {
                togglePin(message)
            },
            onRunCode: { code in
                runCodeBlock(code)
            }
        )
        .id(message.id)
    }

    private func sendMessage() {
        let text = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        input = ""
        acrux.send(text, to: chat)
        suggestSkills(for: text)
    }

    private func suggestSkills(for text: String) {
        Task {
            let suggestions = await acrux.suggestSkills(for: text)
            await MainActor.run {
                skillSuggestion = suggestions.first
            }
        }
    }

    private func runSkillSuggestion(_ suggestion: SkillSuggestion) {
        let command = "/skill \(suggestion.name)"
        acrux.send(command, to: chat)
        skillSuggestion = nil
    }

    private func runCodeBlock(_ code: String) {
        let wrapped = "/run\n```\n\(code)\n```"
        acrux.send(wrapped, to: chat)
    }

    private func togglePin(_ message: Message) {
        guard var current = currentChat else { return }
        if let index = current.messages.firstIndex(where: { $0.id == message.id }) {
            current.messages[index].pinned = !(current.messages[index].pinned ?? false)
            chatStore.save(current)
        }
    }

    private func handleDropped(_ urls: [URL]) {
        for url in urls {
            guard url.isFileURL,
                  let content = try? String(contentsOf: url, encoding: .utf8) else { continue }
            let preview = content.count > 2000 ? String(content.prefix(2000)) + "\n..." : content
            let text = "[Attached file: \(url.lastPathComponent)]\n\n\(preview)"
            acrux.send(text, to: chat)
        }
    }

    private func attachFile() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false

        guard panel.runModal() == .OK, let url = panel.url,
              let content = try? String(contentsOf: url, encoding: .utf8) else { return }

        let preview = content.count > 2000 ? String(content.prefix(2000)) + "\n..." : content
        let text = "[Attached file: \(url.lastPathComponent)]\n\n\(preview)"
        acrux.send(text, to: chat)
    }
}

struct SkillSuggestionBanner: View {
    let suggestion: SkillSuggestion
    let onRun: () -> Void
    let onDismiss: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "wrench.adjustable")
                .foregroundStyle(Color.acruxAccent)
            VStack(alignment: .leading, spacing: 2) {
                Text("Skill '\(suggestion.name)' might help.")
                    .font(.system(size: 13, weight: .semibold))
                if let description = suggestion.description, !description.isEmpty {
                    Text(description)
                        .font(.caption)
                        .foregroundStyle(Color.acruxTextSecondary)
                        .lineLimit(2)
                }
            }
            Spacer()
            Button("Run it") {
                onRun()
            }
            .buttonStyle(GraphitePrimaryButtonStyle())
            .tint(.acruxAccent)
            Button {
                onDismiss()
            } label: {
                Image(systemName: "xmark")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(Color.acruxTextSecondary)
            }
            .buttonStyle(.plain)
        }
        .padding()
        .background(Color.acruxCard)
        .shadow(color: .black.opacity(0.3), radius: 8, y: 2)
        .transition(.graphiteAppear)
    }
}

struct ChatHeader: View {
    let chat: Chat
    @Binding var autoAccept: Bool
    @Binding var useMemory: Bool
    @EnvironmentObject var acrux: AcruxService
    @EnvironmentObject var chatStore: ChatStore
    @ObservedObject var speech: SpeechSynthesizer

    private var currentChat: Chat? { chatStore.chat(id: chat.id) }

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(currentChat?.title ?? chat.title)
                    .font(.system(size: 18, weight: .bold))
                Text("\(chat.model) · \(chat.workspace)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            .padding(.leading, 8)

            Spacer()

            Toggle("Memory", isOn: $useMemory)
                .toggleStyle(.switch)
                .tint(.acruxAccent)
                .help("Use Acrux memory for this chat")

            Button {
                if speech.isSpeaking {
                    speech.stop()
                } else if let last = currentChat?.messages.last(where: { $0.role == "assistant" && !$0.content.isEmpty }) {
                    speech.speak(last.content)
                }
            } label: {
                Image(systemName: speech.isSpeaking ? "speaker.wave.3.fill" : "speaker.wave.2")
                    .font(.system(size: 16))
                    .foregroundStyle(speech.isSpeaking ? Color.acruxAccent : Color.primary)
                    .contentTransition(.symbolEffect(.replace))
            }
            .buttonStyle(AnimatedIconButtonStyle())
            .animation(Theme.springSnappy, value: speech.isSpeaking)
            .help(speech.isSpeaking ? "Stop speaking" : "Read latest response")

            if acrux.isGenerating(chatId: chat.id) {
                Button {
                    acrux.stop(chat: chat)
                } label: {
                    Image(systemName: "stop.fill")
                        .font(.system(size: 16))
                        .foregroundStyle(.red)
                }
                .buttonStyle(AnimatedIconButtonStyle())
                .help("Stop generation")
                .transition(.graphiteAppear)
            }

            Menu {
                Button("Export JSON") {
                    exportJSON()
                }
                .buttonStyle(GraphiteButtonStyle())
                Button("Export Markdown") {
                    exportMarkdown()
                }
                .buttonStyle(GraphiteButtonStyle())
            } label: {
                Image(systemName: "square.and.arrow.up")
                    .font(.system(size: 16))
                    .foregroundStyle(.primary)
                    .frame(width: 36, height: 36)
            }
            .buttonStyle(AnimatedIconButtonStyle())
            .menuStyle(.borderlessButton)

            Toggle("Auto-accept", isOn: $autoAccept)
                .toggleStyle(.switch)
                .tint(.acruxAccent)
        }
        .padding()
        .background(Color.acruxElevated)
    }

    private func exportJSON() {
        let panel = NSSavePanel()
        panel.title = "Export chat as JSON"
        panel.nameFieldStringValue = "\(chat.title).json"
        panel.allowedContentTypes = [.json]
        guard panel.runModal() == .OK, let url = panel.url else { return }

        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = .prettyPrinted
        guard let data = try? encoder.encode(currentChat ?? chat) else { return }
        try? data.write(to: url)
    }

    private func exportMarkdown() {
        let panel = NSSavePanel()
        panel.title = "Export chat as Markdown"
        panel.nameFieldStringValue = "\(chat.title).md"
        panel.allowedContentTypes = [UTType.plainText]
        if #available(macOS 14.0, *), let markdownType = UTType(filenameExtension: "md") {
            panel.allowedContentTypes = [markdownType]
        }
        guard panel.runModal() == .OK, let url = panel.url else { return }

        let messages = currentChat?.messages ?? chat.messages
        var markdown = "# \(chat.title)\n\n"
        for message in messages {
            let role = message.role == "user" ? "User" : "Assistant"
            markdown += "## \(role)\n\n\(message.content)\n\n"
            if let reasoning = message.reasoning, !reasoning.isEmpty {
                markdown += "> Reasoning: \(reasoning)\n\n"
            }
        }
        try? markdown.write(to: url, atomically: true, encoding: .utf8)
    }
}

struct ChatInputBar: View {
    @Binding var input: String
    let isGenerating: Bool
    let onSend: () -> Void
    let onAttach: () -> Void
    let onStop: () -> Void
    @StateObject private var dictation = DictationManager()
    @FocusState private var composerFocused: Bool

    var body: some View {
        HStack(alignment: .bottom, spacing: 12) {
            Button {
                onAttach()
            } label: {
                Image(systemName: "paperclip")
                    .font(.system(size: 18))
                    .foregroundStyle(Color.acruxTextSecondary)
                    .frame(width: 40, height: 44)
            }
            .buttonStyle(AnimatedIconButtonStyle())

            Button {
                dictation.toggle { text in
                    input.append(text)
                }
            } label: {
                Image(systemName: dictation.isListening ? "mic.fill" : "mic")
                    .font(.system(size: 18))
                    .foregroundStyle(dictation.isListening ? Color.acruxAccent : Color.acruxTextSecondary)
                    .frame(width: 40, height: 44)
                    .contentTransition(.symbolEffect(.replace))
                    .shadow(color: dictation.isListening ? Color.acruxAccent.opacity(0.5) : .clear, radius: 8)
            }
            .buttonStyle(AnimatedIconButtonStyle())
            .animation(Theme.springSnappy, value: dictation.isListening)
            .help("Start dictation")

            TextEditor(text: $input)
                .font(.system(size: 14))
                .scrollContentBackground(.hidden)
                .padding(10)
                .frame(minHeight: 44, maxHeight: 120)
                .background(Color.acruxElevated)
                .clipShape(RoundedRectangle(cornerRadius: 14))
                .overlay(
                    RoundedRectangle(cornerRadius: 14)
                        .stroke(Color.acruxAccent.opacity(composerFocused ? 0.5 : 0), lineWidth: 1.5)
                        .shadow(color: Color.acruxAccent.opacity(composerFocused ? 0.15 : 0), radius: 8)
                )
                .animation(Theme.easeQuick, value: composerFocused)
                .focused($composerFocused)
                .onKeyPress(.return) {
                    if !input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        onSend()
                        return .handled
                    }
                    return .ignored
                }

            ZStack {
                if isGenerating {
                    Button {
                        onStop()
                    } label: {
                        Image(systemName: "square.fill")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundColor(.white)
                            .frame(width: 44, height: 44)
                            .background(Color.red.opacity(0.85))
                            .clipShape(Circle())
                    }
                    .buttonStyle(AnimatedCircularButtonStyle())
                    .help("Stop generation")
                    .transition(.scale(scale: 0.6).combined(with: .opacity))
                } else {
                    Button {
                        onSend()
                    } label: {
                        Image(systemName: "arrow.up")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundColor(.acruxOnAccent)
                            .frame(width: 44, height: 44)
                            .background(Color.acruxAccent)
                            .clipShape(Circle())
                            .shadow(color: .black.opacity(0.4), radius: 6, y: 3)
                    }
                    .buttonStyle(AnimatedCircularButtonStyle())
                    .disabled(input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    .opacity(input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? 0.35 : 1.0)
                    .transition(.scale(scale: 0.6).combined(with: .opacity))
                }
            }
            .animation(Theme.springPop, value: isGenerating)
        }
        .padding()
        .background(Color.acruxInputBarBackground)
        .alert("Dictation unavailable", isPresented: .constant(dictation.fallbackMessage != nil)) {
            Button("OK") {
                dictation.fallbackMessage = nil
            }
        } message: {
            Text(dictation.fallbackMessage ?? "")
        }
    }
}
