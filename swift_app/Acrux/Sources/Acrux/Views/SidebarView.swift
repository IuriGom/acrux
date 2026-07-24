import SwiftUI

struct SidebarView: View {
    @Binding var selectedTab: SidebarTab
    @Binding var activeChatId: UUID?
    @Binding var columnVisibility: NavigationSplitViewVisibility
    @EnvironmentObject var acrux: AcruxService
    @Namespace private var selectionNamespace

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 10) {
                PulsingDot(color: .acruxAccent, size: 9)

                Text("Acrux")
                    .font(.system(size: 22, weight: .bold, design: .rounded))

                Spacer()

                Button {
                    withAnimation(Theme.springSnappy) {
                        columnVisibility = .detailOnly
                    }
                } label: {
                    Image(systemName: "sidebar.left")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(Color.acruxTextSecondary)
                }
                .buttonStyle(AnimatedIconButtonStyle())
                .help("Collapse sidebar")
            }
            .padding(.horizontal, 16)
            .padding(.top, 24)
            .padding(.bottom, 28)

            VStack(spacing: 6) {
                ForEach(SidebarTab.allCases, id: \.self) { tab in
                    SidebarButton(
                        tab: tab,
                        selectedTab: $selectedTab,
                        activeChatId: $activeChatId,
                        selectionNamespace: selectionNamespace
                    )
                }
            }
            .padding(.horizontal, 10)

            Spacer()

            VStack(spacing: 10) {
                AcruxPowerButton(
                    isOn: acrux.isBackendRunning,
                    isLoading: acrux.isTogglingBackend,
                    action: {
                        if acrux.isBackendRunning {
                            acrux.stopBackend()
                        } else {
                            acrux.startBackend()
                        }
                    }
                )
                .disabled(acrux.isTogglingBackend)
                .help(acrux.isBackendRunning ? "Stop the Acrux backend" : "Start the Acrux backend")

                HStack {
                    if acrux.isConnected {
                        PulsingDot(color: .acruxAccent, size: 7)
                    } else {
                        Circle()
                            .fill(Color.acruxTextTertiary)
                            .frame(width: 7, height: 7)
                    }
                    Text(acrux.isConnected ? "Acrux online" : "Acrux offline")
                        .font(.caption)
                        .foregroundStyle(Color.acruxTextSecondary)
                        .contentTransition(.numericText())
                    Spacer()
                }
                .padding(12)
                .background(Color.acruxCard)
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .scaleEffect(acrux.isConnected ? 1.0 : 0.98)
                .animation(Theme.springSnappy, value: acrux.isConnected)
            }
            .padding(.horizontal, 14)
            .padding(.bottom, 16)
        }
        .background(Color.acruxSidebar)
        .task {
            await acrux.fetchStatus()
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                await acrux.fetchStatus()
            }
        }
    }
}

struct AcruxPowerButton: View {
    let isOn: Bool
    let isLoading: Bool
    let action: () -> Void
    @State private var ripple = false
    @State private var glowPulse = false
    @State private var particles: [PowerParticle] = []
    @State private var iconRotation: Double = 0

