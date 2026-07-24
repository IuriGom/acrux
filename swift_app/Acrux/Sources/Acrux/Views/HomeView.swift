import SwiftUI
import SpriteKit

extension Notification.Name {
    static let focusMemorySearch = Notification.Name("focusMemorySearch")
    static let openMemoryFactTree = Notification.Name("openMemoryFactTree")
}

enum SidebarTab: String, CaseIterable, Identifiable {
    case home = "Home"
    case newTask = "New Task"
    case chats = "Past Chats"
    case memory = "Memory"
    case knowledgeGraph = "Knowledge Graph"
    case importExport = "Import / Export"
    case health = "Health"
    case acruxStatus = "Acrux Status"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .home: return "house"
        case .newTask: return "plus.square"
        case .chats: return "clock.arrow.circlepath"
        case .memory: return "memorychip"
        case .knowledgeGraph: return "circle.hexagongrid"
        case .importExport: return "square.and.arrow.up"
        case .health: return "stethoscope"
        case .acruxStatus: return "star.fill"
        }
    }

    var keyboardShortcut: KeyboardShortcut? {
        switch self {
        case .home: return KeyboardShortcut("1")
        case .newTask: return KeyboardShortcut("2")
        case .chats: return KeyboardShortcut("3")
        case .memory: return KeyboardShortcut("4")
        case .knowledgeGraph: return KeyboardShortcut("6")
        case .importExport: return nil
        case .health: return nil
        case .acruxStatus: return KeyboardShortcut("5")
        }
    }
}

struct HomeView: View {
    @EnvironmentObject var acrux: AcruxService
    @EnvironmentObject var chatStore: ChatStore
    @State private var selectedTab: SidebarTab = .home
    @State private var openChats: [Chat] = []
    @State private var activeChatId: UUID?
    @State private var chatLayout: ChatLayout = .single
    @State private var visibleChatIds: [UUID] = []
    @State private var columnVisibility: NavigationSplitViewVisibility = .all
    @State private var showCommandPalette = false
    @State private var showMessageSearch = false
    @State private var showFloatingWidget = false
    @State private var showLaunchSplash = true

    var body: some View {
        NavigationSplitView(columnVisibility: $columnVisibility) {
            SidebarView(selectedTab: $selectedTab, activeChatId: $activeChatId, columnVisibility: $columnVisibility)
                .frame(minWidth: 220, idealWidth: 240)
        } detail: {
            detailContent
                .toolbar {
                    ToolbarItem(placement: .navigation) {
                        Button {
                            withAnimation(.easeInOut(duration: 0.2)) {
                                columnVisibility = columnVisibility == .all ? .detailOnly : .all
                            }
                        } label: {
                            Image(systemName: columnVisibility == .all ? "sidebar.left" : "sidebar.left.fill")
                                .foregroundStyle(.primary)
                        }
                        .buttonStyle(AnimatedIconButtonStyle())
                        .help("Collapse or expand the sidebar")
                    }
                }
        }
        .preferredColorScheme(.dark)
        .overlay(
            hiddenShortcutButtons
                .frame(width: 1, height: 1)
                .opacity(0)
        )
        .overlay(
            ZStack {
                if showLaunchSplash {
                    LaunchSplashView()
                        .transition(.opacity.combined(with: .scale(scale: 1.15)))
                        .onAppear {
                            DispatchQueue.main.asyncAfter(deadline: .now() + 2.8) {
                                withAnimation(.easeInOut(duration: 0.8)) {
                                    showLaunchSplash = false
                                }
                            }
                        }
                }
                if showCommandPalette {
                    Color.acruxOverlay
                        .ignoresSafeArea()
                        .onTapGesture { showCommandPalette = false }
                    CommandPaletteView(isPresented: $showCommandPalette, items: commandPaletteItems)
                }
            }
        )
        .dismissablePopup(isPresented: $showMessageSearch) {
            MessageSearchView(isPresented: $showMessageSearch)
        }
        .onAppear {
            AcruxServiceReference.shared = acrux
            chatStore.load()
            if !acrux.isBackendRunning && !acrux.userStoppedBackend {
                acrux.startBackend()
            }
            Task {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                await acrux.fetchStatus()
                await acrux.fetchModels()
            }
        }
        .onChange(of: chatStore.chats) { _, _ in
            openChats = openChats.compactMap { openChat in chatStore.chats.first { $0.id == openChat.id } }
        }
        .onReceive(NotificationCenter.default.publisher(for: .openMemoryFactTree)) { note in
            acrux.pendingFactTree = note.object as? [String: String]
            activeChatId = nil
            selectedTab = .memory
        }
    }

