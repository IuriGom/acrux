import SwiftUI

struct NewTaskView: View {
    @Binding var selectedTab: SidebarTab
    let onOpenChat: (Chat) -> Void
    @EnvironmentObject var acrux: AcruxService
    @EnvironmentObject var chatStore: ChatStore

    @State private var workspace = ""
    @State private var selectedModel = ""
    @State private var autoAccept = false
    @State private var useMemory = true
    @State private var loopMode = false
    @State private var checkpointInterval = 1.0
    @State private var startWatcher = false
    @State private var allowedTools = Set(["read_file", "write_file", "list_files", "run_command", "acrux_recall", "acrux_remember_fact"])
    @State private var showToolsSheet = false
    @State private var showSystemPrompt = false
    @State private var appeared = false

    private let kimiCodeName = "Kimi Code"
    private let tools = [
        ("read_file", "Read a file"),
        ("write_file", "Write a file"),
        ("list_files", "List files"),
        ("run_command", "Run a command"),
        ("acrux_recall", "Search Acrux memory"),
        ("acrux_remember_fact", "Save a fact"),
    ]

    private var isKimiCodeSelected: Bool { selectedModel == kimiCodeName }
    private var canStart: Bool {
        !workspace.isEmpty && !selectedModel.isEmpty && !isKimiCodeSelected
    }