    var body: some View {
        Button(action: handleTap) {
            ZStack {
                // Pulsing aura when online
                if isOn {
                    RoundedRectangle(cornerRadius: 12)
                        .fill(Color.acruxAccent.opacity(0.22))
                        .blur(radius: 18)
                        .scaleEffect(glowPulse ? 1.25 : 1.0)
                        .opacity(glowPulse ? 0.7 : 0.25)
                        .animation(.easeInOut(duration: 1.0).repeatForever(autoreverses: true), value: glowPulse)
                        .onAppear { glowPulse = true }
                }

                // Power-up sweep background
                PowerFillBackground(isOn: isOn, cornerRadius: 12)

                // Ripple ring on tap
                if ripple {
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(isOn ? Color.acruxAccent : Color.acruxTextSecondary, lineWidth: 2)
                        .scaleEffect(ripple ? 1.45 : 0.9)
                        .opacity(ripple ? 0 : 1)
                }

                // Spark particles
                ForEach(particles) { particle in
                    Circle()
                        .fill(particle.color)
                        .frame(width: particle.size, height: particle.size)
                        .offset(x: particle.x, y: particle.y)
                        .opacity(particle.opacity)
                        .scaleEffect(particle.scale)
                }

                // Content
                HStack(spacing: 10) {
                    if isLoading {
                        ProgressView()
                            .controlSize(.small)
                            .scaleEffect(0.8)
                            .tint(.primary)
                    } else {
                        Image(systemName: "power")
                            .font(.system(size: 16, weight: .black))
                            .foregroundStyle(isOn ? Color.acruxAccent : Color.acruxTextSecondary)
                            .rotationEffect(.degrees(iconRotation))
                            .scaleEffect(isOn ? 1.1 : 1.0)
                            .symbolEffect(.bounce, value: isOn)
                    }
                    Text(isOn ? "Go Offline" : "Go Online")
                        .font(.system(size: 13, weight: .bold))
                    Spacer()
                }
                .foregroundStyle(isOn ? Color.acruxAccent : .primary)
                .padding(.horizontal, 14)
                .padding(.vertical, 12)
            }
            .frame(height: 46)
            .clipped()
        }
        .buttonStyle(AcruxPowerButtonStyle())
        .disabled(isLoading)
        .onChange(of: isOn) { _, on in
            withAnimation(.spring(response: 0.55, dampingFraction: 0.68)) {
                iconRotation = on ? 360 : 0
            }
        }
    }

    private func handleTap() {
        spawnParticles()
        withAnimation(Theme.springSnappy) {
            ripple = true
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
            ripple = false
        }
        action()
    }

    private func spawnParticles() {
        let colors: [Color] = [.acruxAccent, .white, .acruxUserBubble]
        var newParticles: [PowerParticle] = []
        for i in 0..<16 {
            let angle = Double(i) * (2 * .pi / 16)
            let distance: CGFloat = 35 + CGFloat.random(in: 0...25)
            newParticles.append(PowerParticle(
                x: cos(angle) * distance,
                y: sin(angle) * distance,
                color: colors[i % colors.count],
                size: CGFloat.random(in: 3...7),
                delay: Double(i) * 0.01
            ))
        }
        particles = newParticles
        for (index, _) in newParticles.enumerated() {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.02 + Double(index) * 0.01) {
                withAnimation(.easeOut(duration: 0.5)) {
                    if index < particles.count {
                        particles[index].opacity = 0
                        particles[index].scale = 0
                    }
                }
            }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.7) {
            particles.removeAll()
        }
    }
}

struct AcruxPowerButtonStyle: ButtonStyle {
    @State private var hovering = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.94 : (hovering ? 1.04 : 1.0))
            .shadow(color: .black.opacity(hovering ? 0.55 : 0.3), radius: hovering ? 16 : 10, y: hovering ? 6 : 4)
            .animation(Theme.springPop, value: configuration.isPressed)
            .animation(Theme.springSnappy, value: hovering)
            .onHover { hovering = $0 }
    }
}

struct PowerParticle: Identifiable {
    let id = UUID()
    var x: CGFloat
    var y: CGFloat
    var color: Color
    var size: CGFloat
    var opacity: Double = 1
    var scale: CGFloat = 1
    var delay: Double
}

/// Animated power background: a rotating accent ring + sweeping light instead of liquid.
struct PowerFillBackground: View {
    let isOn: Bool
    let cornerRadius: CGFloat
    @State private var spinning = false
    @State private var sweep = false

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: cornerRadius)
                .fill(isOn ? Color.acruxAccent.opacity(0.10) : Color.acruxCard)

            if isOn {
                RoundedRectangle(cornerRadius: cornerRadius)
                    .stroke(
                        AngularGradient(
                            gradient: Gradient(colors: [
                                Color.acruxAccent.opacity(0.0),
                                Color.acruxAccent.opacity(0.7),
                                Color.acruxAccent.opacity(0.0)
                            ]),
                            center: .center
                        ),
                        lineWidth: 2
                    )
                    .rotationEffect(.degrees(spinning ? 360 : 0))
                    .animation(.linear(duration: 2.2).repeatForever(autoreverses: false), value: spinning)
                    .onAppear { spinning = true }

                GeometryReader { geo in
                    LinearGradient(
                        gradient: Gradient(colors: [
                            Color.acruxAccent.opacity(0.22),
                            Color.acruxAccent.opacity(0.0)
                        ]),
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                    .frame(width: geo.size.width * 0.7)
                    .offset(x: sweep ? geo.size.width * 0.5 : -geo.size.width * 0.7)
                    .animation(.easeInOut(duration: 1.6).repeatForever(autoreverses: true), value: sweep)
                    .onAppear { sweep = true }
                }
                .clipShape(RoundedRectangle(cornerRadius: cornerRadius))
            } else {
                RoundedRectangle(cornerRadius: cornerRadius)
                    .stroke(Color.acruxSubtleBorder, lineWidth: 1.5)
            }
        }
    }
}

