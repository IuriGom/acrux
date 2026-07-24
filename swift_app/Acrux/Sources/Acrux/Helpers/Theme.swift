import SwiftUI

/// Graphite motion system — shared animation presets, button styles,
/// and animated primitives used across the app.
enum Theme {

    // MARK: - Animation presets

    /// Snappy spring for selection changes, hovers. response 0.35, damping 0.72
    static let springSnappy = Animation.spring(response: 0.35, dampingFraction: 0.72)

    /// Soft spring for message/card entrances. response 0.5, damping 0.78
    static let springEntrance = Animation.spring(response: 0.5, dampingFraction: 0.78)

    /// Bouncier spring for playful pops (send button, badges). response 0.45, damping 0.6
    static let springPop = Animation.spring(response: 0.45, dampingFraction: 0.6)

    /// Quick ease for fades. 0.18s
    static let easeQuick = Animation.easeInOut(duration: 0.18)

    /// Medium ease for view transitions. 0.28s
    static let easeMedium = Animation.easeInOut(duration: 0.28)
}

// MARK: - Entrance transition

extension AnyTransition {
    /// Spring entrance: fade + rise + slight scale-up.
    static var graphiteAppear: AnyTransition {
        .asymmetric(
            insertion: .opacity
                .combined(with: .offset(y: 14))
                .combined(with: .scale(scale: 0.97, anchor: .top)),
            removal: .opacity.combined(with: .scale(scale: 0.98))
        )
    }

    /// Fade + slide from the trailing edge (user messages).
    static var graphiteUser: AnyTransition {
        .opacity.combined(with: .offset(x: 18, y: 6)).combined(with: .scale(scale: 0.97, anchor: .bottomTrailing))
    }
}

// MARK: - Button styles

/// Lightweight row action button: only press-scale animation, no per-button hover state.
struct MemoryActionButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 12, weight: .medium))
            .padding(.vertical, 5)
            .padding(.horizontal, 8)
            .background(
                RoundedRectangle(cornerRadius: 7)
                    .fill(Color.acruxElevated.opacity(configuration.isPressed ? 0.85 : 0.0))
            )
            .scaleEffect(configuration.isPressed ? 0.92 : 1.0)
            .animation(Theme.springPop, value: configuration.isPressed)
    }
}

/// Ghost button on graphite: hover lift + background fade, springy press.
struct GraphiteButtonStyle: ButtonStyle {
    @State private var hovering = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .padding(.vertical, 8)
            .padding(.horizontal, 14)
            .background(
                RoundedRectangle(cornerRadius: 9)
                    .fill(Color.acruxElevated.opacity(configuration.isPressed ? 1.0 : (hovering ? 0.9 : 0.0)))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 9)
                    .stroke(Color.acruxAccent.opacity(hovering ? 0.5 : 0.0), lineWidth: 1.5)
                    .shadow(color: Color.acruxAccent.opacity(hovering ? 0.35 : 0.0), radius: 6)
            )
            .scaleEffect(configuration.isPressed ? 0.93 : 1.0)
            .offset(y: hovering && !configuration.isPressed ? -2 : 0)
            .shadow(color: .black.opacity(hovering ? 0.35 : 0.0), radius: hovering ? 10 : 0, y: hovering ? 4 : 0)
            .animation(Theme.springPop, value: configuration.isPressed)
            .animation(Theme.springSnappy, value: hovering)
            .onHover { hovering = $0 }
    }
}

/// Primary action: white fill, black glyph, spring press. Used for send/confirm.
struct GraphitePrimaryButtonStyle: ButtonStyle {
    @State private var hovering = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 13, weight: .bold))
            .padding(.vertical, 8)
            .padding(.horizontal, 16)
            .foregroundStyle(Color.acruxOnAccent)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(
                        LinearGradient(
                            colors: [
                                configuration.isPressed ? Color.acruxAccent.opacity(0.8) : Color.acruxAccent,
                                configuration.isPressed ? Color.acruxAccent.opacity(0.65) : Color.acruxAccent.opacity(0.85)
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .shadow(color: Color.acruxAccent.opacity(hovering ? 0.5 : 0.0), radius: hovering ? 14 : 0, y: 0)
                    .shadow(color: .black.opacity(hovering ? 0.5 : 0.3), radius: hovering ? 10 : 5, y: hovering ? 5 : 2)
            )
            .scaleEffect(configuration.isPressed ? 0.93 : (hovering ? 1.05 : 1.0))
            .offset(y: hovering && !configuration.isPressed ? -2 : 0)
            .animation(Theme.springPop, value: configuration.isPressed)
            .animation(Theme.springSnappy, value: hovering)
            .onHover { hovering = $0 }
    }
}

