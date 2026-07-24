import SwiftUI

/// A sine-wave shape that fills a rectangle up to `fillLevel` (0...1).
/// The wave crest moves with `phase`, giving a liquid effect.
struct WaveShape: Shape {
    var fillLevel: CGFloat
    var phase: Double
    var waveCount: CGFloat = 1.5
    var amplitude: CGFloat = 6

    var animatableData: CGFloat {
        get { fillLevel }
        set { fillLevel = newValue }
    }

    func path(in rect: CGRect) -> Path {
        var path = Path()
        let waterHeight = rect.height * fillLevel
        let baseY = rect.maxY - waterHeight

        path.move(to: CGPoint(x: rect.minX, y: rect.maxY))
        path.addLine(to: CGPoint(x: rect.minX, y: baseY))

        let width = rect.width
        let steps = max(Int(width / 4), 20)
        for i in 0...steps {
            let x = width * CGFloat(i) / CGFloat(steps)
            let relativeX = CGFloat(i) / CGFloat(steps)
            let y = baseY + sin((relativeX * .pi * 2 * waveCount) + CGFloat(phase)) * amplitude
            path.addLine(to: CGPoint(x: x, y: y))
        }

        path.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY))
        path.closeSubpath()
        return path
    }
}

/// Background for a button that fills with an animated liquid wave when `isOn`.
struct LiquidFillBackground: View {
    let isOn: Bool
    let accent: Color
    let cornerRadius: CGFloat
    @State private var fillLevel: CGFloat = 0
    @State private var phase: Double = 0

    var body: some View {
        GeometryReader { geo in
            ZStack {
                // Static base fill (subtle) when on
                if isOn {
                    RoundedRectangle(cornerRadius: cornerRadius)
                        .fill(accent.opacity(0.12))
                }

                // Animated wave fill
                WaveShape(
                    fillLevel: fillLevel,
                    phase: phase,
                    waveCount: 1.2,
                    amplitude: min(geo.size.height * 0.12, 8)
                )
                .fill(accent.opacity(0.35))
                .clipShape(RoundedRectangle(cornerRadius: cornerRadius))
                .animation(.spring(response: 0.7, dampingFraction: 0.72), value: fillLevel)
            }
        }
        .onAppear {
            fillLevel = isOn ? 1.0 : 0.0
            if isOn { startWaving() }
        }
        .onChange(of: isOn) { _, on in
            withAnimation(.spring(response: 0.7, dampingFraction: 0.72)) {
                fillLevel = on ? 1.0 : 0.0
            }
            if on { startWaving() }
        }
    }

    private func startWaving() {
        withAnimation(.linear(duration: 1.6).repeatForever(autoreverses: false)) {
            phase += .pi * 2
        }
    }
}

/// Button style that puts an animated liquid fill behind the label.
struct LiquidButtonStyle: ButtonStyle {
    let isOn: Bool
    let accent: Color
    let cornerRadius: CGFloat = 12
    @State private var hovering = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .padding(.vertical, 12)
            .padding(.horizontal, 14)
            .background(
                ZStack {
                    LiquidFillBackground(isOn: isOn, accent: accent, cornerRadius: cornerRadius)
                    RoundedRectangle(cornerRadius: cornerRadius)
                        .stroke(isOn ? accent.opacity(0.7) : Color.acruxSubtleBorder, lineWidth: 1.5)
                }
            )
            .scaleEffect(configuration.isPressed ? 0.94 : (hovering ? 1.03 : 1.0))
            .shadow(color: .black.opacity(hovering ? 0.5 : 0.3), radius: hovering ? 14 : 8, y: hovering ? 5 : 3)
            .animation(Theme.springPop, value: configuration.isPressed)
            .animation(Theme.springSnappy, value: hovering)
            .onHover { hovering = $0 }
    }
}
