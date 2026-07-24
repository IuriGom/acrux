# Graphite Redesign — Design Spec

Date: 2026-07-15
Status: Approved by user (picked option B "Graphite" in visual companion, explicitly asked for rich animations)

## Direction

Full-app visual redesign to **Graphite**: monochrome, dark, low-profile. Hierarchy from layered gray surfaces and soft shadows instead of borders. Zero chromatic accents in the chrome — emphasis comes from surface elevation, type weight, and motion.

## Design tokens

- `bg` #0E0F11 — deepest background (main content)
- `sidebar` #121316 — sidebar surface
- `surface1` #16181C — cards (tool cards, popups)
- `surface2` #1A1D22 — headers, composer, hover states
- `surface3` #1E2126 — active nav pill, pressed states
- `textPrimary` #F2F2F3
- `textSecondary` #868C94
- `textTertiary` #5D636B
- `accent` #C9CCD1 — toggles-on, active indicators (monochrome "accent")
- `onAccent` #101214 — text on accent fills (send button)
- user bubble: `surface3`-family #2A2E34, no colored fill
- danger/offline: desaturated warm gray, never bright red
- Corner radius: 12–14 cards/popups, 7–8 nav items, composer 14
- Shadows: soft black 0.3–0.4 opacity instead of strokes

Replaces: purple `Color(0.49,0.36,1.0)`, cyan `Color(0.0,0.83,1.0)`, navy backgrounds, radial purple glows. Knowledge Graph keeps its physics; node colors move to a grayscale ramp (white center → light gray projects → mid gray facts → dim episodes), labels unchanged.

## Animation system

Global presets in `Theme.swift`: `springSnappy` (0.35/0.7), `springBouncy` (0.5/0.6), `easeQuick` (0.18), plus a `Shimmer` modifier and `PulsingDot`.

- **Sidebar**: sliding selection pill (matchedGeometryEffect), hover fade
- **Chat**: messages spring in (fade + rise + 0.96→1 scale), staggered; reasoning block shimmers while streaming; tool cards slide in, subtle pulse while running, result fades in; typing dots while generating
- **Composer**: focus ring fade, send button morphs arrow→stop with spring
- **Tabs (chat tabs + main tabs)**: sliding indicator, content fade/slide
- **Popups**: spring scale 0.92→1 + fade entrance (existing dismissal kept)
- **Health/Status**: animated checkmark draw, pulsing status dot
- **Buttons**: shared `GraphiteButtonStyle` — hover lift, 0.97 press scale
- **Home**: staggered card entrances

## Files

New: `Sources/Acrux/Theme.swift`.
Swept: SidebarView, ChatView, ChatTabsView, MessageRow, NewTaskView, HomeView, KnowledgeGraphView, MemoryInspectorView + Memory* views, HealthCheckView, AcruxStatusView, ImportExportView, PastChatsView, DismissablePopup, FloatingAcruxWidget, AcruxStatusBarController, and remaining views for hardcoded purple/cyan.

## Non-goals

No layout/IA changes, no feature work, no backend changes. Visual language + motion only.
