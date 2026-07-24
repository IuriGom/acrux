import SwiftUI

struct GitPill: View {
    let label: String?

    var body: some View {
        if let label, !label.isEmpty {
            Text(label)
                .font(.system(size: 10, weight: .semibold, design: .monospaced))
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(Color.orange.opacity(0.15))
                .foregroundStyle(.orange)
                .clipShape(Capsule())
                .overlay(
                    Capsule()
                        .stroke(Color.orange.opacity(0.3), lineWidth: 1)
                )
        }
    }
}

struct ConfidenceBadge: View {
    let confidence: Double?
    let stale: Bool?

    private var level: (text: String, color: Color) {
        guard let confidence else { return ("—", .secondary) }
        let percent = Int((confidence * 100).rounded())
        if stale == true {
            return ("\(percent)%", .gray)
        } else if confidence >= 0.8 {
            return ("\(percent)%", .green)
        } else if confidence >= 0.5 {
            return ("\(percent)%", .yellow)
        } else {
            return ("\(percent)%", .red)
        }
    }

    var body: some View {
        HStack(spacing: 4) {
            Text(level.text)
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(level.color)
            if stale == true {
                Text("STALE")
                    .font(.system(size: 9, weight: .bold))
                    .foregroundStyle(.gray)
            }
        }
        .padding(.horizontal, 6)
        .padding(.vertical, 2)
        .background(level.color.opacity(0.12))
        .clipShape(Capsule())
        .overlay(
            Capsule()
                .stroke(level.color.opacity(0.25), lineWidth: 1)
        )
    }
}

struct TagChips: View {
    let tags: [String]

    var body: some View {
        if !tags.isEmpty {
            FlowLayout(spacing: 6) {
                ForEach(Array(tags.enumerated()), id: \.element) { index, tag in
                    Text(tag)
                        .font(.system(size: 10, weight: .medium))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.blue.opacity(0.12))
                        .foregroundStyle(.blue)
                        .clipShape(Capsule())
                        .transition(.asymmetric(
                            insertion: .scale.combined(with: .opacity),
                            removal: .opacity
                        ))
                }
            }
        }
    }
}

struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let result = FlowResult(in: proposal.width ?? .infinity, subviews: subviews, spacing: spacing)
        return result.size
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = FlowResult(in: bounds.width, subviews: subviews, spacing: spacing)
        for (index, subview) in subviews.enumerated() {
            subview.place(at: CGPoint(x: bounds.minX + result.positions[index].x,
                                      y: bounds.minY + result.positions[index].y),
                          proposal: .unspecified)
        }
    }

    private struct FlowResult {
        var size: CGSize = .zero
        var positions: [CGPoint] = []

        init(in maxWidth: CGFloat, subviews: Subviews, spacing: CGFloat) {
            var x: CGFloat = 0
            var y: CGFloat = 0
            var rowHeight: CGFloat = 0

            for subview in subviews {
                let size = subview.sizeThatFits(.unspecified)
                if x + size.width > maxWidth, x > 0 {
                    x = 0
                    y += rowHeight + spacing
                    rowHeight = 0
                }
                positions.append(CGPoint(x: x, y: y))
                x += size.width + spacing
                rowHeight = max(rowHeight, size.height)
            }

            self.size = CGSize(width: maxWidth > 0 ? min(maxWidth, x) : x,
                               height: y + rowHeight)
        }
    }
}