    var body: some View {
        ZStack {
            // Animated background sweep
            GeometryReader { geo in
                LinearGradient(
                    gradient: Gradient(colors: [
                        Color.acruxBg,
                        Color.acruxAccent.opacity(appeared ? 0.04 : 0.0),
                        Color.acruxBg
                    ]),
                    startPoint: .leading,
                    endPoint: .trailing
                )
                .frame(width: geo.size.width * 2)
                .offset(x: appeared ? 0 : -geo.size.width)
                .animation(.easeInOut(duration: 1.2), value: appeared)
            }
            .ignoresSafeArea()

            VStack(alignment: .leading, spacing: 0) {
                AnimatedSection(
                    appeared: appeared,
                    delay: 0,
                    y: -40,
                    startScale: 0.5,
                    rotation: -8,
                    blur: 10,
                    response: 0.7,
                    damping: 0.6
                ) {
                    Text("New Task")
                        .font(.system(size: 36, weight: .black, design: .rounded))
                        .padding(.top, 40)
                        .padding(.horizontal, 40)
                        .shadow(color: Color.acruxAccent.opacity(appeared ? 0.4 : 0.0), radius: 20, y: 4)
                }

                VStack(alignment: .leading, spacing: 24) {
                    AnimatedSection(
                        appeared: appeared,
                        delay: 0.12,
                        x: -120,
                        y: 20,
                        rotation: -3,
                        blur: 6
                    ) {
                        workspaceSection
                    }

                    AnimatedSection(
                        appeared: appeared,
                        delay: 0.22,
                        x: 120,
                        y: 20,
                        rotation: 3,
                        blur: 6
                    ) {
                        ModelSectionView(
                            selectedModel: $selectedModel,
                            models: acrux.models,
                            kimiCodeName: kimiCodeName,
                            onRefresh: {
                                Task { await acrux.fetchModels() }
                            }
                        )
                    }

                    AnimatedSection(
                        appeared: appeared,
                        delay: 0.32,
                        y: 40,
                        startScale: 0.3
                    ) {
                        toolsButton
                    }

                    AnimatedSection(
                        appeared: appeared,
                        delay: 0.42,
                        y: 60,
                        blur: 8
                    ) {
                        VStack(alignment: .leading, spacing: 18) {
                            animatedToggle("Auto-accept tools", isOn: $autoAccept)
                            animatedToggle("Use Acrux memory for this chat", isOn: $useMemory)

                            VStack(alignment: .leading, spacing: 8) {
                                animatedToggle("Agent loop mode", isOn: $loopMode)
                                if loopMode {
                                    HStack {
                                        Text("Checkpoint every")
                                            .font(.caption)
                                        Slider(value: $checkpointInterval, in: 1...10, step: 1)
                                            .frame(width: 160)
                                        Text("\(Int(checkpointInterval)) turns")
                                            .font(.caption)
                                            .monospacedDigit()
                                    }
                                    .transition(.asymmetric(
                                        insertion: .opacity.combined(with: .offset(y: -12)).combined(with: .scale(scale: 0.95)),
                                        removal: .opacity.combined(with: .offset(y: 12)).combined(with: .scale(scale: 0.95))
                                    ))
                                }
                            }

                            animatedToggle("Start workspace watcher", isOn: $startWatcher)
                        }
                    }

                    AnimatedSection(
                        appeared: appeared,
                        delay: 0.55,
                        y: 40,
                        startScale: 0.85
                    ) {
                        HStack {
                            Button("System prompt") {
                                showSystemPrompt = true
                            }
                            .buttonStyle(ElasticButtonStyle())
                            .disabled(workspace.isEmpty)

                            Spacer()

                            Button("Start") {
                                startChat()
                            }
                            .buttonStyle(PulseButtonStyle())
                            .disabled(!canStart)
                        }
                        .padding(.top, 12)
                    }

                    Spacer(minLength: 40)
                }
                .padding(.horizontal, 40)
                .padding(.top, 32)
                .frame(maxWidth: 600, alignment: .leading)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .background(Color.acruxBg)
        .dismissablePopup(isPresented: $showToolsSheet) {
            ToolsSheet(tools: tools, allowedTools: $allowedTools)
        }
        .dismissablePopup(isPresented: $showSystemPrompt) {
            ProjectSystemPromptView(project: workspace)
        }
        .onAppear {
            appeared = false
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                withAnimation {
                    appeared = true
                }
            }
        }
    }

    private var workspaceSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("WORKSPACE FOLDER")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
            HStack {
                Text(workspace.isEmpty ? "No folder selected" : workspace)
                    .foregroundStyle(workspace.isEmpty ? .secondary : .primary)
                    .lineLimit(1)
                Spacer()
                Button("Choose folder") {
                    if let path = WorkspacePicker.pick() {
                        workspace = path
                    }
                }
                .buttonStyle(WiggleButtonStyle())
            }
            .padding()
            .background(.ultraThinMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color.acruxAccent.opacity(workspace.isEmpty ? 0.0 : 0.5), lineWidth: 1.5)
                    .shadow(color: Color.acruxAccent.opacity(workspace.isEmpty ? 0.0 : 0.25), radius: workspace.isEmpty ? 0 : 8)
            )
            .scaleEffect(workspace.isEmpty ? 1.0 : 1.015)
            .animation(Theme.springSnappy, value: workspace)
            .graphiteHoverRow()
        }
    }

    private var toolsButton: some View {
        HStack {
            Button {
                showToolsSheet = true
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: "wrench.adjustable")
                    Text("Tools")
                        .font(.system(size: 14, weight: .semibold))
                    Text("\(allowedTools.count)/\(tools.count)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .buttonStyle(FlipButtonStyle())

            Spacer()
        }
    }

    private func animatedToggle(_ title: String, isOn: Binding<Bool>) -> some View {
        AcruxToggleRow(title: title, isOn: isOn)
    }

    private func startChat() {
        let chat = Chat(
            id: UUID(),
            title: "New task",
            workspace: workspace,
            model: selectedModel,
            allowedTools: Array(allowedTools),
            autoAccept: autoAccept,
            useMemory: useMemory,
            loopMode: loopMode,
            checkpointInterval: Int(checkpointInterval),
            messages: [],
            createdAt: Date(),
            updatedAt: Date()
        )
        chatStore.save(chat)
        onOpenChat(chat)
        selectedTab = .chats
        if startWatcher {
            Task {
                _ = await acrux.setWatcher(project: workspace, running: true)
            }
        }
    }
}

struct ToolsSheet: View {
    let tools: [(String, String)]
    @Binding var allowedTools: Set<String>
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            HStack {
                Text("Allowed Tools")
                    .font(.system(size: 20, weight: .bold))
                Spacer()
                Button("Done") {
                    dismiss()
                }
                .buttonStyle(GraphitePrimaryButtonStyle())
            }

            Text("Choose which tools the assistant may use for this task.")
                .font(.caption)
                .foregroundStyle(.secondary)

