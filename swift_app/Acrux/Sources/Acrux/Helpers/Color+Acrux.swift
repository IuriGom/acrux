import SwiftUI

extension Color {
    // MARK: - Graphite palette (monochrome, layered grays)

    /// Deepest background — main content areas. #0E0F11
    static var acruxBg: Color { Color(red: 0.055, green: 0.059, blue: 0.067) }

    /// Sidebar surface. #121316
    static var acruxSidebar: Color { Color(red: 0.071, green: 0.075, blue: 0.086) }

    /// Cards, tool rows, popups. #16181C
    static var acruxCard: Color { Color(red: 0.086, green: 0.094, blue: 0.110) }

    /// Headers, composer, hover states. #1A1D22
    static var acruxElevated: Color { Color(red: 0.102, green: 0.114, blue: 0.133) }

    /// Active nav pill, pressed states, user bubble. #1E2126
    static var acruxActive: Color { Color(red: 0.118, green: 0.129, blue: 0.149) }

    /// User message bubble. #2A2E34
    static var acruxUserBubble: Color { Color(red: 0.165, green: 0.180, blue: 0.204) }

    /// Monochrome accent — toggles-on, active indicators, primary fills. #C9CCD1
    static var acruxAccent: Color { Color(red: 0.788, green: 0.800, blue: 0.820) }

    /// Text/icons on accent fills. #101214
    static var acruxOnAccent: Color { Color(red: 0.063, green: 0.071, blue: 0.078) }

    /// Secondary text. #868C94
    static var acruxTextSecondary: Color { Color(red: 0.525, green: 0.549, blue: 0.580) }

    /// Tertiary text, placeholders. #5D636B
    static var acruxTextTertiary: Color { Color(red: 0.365, green: 0.388, blue: 0.420) }

    // MARK: - Adaptive surfaces (kept for existing call sites)

    /// A subtle adaptive surface color that works in both light and dark mode.
    static var acruxSurface: Color {
        Color.primary.opacity(0.12)
    }

    /// A slightly stronger adaptive surface for cards and tool rows.
    static var acruxSecondarySurface: Color {
        Color.primary.opacity(0.16)
    }

    /// Adaptive border color that is visible on both light and dark backgrounds.
    static var acruxBorder: Color {
        Color.primary.opacity(0.22)
    }

    /// Adaptive subtle border for lower-contrast separators.
    static var acruxSubtleBorder: Color {
        Color.primary.opacity(0.14)
    }

    /// Background for assistant message bubbles.
    static var acruxAssistantBubble: Color {
        Color.primary.opacity(0.10)
    }

    /// Background for reasoning panels.
    static var acruxReasoningBackground: Color {
        Color.primary.opacity(0.08)
    }

    /// Background for code blocks.
    static var acruxCodeBackground: Color {
        Color.primary.opacity(0.14)
    }

    /// Background for the bottom input bar.
    static var acruxInputBarBackground: Color {
        Color.primary.opacity(0.08)
    }

    /// Overlay for command palette and modal backdrops.
    static var acruxOverlay: Color {
        Color.black.opacity(0.45)
    }
}