struct SidebarButton: View {
    let tab: SidebarTab
    @Binding var selectedTab: SidebarTab
    @Binding var activeChatId: UUID?
    let selectionNamespace: Namespace.ID
    @State private var hovering = false

    var isSelected: Bool { tab == selectedTab && activeChatId == nil }

    var body: some View {
        Button {
            withAnimation(Theme.springSnappy) {
                activeChatId = nil
                selectedTab = tab
            }
        } label: {
            HStack(spacing: 12) {
                AnimatedSidebarIcon(tab: tab, hovering: hovering, selected: isSelected)
                    .frame(width: 22)
                Text(tab.rawValue)
                    .font(.system(size: 14, weight: .medium))
                Spacer()
            }
            .padding(.vertical, 10)
            .padding(.horizontal, 12)
            .background {
                if isSelected {
                    RoundedRectangle(cornerRadius: 10)
                        .fill(Color.acruxActive)
                        .matchedGeometryEffect(id: "sidebar-selection", in: selectionNamespace)
                        .shadow(color: .black.opacity(0.3), radius: 6, y: 2)
                } else if hovering {
                    RoundedRectangle(cornerRadius: 10)
                        .fill(Color.acruxElevated.opacity(0.6))
                }
            }
            .foregroundStyle(isSelected ? .primary : Color.acruxTextSecondary)
            .contentShape(RoundedRectangle(cornerRadius: 10))
        }
        .buttonStyle(.plain)
        .scaleEffect(hovering && !isSelected ? 1.02 : 1.0)
        .animation(Theme.easeQuick, value: hovering)
        .onHover { hovering = $0 }
        .ifLet(tab.keyboardShortcut) { view, shortcut in
            view.keyboardShortcut(shortcut)
        }
    }
}

/// House outline that draws itself on hover — roof, walls, door and chimney.
struct HouseShape: Shape {
    func path(in rect: CGRect) -> Path {
        var p = Path()
        let w = rect.width
        let h = rect.height
        let roofY = h * 0.35

        // Chimney
        p.move(to: CGPoint(x: w * 0.65, y: h * 0.15))
        p.addLine(to: CGPoint(x: w * 0.65, y: h * 0.05))
        p.addLine(to: CGPoint(x: w * 0.78, y: h * 0.05))
        p.addLine(to: CGPoint(x: w * 0.78, y: h * 0.22))

        // Roof
        p.move(to: CGPoint(x: w * 0.05, y: roofY))
        p.addLine(to: CGPoint(x: w * 0.5, y: h * 0.05))
        p.addLine(to: CGPoint(x: w * 0.95, y: roofY))

        // Left wall
        p.move(to: CGPoint(x: w * 0.2, y: roofY))
        p.addLine(to: CGPoint(x: w * 0.2, y: h * 0.95))

        // Bottom
        p.addLine(to: CGPoint(x: w * 0.8, y: h * 0.95))

        // Right wall
        p.addLine(to: CGPoint(x: w * 0.8, y: roofY))

        // Door
        p.move(to: CGPoint(x: w * 0.42, y: h * 0.95))
        p.addLine(to: CGPoint(x: w * 0.42, y: h * 0.62))
        p.addLine(to: CGPoint(x: w * 0.58, y: h * 0.62))
        p.addLine(to: CGPoint(x: w * 0.58, y: h * 0.95))

        return p
    }
}