            LazyVGrid(columns: [GridItem(.flexible(), spacing: 12), GridItem(.flexible(), spacing: 12)], spacing: 12) {
                ForEach(tools, id: \.0) { name, desc in
                    ToolCard(name: name, desc: desc, isOn: Binding(
                        get: { allowedTools.contains(name) },
                        set: { isOn in
                            if isOn { allowedTools.insert(name) } else { allowedTools.remove(name) }
                        }
                    ))
                }
            }

            Spacer()
        }
        .padding(28)
        .frame(minWidth: 420, minHeight: 320)
        .background(Color.acruxBg)
    }
}

struct ToolCard: View {
    let name: String
    let desc: String
    @Binding var isOn: Bool

    var body: some View {
        Toggle(isOn: $isOn) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(name)
                        .font(.system(size: 13, weight: .semibold))
                        .lineLimit(1)
                    Text(desc)
                        .font(.caption)
                        .foregroundStyle(Color.acruxTextSecondary)
                        .lineLimit(2)
                        .multilineTextAlignment(.leading)
                }
                .frame(maxWidth: .infinity, alignment: .leading)

                if isOn {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 18, weight: .bold))
                        .foregroundStyle(Color.acruxAccent)
                        .transition(.scale.combined(with: .opacity))
                }
            }
        }
        .toggleStyle(.checkbox)
        .tint(.acruxAccent)
        .padding(12)
        .frame(maxWidth: .infinity, minHeight: 72, alignment: .leading)
        .background(isOn ? Color.acruxActive : Color.acruxCard)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.acruxAccent.opacity(isOn ? 0.6 : 0.0), lineWidth: 1.5)
                .shadow(color: Color.acruxAccent.opacity(isOn ? 0.35 : 0), radius: isOn ? 8 : 0)
        )
        .shadow(color: .black.opacity(isOn ? 0.35 : 0.2), radius: isOn ? 8 : 4, y: 2)
        .scaleEffect(isOn ? 1.02 : 1.0)
        .animation(Theme.springSnappy, value: isOn)
    }
}

struct ModelMenu: View {
    @Binding var selection: String
    let models: [OllamaModel]
    let kimiCodeName: String

    var body: some View {
        Menu {
            Section("Local Ollama models") {
                ForEach(models) { model in
                    Button {
                        selection = model.name
                    } label: {
                        HStack {
                            Text("\(model.name) ・ \(formatBytes(model.size))")
                            Spacer()
                            if selection == model.name {
                                Image(systemName: "checkmark")
                                    .font(.system(size: 10, weight: .bold))
                            }
                        }
                    }
                }
            }

            Button {
                selection = kimiCodeName
            } label: {
                HStack {
                    Text(kimiCodeName)
                    Spacer()
                    if selection == kimiCodeName {
                        Image(systemName: "checkmark")
                            .font(.system(size: 10, weight: .bold))
                    }
                }
            }
        } label: {
            HStack(spacing: 8) {
                Text(selection.isEmpty ? "Select a model..." : selection)
                    .font(.system(size: 13, weight: .medium))
                    .foregroundStyle(selection.isEmpty ? Color.acruxTextTertiary : .primary)
                    .lineLimit(1)
                Spacer()
                Image(systemName: "chevron.down")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(Color.acruxAccent)
            }
            .padding(.horizontal, 4)
            .padding(.vertical, 6)
            .frame(minWidth: 220, idealWidth: 280, maxWidth: 340)
            .overlay(
                Rectangle()
                    .fill(Color.acruxAccent.opacity(0.35))
                    .frame(height: 1),
                alignment: .bottom
            )
        }
        .menuStyle(.borderlessButton)
        .menuIndicator(.hidden)
    }
}

struct ModelSectionView: View {
    @Binding var selectedModel: String
    let models: [OllamaModel]
    let kimiCodeName: String
    let onRefresh: () -> Void