/// Icon-only button that spins the symbol continuously while hovered.
struct SpinIconButtonStyle: ButtonStyle {
    @State private var hovering = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .padding(6)
            .background(hovering ? Color.acruxElevated.opacity(0.6) : Color.clear)
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .scaleEffect(configuration.isPressed ? 0.85 : (hovering ? 1.12 : 1.0))
            .rotationEffect(.degrees(hovering ? 360 : 0))
            .animation(
                hovering ? .linear(duration: 0.7).repeatForever(autoreverses: false) : .default,
                value: hovering
            )
            .animation(Theme.springPop, value: configuration.isPressed)
            .onHover { hovering = $0 }
    }
}

/// Icon-only button: scales/rotates on press, lifts on hover.
struct AnimatedIconButtonStyle: ButtonStyle {
    @State private var hovering = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .padding(6)
            .background(hovering ? Color.acruxElevated.opacity(0.6) : Color.clear)
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .scaleEffect(configuration.isPressed ? 0.85 : (hovering ? 1.14 : 1.0))
            .rotationEffect(.degrees(configuration.isPressed ? -10 : 0))
            .symbolEffect(.variableColor, value: hovering)
            .animation(Theme.springPop, value: configuration.isPressed)
            .animation(Theme.springSnappy, value: hovering)
            .onHover { hovering = $0 }
    }
}

/// Circular action button (send/stop) with spring press and hover glow.
struct AnimatedCircularButtonStyle: ButtonStyle {
    @State private var hovering = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.88 : (hovering ? 1.1 : 1.0))
            .shadow(color: .black.opacity(hovering ? 0.5 : 0.35), radius: hovering ? 14 : 8, y: hovering ? 5 : 3)
            .animation(Theme.springPop, value: configuration.isPressed)
            .animation(Theme.springSnappy, value: hovering)
            .onHover { hovering = $0 }
    }
}

/// Elastic jelly button: squashes and bounces on press, lifts on hover.
struct ElasticButtonStyle: ButtonStyle {
    @State private var hovering = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .padding(.vertical, 8)
            .padding(.horizontal, 14)
            .background(
                RoundedRectangle(cornerRadius: 9)
                    .fill(Color.acruxElevated.opacity(configuration.isPressed ? 1.0 : (hovering ? 0.9 : 0.0)))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 9)
                    .stroke(Color.acruxAccent.opacity(hovering ? 0.5 : 0.0), lineWidth: 1.5)
            )
            .scaleEffect(
                x: configuration.isPressed ? 1.06 : (hovering ? 1.03 : 1.0),
                y: configuration.isPressed ? 0.88 : (hovering ? 1.03 : 1.0)
            )
            .offset(y: hovering && !configuration.isPressed ? -3 : 0)
            .shadow(color: .black.opacity(hovering ? 0.35 : 0.0), radius: hovering ? 12 : 0, y: hovering ? 4 : 0)
            .animation(.spring(response: 0.4, dampingFraction: 0.45), value: configuration.isPressed)
            .animation(Theme.springSnappy, value: hovering)
            .onHover { hovering = $0 }
    }
}

/// Pulsing primary button: glows and pulses on hover, bounces on press.
struct PulseButtonStyle: ButtonStyle {
    @State private var hovering = false
    @State private var pulse = false

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
                                configuration.isPressed ? Color.acruxAccent.opacity(0.8) : Color.acruxAccent,
                                configuration.isPressed ? Color.acruxAccent.opacity(0.65) : Color.acruxAccent.opacity(0.85)
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
            )
            .foregroundColor(.acruxOnAccent)
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(Color.white.opacity(hovering ? 0.3 : 0.0), lineWidth: 1.5)
            )
            .shadow(color: Color.acruxAccent.opacity(hovering ? 0.6 : 0.0), radius: hovering ? 24 : 0, y: 0)
            .shadow(color: .black.opacity(hovering ? 0.55 : 0.35), radius: hovering ? 22 : 14, x: 0, y: hovering ? 10 : 6)
            .scaleEffect(configuration.isPressed ? 0.92 : (hovering ? 1.04 : 1.0))
            .offset(y: hovering && !configuration.isPressed ? -2 : 0)
            .scaleEffect(pulse ? 1.02 : 1.0)
            .animation(.spring(response: 0.4, dampingFraction: 0.5), value: configuration.isPressed)
            .animation(Theme.springSnappy, value: hovering)
            .onHover { hovering = $0 }
            .onAppear {
                withAnimation(.easeInOut(duration: 0.9).repeatForever(autoreverses: true)) {
                    pulse = true
                }
            }
    }
}