    @ViewBuilder
    private var hiddenShortcutButtons: some View {
        Button {
            activeChatId = nil
            selectedTab = .newTask
        } label: {
            EmptyView()
        }
        .keyboardShortcut("n", modifiers: .command)

        Button {
            if acrux.isBackendRunning {
                acrux.stopBackend()
            } else {
                acrux.startBackend()
            }
        } label: {
            EmptyView()
        }
        .keyboardShortcut("b", modifiers: [.command, .shift])
        .disabled(acrux.isTogglingBackend)

        Button {
            activeChatId = nil
            selectedTab = .memory
            NotificationCenter.default.post(name: .focusMemorySearch, object: nil)
        } label: {
            EmptyView()
        }
        .keyboardShortcut("k", modifiers: .command)

        Button {
            showCommandPalette.toggle()
        } label: {
            EmptyView()
        }
        .keyboardShortcut("p", modifiers: [.command, .shift])

        Button {
            activeChatId = nil
            selectedTab = .knowledgeGraph
        } label: {
            EmptyView()
        }
        .keyboardShortcut("g", modifiers: [.command, .shift])

        Button {
            showMessageSearch = true
        } label: {
            EmptyView()
        }
        .keyboardShortcut("f", modifiers: [.command, .shift])
    }

    private var commandPaletteItems: [CommandPaletteItem] {
        [
            CommandPaletteItem(title: "New task", icon: "plus.square") {
                activeChatId = nil
                selectedTab = .newTask
            },
            CommandPaletteItem(title: "Search memory", icon: "magnifyingglass") {
                activeChatId = nil
                selectedTab = .memory
                NotificationCenter.default.post(name: .focusMemorySearch, object: nil)
            },
            CommandPaletteItem(title: "Knowledge graph", icon: "circle.hexagongrid") {
                activeChatId = nil
                selectedTab = .knowledgeGraph
            },
            CommandPaletteItem(title: "Search messages", icon: "bubble.left") {
                showMessageSearch = true
            },
            CommandPaletteItem(title: "Toggle Acrux backend", icon: "power", disabled: acrux.isTogglingBackend) {
                if acrux.isBackendRunning {
                    acrux.stopBackend()
                } else {
                    acrux.startBackend()
                }
            },
            CommandPaletteItem(title: "Health checks", icon: "stethoscope") {
                activeChatId = nil
                selectedTab = .health
            },
            CommandPaletteItem(title: "Import / Export", icon: "square.and.arrow.up") {
                activeChatId = nil
                selectedTab = .importExport
            },
            CommandPaletteItem(title: "Toggle floating widget", icon: "square.on.square") {
                toggleFloatingWidget()
            }
        ]
    }

    private func toggleFloatingWidget() {
        if let panel = FloatingPanelController.shared, panel.isVisible {
            panel.close()
        } else {
            let panel = FloatingPanelController()
            panel.center()
            panel.orderFront(nil)
        }
    }

    @ViewBuilder
    private var detailContent: some View {
        VStack(spacing: 0) {
            if !openChats.isEmpty {
                ChatTabsView(
                    activeChatId: $activeChatId,
                    openChats: openChats,
                    visibleChatIds: visibleChatIds,
                    layout: chatLayout,
                    onClose: closeChat,
                    onLayoutChange: setLayout(_:),
                    onToggleVisible: toggleVisible(_:)
                )
            }

            ZStack {
                if openChats.isEmpty {
                    animatedSidebarContent
                        .transition(.asymmetric(
                            insertion: .opacity.combined(with: .offset(x: -160)).combined(with: .scale(scale: 0.92)),
                            removal: .opacity.combined(with: .offset(x: -120)).combined(with: .scale(scale: 0.95))
                        ))
                } else {
                    ChatWorkspaceView(
                        layout: chatLayout,
                        visibleChatIds: visibleChatIds,
                        activeChatId: $activeChatId
                    )
                    .transition(.asymmetric(
                        insertion: .move(edge: .trailing).combined(with: .opacity).combined(with: .scale(scale: 0.96)),
                        removal: .move(edge: .trailing).combined(with: .opacity).combined(with: .scale(scale: 0.96))
                    ))
                }
            }
            .animation(.spring(response: 0.65, dampingFraction: 0.75), value: openChats.isEmpty)
            .animation(.spring(response: 0.45, dampingFraction: 0.78), value: chatLayout)
        }
    }