    private var isKimiCodeSelected: Bool { selectedModel == kimiCodeName }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("MODEL")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)

            HStack(spacing: 10) {
                ModelMenu(
                    selection: $selectedModel,
                    models: models,
                    kimiCodeName: kimiCodeName
                )

                Button(action: onRefresh) {
                    Image(systemName: "arrow.clockwise")
                        .font(.system(size: 13, weight: .semibold))
                }
                .buttonStyle(SpinIconButtonStyle())
                .foregroundStyle(Color.acruxAccent)
                .help("Refresh Ollama model list")
            }
            .frame(height: 34)

            if isKimiCodeSelected {
                HStack(alignment: .top, spacing: 10) {
                    Image(systemName: "info.circle.fill")
                        .foregroundStyle(Color.acruxAccent)
                    Text("Kimi Code connects to Acrux through the MCP server, not this chat. Use Kimi Code directly for coding assistance.")
                        .font(.caption)
                        .fixedSize(horizontal: false, vertical: true)
                    Spacer()
                }
                .padding()
                .background(Color.acruxCard)
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .shadow(color: .black.opacity(0.25), radius: 6, y: 2)
                .transition(.graphiteAppear)
            }
        }
        .onAppear {
            if models.isEmpty {
                onRefresh()
            }
            if selectedModel.isEmpty, let first = models.first {
                selectedModel = first.name
            }
        }
        .onChange(of: models) { _, models in
            if selectedModel.isEmpty, let first = models.first {
                selectedModel = first.name
            }
        }
    }
}

private func formatBytes(_ bytes: Int) -> String {
    let units = ["B", "KB", "MB", "GB", "TB"]
    var value = Double(bytes)
    var idx = 0
    while value >= 1024 && idx < units.count - 1 {
        value /= 1024
        idx += 1
    }
    return String(format: "%.1f %@", value, units[idx])
}

/// Extravagant toggle row: sweep fill, drawing checkmark, glow and pop.
struct AcruxToggleRow: View {
    let title: String
    @Binding var isOn: Bool
    @State private var hovering = false
    @State private var pressing = false

    var body: some View {
        Button {
            withAnimation(Theme.springPop) {
                pressing = true
                isOn.toggle()
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.12) {
                pressing = false
            }
        } label: {
            HStack(spacing: 14) {
                ZStack {
                    Circle()
                        .stroke(isOn ? Color.acruxAccent : Color.acruxSubtleBorder, lineWidth: 2)
                        .frame(width: 24, height: 24)
                        .background(
                            Circle()
                                .fill(isOn ? Color.acruxAccent.opacity(0.2) : Color.clear)
                        )
                        .scaleEffect(isOn ? 1.1 : 1.0)

                    if isOn {
                        Image(systemName: "checkmark")
                            .font(.system(size: 11, weight: .black))
                            .foregroundStyle(Color.acruxAccent)
                            .transition(.scale.combined(with: .opacity))
                    }
                }
                .animation(Theme.springPop, value: isOn)

                Text(title)
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(isOn ? .primary : Color.acruxTextSecondary)

                Spacer()
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
            .background(
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 12)
                        .fill(isOn ? Color.acruxActive : Color.acruxCard)

                    GeometryReader { geo in
                        RoundedRectangle(cornerRadius: 12)
                            .fill(
                                LinearGradient(
                                    colors: [Color.acruxAccent.opacity(0.45), Color.acruxAccent.opacity(0.0)],
                                    startPoint: .leading,
                                    endPoint: .trailing
                                )
                            )
                            .frame(width: isOn ? geo.size.width * 0.65 : 0)
                            .animation(.easeOut(duration: 0.35), value: isOn)
                    }
                }
            )
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color.acruxAccent.opacity(isOn ? 0.75 : 0.0), lineWidth: 2)
                    .shadow(color: Color.acruxAccent.opacity(isOn ? 0.4 : 0.0), radius: isOn ? 12 : 0)
            )
            .shadow(color: .black.opacity(isOn ? 0.35 : 0.2), radius: isOn ? 10 : 4, y: 2)
            .contentShape(RoundedRectangle(cornerRadius: 12))
        }
        .buttonStyle(.plain)
        .scaleEffect(pressing ? 0.95 : (hovering ? 1.02 : 1.0))
        .offset(x: hovering ? 3 : 0)
        .animation(Theme.springPop, value: pressing)
        .animation(Theme.springSnappy, value: hovering)
        .onHover { hovering = $0 }
    }
}