/// Wiggle button: shakes on press, lifts on hover.
struct WiggleButtonStyle: ButtonStyle {
    @State private var hovering = false
    @State private var wiggle = 0.0

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .padding(.vertical, 8)
            .padding(.horizontal, 14)
            .background(
                RoundedRectangle(cornerRadius: 9)
                    .fill(Color.acruxElevated.opacity(configuration.isPressed ? 1.0 : (hovering ? 0.9 : 0.0)))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 9)
                    .stroke(Color.acruxAccent.opacity(hovering ? 0.5 : 0.0), lineWidth: 1.5)
            )
            .rotationEffect(.degrees(configuration.isPressed ? wiggle : (hovering ? 1.5 : 0)))
            .offset(y: hovering && !configuration.isPressed ? -2 : 0)
            .shadow(color: .black.opacity(hovering ? 0.35 : 0.0), radius: hovering ? 10 : 0, y: hovering ? 4 : 0)
            .animation(Theme.springPop, value: configuration.isPressed)
            .animation(Theme.springSnappy, value: hovering)
            .onHover { hovering = $0 }
            .onChange(of: configuration.isPressed) { _, pressed in
                if pressed {
                    withAnimation(.linear(duration: 0.08).repeatCount(5, autoreverses: true)) {
                        wiggle = 4
                    }
                } else {
                    wiggle = 0
                }
            }
    }
}

/// 3D flip button: flips slightly on press, lifts on hover.
struct FlipButtonStyle: ButtonStyle {
    @State private var hovering = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .padding(.vertical, 8)
            .padding(.horizontal, 14)
            .background(
                RoundedRectangle(cornerRadius: 9)
                    .fill(Color.acruxElevated.opacity(configuration.isPressed ? 1.0 : (hovering ? 0.9 : 0.0)))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 9)
                    .stroke(Color.acruxAccent.opacity(hovering ? 0.5 : 0.0), lineWidth: 1.5)
            )
            .rotation3DEffect(
                .degrees(configuration.isPressed ? 15 : (hovering ? 5 : 0)),
                axis: (x: 1, y: 0, z: 0)
            )
            .offset(y: hovering && !configuration.isPressed ? -2 : 0)
            .shadow(color: .black.opacity(hovering ? 0.35 : 0.0), radius: hovering ? 10 : 0, y: hovering ? 4 : 0)
            .animation(Theme.springPop, value: configuration.isPressed)
            .animation(Theme.springSnappy, value: hovering)
            .onHover { hovering = $0 }
    }
}

// MARK: - Shimmer (streaming reasoning, loading text)

struct ShimmerModifier: ViewModifier {
    @State private var phase: CGFloat = -1
    var active: Bool

    func body(content: Content) -> some View {
        content
            .overlay(
                GeometryReader { geo in
                    if active {
                        LinearGradient(
                            colors: [.clear, .white.opacity(0.35), .clear],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                        .frame(width: geo.size.width * 0.6)
                        .offset(x: phase * geo.size.width * 1.6)
                        .onAppear {
                            withAnimation(.linear(duration: 1.4).repeatForever(autoreverses: false)) {
                                phase = 1
                            }
                        }
                    }
                }
                .mask(content)
                .allowsHitTesting(false)
            )
    }
}

extension View {
    /// Sliding highlight used while a model is streaming reasoning.
    func shimmer(active: Bool) -> some View {
        modifier(ShimmerModifier(active: active))
    }
}

/// Symbol that spins continuously while `active`, otherwise resets.
struct RotatingSymbol: View {
    let systemName: String
    let active: Bool
    @State private var rotation: Double = 0

    var body: some View {
        Image(systemName: systemName)
            .rotationEffect(.degrees(rotation))
            .animation(active ? .linear(duration: 1.0).repeatForever(autoreverses: false) : .default, value: active)
            .onChange(of: active) { _, new in
                if new {
                    rotation += 360
                } else {
                    rotation = 0
                }
            }
    }
}

// MARK: - Pulsing status dot

struct PulsingDot: View {
    var color: Color = .acruxAccent
    var size: CGFloat = 8
    @State private var pulsing = false