/// Closed house silhouette for the fill behind the outline.
struct HouseFillShape: Shape {
    func path(in rect: CGRect) -> Path {
        var p = Path()
        let w = rect.width
        let h = rect.height
        let roofY = h * 0.35

        p.move(to: CGPoint(x: w * 0.05, y: roofY))
        p.addLine(to: CGPoint(x: w * 0.5, y: h * 0.05))
        p.addLine(to: CGPoint(x: w * 0.95, y: roofY))
        p.addLine(to: CGPoint(x: w * 0.8, y: roofY))
        p.addLine(to: CGPoint(x: w * 0.8, y: h * 0.95))
        p.addLine(to: CGPoint(x: w * 0.2, y: h * 0.95))
        p.addLine(to: CGPoint(x: w * 0.2, y: roofY))
        p.closeSubpath()

        return p
    }
}

struct AnimatedSidebarIcon: View {
    let tab: SidebarTab
    let hovering: Bool
    let selected: Bool
    @State private var housePhase: CGFloat = 1

    @ViewBuilder
    var body: some View {
        switch tab {
        case .home:
            ZStack {
                HouseFillShape()
                    .fill(selected ? Color.acruxAccent.opacity(0.22) : Color.acruxTextSecondary.opacity(0.14))
                    .frame(width: 20, height: 18)
                HouseShape()
                    .trim(from: 0, to: housePhase)
                    .stroke(selected ? Color.acruxAccent : Color.acruxTextSecondary, lineWidth: 2)
                    .frame(width: 20, height: 18)
            }
            .onChange(of: hovering) { _, new in
                if new {
                    housePhase = 0
                    withAnimation(.easeOut(duration: 0.45)) {
                        housePhase = 1
                    }
                } else {
                    housePhase = 1
                }
            }
        case .newTask:
            Image(systemName: tab.icon)
                .foregroundStyle(selected ? .primary : Color.acruxTextSecondary)
                .rotationEffect(.degrees(hovering ? 90 : 0))
                .scaleEffect(hovering ? 1.2 : 1.0)
                .animation(.spring(response: 0.4, dampingFraction: 0.6), value: hovering)
        case .chats:
            Image(systemName: tab.icon)
                .foregroundStyle(selected ? .primary : Color.acruxTextSecondary)
                .rotationEffect(.degrees(hovering ? 360 : 0))
                .animation(.spring(response: 0.6, dampingFraction: 0.7), value: hovering)
        case .memory:
            Image(systemName: tab.icon)
                .foregroundStyle(selected ? .primary : Color.acruxTextSecondary)
                .scaleEffect(hovering ? 1.25 : 1.0)
                .opacity(hovering ? 0.7 : 1.0)
                .animation(.easeInOut(duration: 0.18).repeatCount(3, autoreverses: true), value: hovering)
        case .knowledgeGraph:
            Image(systemName: tab.icon)
                .foregroundStyle(selected ? .primary : Color.acruxTextSecondary)
                .rotationEffect(.degrees(hovering ? 90 : 0))
                .scaleEffect(hovering ? 1.1 : 1.0)
                .animation(.spring(response: 0.5, dampingFraction: 0.6), value: hovering)
        case .importExport:
            Image(systemName: tab.icon)
                .foregroundStyle(selected ? .primary : Color.acruxTextSecondary)
                .offset(y: hovering ? -5 : 0)
                .animation(.spring(response: 0.35, dampingFraction: 0.5), value: hovering)
        case .health:
            Image(systemName: tab.icon)
                .foregroundStyle(selected ? .primary : Color.acruxTextSecondary)
                .scaleEffect(hovering ? 1.2 : 1.0)
                .rotationEffect(.degrees(hovering ? -10 : 0))
                .animation(.spring(response: 0.4, dampingFraction: 0.55), value: hovering)
        case .acruxStatus:
            Image(systemName: tab.icon)
                .foregroundStyle(selected ? .primary : Color.acruxTextSecondary)
                .scaleEffect(hovering ? 1.2 : 1.0)
                .animation(.easeInOut(duration: 0.22).repeatCount(3, autoreverses: true), value: hovering)
        }
    }
}

private extension View {
    @ViewBuilder
    func ifLet<T, Content: View>(_ value: T?, transform: (Self, T) -> Content) -> some View {
        if let value {
            transform(self, value)
        } else {
            self
        }
    }
}