    @ViewBuilder
    private var sidebarContent: some View {
        switch selectedTab {
        case .home:
            LandingView(selectedTab: $selectedTab)
        case .newTask:
            NewTaskView(selectedTab: $selectedTab, onOpenChat: openChat)
        case .chats:
            PastChatsView(selectedTab: $selectedTab, onOpenChat: openChat)
        case .memory:
            MemoryInspectorView()
        case .knowledgeGraph:
            KnowledgeGraphView()
        case .importExport:
            ImportExportView()
        case .health:
            HealthCheckView()
        case .acruxStatus:
            AcruxStatusView()
        }
    }

    @ViewBuilder
    private var animatedSidebarContent: some View {
        sidebarContent
            .id(selectedTab)
            .transition(.asymmetric(
                insertion: .opacity
                    .combined(with: .offset(x: 60, y: 20))
                    .combined(with: .scale(scale: 0.94)),
                removal: .opacity
                    .combined(with: .offset(x: -60, y: -20))
                    .combined(with: .scale(scale: 0.96))
            ))
            .animation(.spring(response: 0.55, dampingFraction: 0.78), value: selectedTab)
    }

    private func openChat(_ chat: Chat) {
        if !openChats.contains(where: { $0.id == chat.id }) {
            withAnimation(Theme.springEntrance) {
                openChats.append(chat)
            }
        }
        if !visibleChatIds.contains(chat.id) {
            visibleChatIds.append(chat.id)
            if visibleChatIds.count > chatLayout.maxVisible {
                withAnimation(Theme.springSnappy) {
                    chatLayout = layoutFor(count: visibleChatIds.count)
                }
            }
        }
        withAnimation(Theme.springEntrance) {
            activeChatId = chat.id
        }
    }

    private func closeChat(_ chat: Chat) {
        withAnimation(Theme.springSnappy) {
            openChats.removeAll { $0.id == chat.id }
            visibleChatIds.removeAll { $0 == chat.id }
        }
        acrux.closeChat(chat)
        if activeChatId == chat.id {
            withAnimation(Theme.springSnappy) {
                activeChatId = visibleChatIds.last ?? openChats.last?.id
            }
        }
        if visibleChatIds.isEmpty, let first = openChats.first {
            visibleChatIds.append(first.id)
            chatLayout = .single
        }
    }

    private func setLayout(_ layout: ChatLayout) {
        withAnimation(Theme.springSnappy) {
            chatLayout = layout
            let max = layout.maxVisible
            if visibleChatIds.count > max {
                visibleChatIds = Array(visibleChatIds.prefix(max))
            }
            if let active = activeChatId, !visibleChatIds.contains(active), let first = visibleChatIds.first {
                activeChatId = first
            }
        }
    }

    private func toggleVisible(_ id: UUID) {
        withAnimation(Theme.springSnappy) {
            if visibleChatIds.contains(id) {
                visibleChatIds.removeAll { $0 == id }
                if visibleChatIds.isEmpty, let first = openChats.first {
                    visibleChatIds.append(first.id)
                    chatLayout = .single
                }
            } else {
                if visibleChatIds.count >= 4 {
                    return
                }
                visibleChatIds.append(id)
                chatLayout = layoutFor(count: visibleChatIds.count)
            }
            if let active = activeChatId, !visibleChatIds.contains(active) {
                activeChatId = visibleChatIds.first
            }
        }
    }

    private func layoutFor(count: Int) -> ChatLayout {
        switch count {
        case 1: return .single
        case 2: return .dual
        default: return .quad
        }
    }
}

struct LaunchSplashView: View {
    @State private var pulse = false
    @State private var ringScale: CGFloat = 0.4
    @State private var ringOpacity: Double = 1
    @State private var logoScale: CGFloat = 0.5
    @State private var logoRotation: Double = -25
    @State private var textOpacity: Double = 0
    @State private var textOffset: CGFloat = 30
    @State private var particles: [SplashParticle] = []
    @State private var glowAmount: CGFloat = 0

    private let screenW = NSScreen.main?.frame.width ?? 1400
    private let screenH = NSScreen.main?.frame.height ?? 900