    var body: some View {
        ZStack {
            Circle()
                .fill(color.opacity(0.35))
                .frame(width: size * 2.2, height: size * 2.2)
                .scaleEffect(pulsing ? 1.25 : 0.7)
                .opacity(pulsing ? 0.0 : 0.7)
            Circle()
                .fill(color)
                .frame(width: size, height: size)
        }
        .onAppear {
            withAnimation(.easeOut(duration: 1.6).repeatForever(autoreverses: false)) {
                pulsing = true
            }
        }
    }
}

// MARK: - Typing dots (generating indicator)

struct TypingDots: View {
    @State private var animating = false

    var body: some View {
        HStack(spacing: 5) {
            ForEach(0..<3, id: \.self) { i in
                Circle()
                    .fill(Color.acruxTextSecondary)
                    .frame(width: 6, height: 6)
                    .offset(y: animating ? -4 : 0)
                    .animation(
                        .easeInOut(duration: 0.5)
                            .repeatForever()
                            .delay(Double(i) * 0.15),
                        value: animating
                    )
            }
        }
        .onAppear { animating = true }
    }
}

// MARK: - Card modifier

extension View {
    /// Standard graphite card: surface, radius, soft shadow instead of a stroke.
    func graphiteCard(cornerRadius: CGFloat = 12) -> some View {
        self
            .background(Color.acruxCard)
            .clipShape(RoundedRectangle(cornerRadius: cornerRadius))
            .shadow(color: .black.opacity(0.35), radius: 8, y: 3)
    }

    /// Hover lift + background fill for list rows and tappable cards.
    func graphiteHoverRow(active: Bool = false) -> some View {
        modifier(GraphiteHoverRowModifier(active: active))
    }
}

struct GraphiteHoverRowModifier: ViewModifier {
    let active: Bool
    @State private var hovering = false

    func body(content: Content) -> some View {
        content
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(backgroundFill)
            )
            .scaleEffect(hovering ? 1.012 : 1.0)
            .offset(x: hovering ? 1.5 : 0)
            .animation(Theme.springSnappy, value: hovering)
            .animation(Theme.easeQuick, value: active)
            .onHover { hovering = $0 }
            .contentShape(Rectangle())
    }

    private var backgroundFill: Color {
        if active { return Color.acruxActive }
        return hovering ? Color.acruxElevated.opacity(0.7) : Color.clear
    }
}

/// Container that animates its content in once `appeared` becomes true.
/// Centralises entrance offsets / rotations / blur so large view bodies don't explode the type checker.
struct AnimatedSection<Content: View>: View {
    let appeared: Bool
    var delay: Double = 0
    var x: CGFloat = 0
    var y: CGFloat = 0
    var scale: CGFloat = 1.0
    var startScale: CGFloat = 1.0
    var rotation: Double = 0
    var blur: CGFloat = 0
    var response: Double = 0.6
    var damping: Double = 0.65
    @ViewBuilder let content: Content

    var body: some View {
        content
            .opacity(appeared ? 1 : 0)
            .offset(x: appeared ? 0 : x, y: appeared ? 0 : y)
            .scaleEffect(appeared ? scale : startScale)
            .rotationEffect(.degrees(appeared ? 0 : rotation))
            .blur(radius: appeared ? 0 : blur)
            .animation(.spring(response: response, dampingFraction: damping).delay(delay), value: appeared)
    }
}

/// Shimmer skeleton placeholder for loading rows.
struct SkeletonRow: View {
    var body: some View {
        HStack(spacing: 12) {
            RoundedRectangle(cornerRadius: 4)
                .fill(Color.acruxTextTertiary.opacity(0.25))
                .frame(width: 32, height: 32)
            VStack(alignment: .leading, spacing: 6) {
                RoundedRectangle(cornerRadius: 3)
                    .fill(Color.acruxTextTertiary.opacity(0.25))
                    .frame(width: 160, height: 10)
                RoundedRectangle(cornerRadius: 3)
                    .fill(Color.acruxTextTertiary.opacity(0.15))
                    .frame(width: 220, height: 8)
            }
            Spacer()
        }
        .padding(.vertical, 6)
        .shimmer(active: true)
    }
}

/// Animated checkmark used in Health / Status checks.
struct AnimatedCheckmark: View {
    @State private var drawn = false

    var body: some View {
        Circle()
            .stroke(Color.acruxAccent, lineWidth: 2)
            .frame(width: 20, height: 20)
            .overlay(
                Image(systemName: "checkmark")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(Color.acruxAccent)
                    .scaleEffect(drawn ? 1 : 0)
                    .opacity(drawn ? 1 : 0)
            )
            .onAppear {
                withAnimation(Theme.springPop.delay(0.1)) {
                    drawn = true
                }
            }
    }
}