    var body: some View {
        ZStack {
            // Deep animated gradient background
            Color.acruxBg.ignoresSafeArea()

            GeometryReader { geo in
                ZStack {
                    // Slowly rotating color wheel
                    AngularGradient(
                        gradient: Gradient(colors: [
                            Color.acruxAccent.opacity(0.0),
                            Color.acruxAccent.opacity(0.25),
                            Color.purple.opacity(0.15),
                            Color.acruxAccent.opacity(0.0)
                        ]),
                        center: .center,
                        angle: .degrees(pulse ? 360 : 0)
                    )
                    .blur(radius: 80)
                    .scaleEffect(1.4)
                    .animation(.linear(duration: 8).repeatForever(autoreverses: false), value: pulse)

                    // Expanding rings
                    ForEach(0..<5) { i in
                        Circle()
                            .stroke(
                                Color.acruxAccent.opacity(0.15 - Double(i) * 0.025),
                                lineWidth: CGFloat(3 - i)
                            )
                            .frame(width: 200 + CGFloat(i) * 220, height: 200 + CGFloat(i) * 220)
                            .scaleEffect(pulse ? 1.35 : 0.7)
                            .opacity(pulse ? 0.05 : 0.35)
                            .animation(
                                .easeInOut(duration: 2.2)
                                    .repeatForever(autoreverses: true)
                                    .delay(Double(i) * 0.3),
                                value: pulse
                            )
                    }
                }
                .frame(width: geo.size.width, height: geo.size.height)
            }

            // Animated particle field
            ForEach(particles) { particle in
                Circle()
                    .fill(particle.color)
                    .frame(width: particle.size, height: particle.size)
                    .position(particle.position)
                    .opacity(particle.opacity)
                    .blur(radius: particle.blur)
                    .offset(x: pulse ? particle.drift.x : -particle.drift.x,
                            y: pulse ? particle.drift.y : -particle.drift.y)
                    .animation(
                        .easeInOut(duration: particle.speed)
                            .repeatForever(autoreverses: true)
                            .delay(particle.delay),
                        value: pulse
                    )
            }

            VStack(spacing: 34) {
                ZStack {
                    // Outer glow
                    Circle()
                        .fill(Color.acruxAccent.opacity(0.35))
                        .frame(width: 160, height: 160)
                        .blur(radius: glowAmount)
                        .opacity(glowAmount > 0 ? 1 : 0)

                    // Expanding ripple rings
                    Circle()
                        .stroke(Color.acruxAccent.opacity(0.8), lineWidth: 3)
                        .frame(width: 120, height: 120)
                        .scaleEffect(ringScale)
                        .opacity(ringOpacity)

                    Circle()
                        .stroke(Color.white.opacity(0.5), lineWidth: 2)
                        .frame(width: 120, height: 120)
                        .scaleEffect(ringScale * 0.82)
                        .opacity(ringOpacity)

                    // Inner disc
                    Circle()
                        .fill(
                            RadialGradient(
                                gradient: Gradient(colors: [Color.acruxAccent.opacity(0.25), Color.acruxAccent.opacity(0.0)]),
                                center: .center,
                                startRadius: 0,
                                endRadius: 70
                            )
                        )
                        .frame(width: 140, height: 140)
                        .scaleEffect(logoScale)

                    Image(systemName: "star.fill")
                        .font(.system(size: 74, weight: .black))
                        .foregroundStyle(
                            LinearGradient(
                                colors: [.white, Color.acruxAccent, Color.purple.opacity(0.8)],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .scaleEffect(logoScale)
                        .rotationEffect(.degrees(logoRotation))
                        .shadow(color: Color.acruxAccent.opacity(0.8), radius: 30, x: 0, y: 0)
                        .shadow(color: Color.white.opacity(0.4), radius: 12, x: 0, y: 0)
                }

                VStack(spacing: 10) {
                    Text("Acrux")
                        .font(.system(size: 68, weight: .black, design: .rounded))
                        .foregroundStyle(
                            LinearGradient(
                                colors: [.white, Color(red: 0.85, green: 0.86, blue: 0.88), Color.acruxAccent.opacity(0.7)],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .opacity(textOpacity)
                        .offset(y: textOffset)
                        .shadow(color: Color.acruxAccent.opacity(0.45), radius: 20, y: 4)

                    Text("Loading memory system…")
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundStyle(Color.acruxTextSecondary)
                        .shimmer(active: true)
                        .opacity(textOpacity)
                        .offset(y: textOffset)
                }
            }
        }
        .onAppear {
            pulse = true
            spawnParticles()
            withAnimation(.spring(response: 0.6, dampingFraction: 0.65)) {
                logoScale = 1.0
                logoRotation = 0
                glowAmount = 28
            }
            withAnimation(.easeOut(duration: 1.4)) {
                ringScale = 3.2
                ringOpacity = 0
            }
            withAnimation(.spring(response: 0.7, dampingFraction: 0.75).delay(0.25)) {
                textOpacity = 1.0
                textOffset = 0
            }
        }
    }

    private func spawnParticles() {
        let colors: [Color] = [.acruxAccent, .white, .acruxAccent.opacity(0.7), .purple.opacity(0.6)]
        var newParticles: [SplashParticle] = []
        for i in 0..<90 {
            let angle = Double(i) * (2 * .pi / 90) + Double.random(in: 0...(2 * .pi))
            let distance: CGFloat = CGFloat.random(in: 60...max(screenW, screenH) * 0.55)
            newParticles.append(SplashParticle(
                position: CGPoint(
                    x: screenW / 2 + cos(angle) * distance,
                    y: screenH / 2 + sin(angle) * distance
                ),
                color: colors.randomElement()!,
                size: CGFloat.random(in: 2...7),
                opacity: Double.random(in: 0.15...0.7),
                blur: CGFloat.random(in: 0...3),
                drift: CGPoint(x: CGFloat.random(in: -40...40), y: CGFloat.random(in: -40...40)),
                speed: Double.random(in: 2.5...5.0),
                delay: Double.random(in: 0...1.5)
            ))
        }
        particles = newParticles
    }
}

struct SplashParticle: Identifiable {
    let id = UUID()
    var position: CGPoint
    var color: Color
    var size: CGFloat
    var opacity: Double
    var blur: CGFloat
    var drift: CGPoint
    var speed: Double
    var delay: Double
}

struct LandingView: View {
    @Binding var selectedTab: SidebarTab

    var body: some View {
        ZStack {
            SpriteView(scene: AcruxAnimationScene(size: CGSize(width: 1400, height: 900)),
                       options: [.allowsTransparency])
                .ignoresSafeArea()

            VStack(spacing: 18) {
                Text("Acrux")
                    .font(.system(size: 86, weight: .black, design: .rounded))
                    .foregroundStyle(
                        LinearGradient(
                            colors: [.white, Color(red: 0.75, green: 0.76, blue: 0.78), Color(red: 0.45, green: 0.47, blue: 0.50)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )

                Text("Local memory. Long-term reasoning. Your workspace, understood.")
                    .font(.title3)
                    .foregroundStyle(Color.acruxTextSecondary)

                Button("Start a task") {
                    withAnimation(Theme.springSnappy) {
                        selectedTab = .newTask
                    }
                }
                .buttonStyle(AcruxButtonStyle())
                .padding(.top, 12)
            }
        }
    }
}

struct AcruxButtonStyle: ButtonStyle {
    @State private var hovering = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline.weight(.semibold))
            .padding(.horizontal, 28)
            .padding(.vertical, 14)
            .background(
                RoundedRectangle(cornerRadius: 16)
                    .fill(
                        LinearGradient(
                            colors: [
                                configuration.isPressed ? Color.acruxAccent.opacity(0.85) : Color.acruxAccent,
                                configuration.isPressed ? Color.acruxAccent.opacity(0.7) : Color.acruxAccent.opacity(0.85)
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
            )
            .foregroundColor(.acruxOnAccent)
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .shadow(color: Color.acruxAccent.opacity(hovering ? 0.5 : 0.0), radius: hovering ? 24 : 0, y: 0)
            .shadow(color: .black.opacity(hovering ? 0.55 : 0.35), radius: hovering ? 22 : 14, x: 0, y: hovering ? 10 : 6)
            .scaleEffect(configuration.isPressed ? 0.93 : (hovering ? 1.04 : 1.0))
            .offset(y: hovering && !configuration.isPressed ? -2 : 0)
            .animation(Theme.springPop, value: configuration.isPressed)
            .animation(Theme.springSnappy, value: hovering)
            .onHover { hovering = $0 }
    }
}
