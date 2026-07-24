import SwiftUI

struct InlineDiffView: View {
    let diff: String
    var onAccept: (() -> Void)?
    var onReject: (() -> Void)?

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Suggested changes")
                    .font(.system(size: 13, weight: .semibold))
                Spacer()
                if let onAccept {
                    Button("Accept") { onAccept() }
                        .buttonStyle(ToolButtonStyle(color: .green))
                }
                if let onReject {
                    Button("Reject") { onReject() }
                        .buttonStyle(ToolButtonStyle(color: .red))
                }
            }
            .padding(10)
            .background(Color.acruxSurface)

            ScrollView(.horizontal, showsIndicators: true) {
                VStack(alignment: .leading, spacing: 0) {
                    ForEach(parsedLines, id: \.self) { line in
                        HStack(spacing: 0) {
                            Text(line.prefix)
                                .font(.system(size: 12, design: .monospaced))
                                .foregroundStyle(color(for: line))
                                .frame(width: 24, alignment: .center)
                            Text(line.text)
                                .font(.system(size: 12, design: .monospaced))
                                .foregroundStyle(.primary)
                                .padding(.leading, 6)
                            Spacer(minLength: 20)
                        }
                        .padding(.vertical, 1)
                        .background(background(for: line))
                    }
                }
                .padding(.horizontal, 6)
                .padding(.vertical, 8)
            }
        }
        .background(Color.acruxCodeBackground)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.acruxSubtleBorder, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private struct DiffLine: Hashable {
        let prefix: String
        let text: String
    }

    private var parsedLines: [DiffLine] {
        diff.components(separatedBy: .newlines).map { raw in
            let prefix = String(raw.prefix(1))
            let text = String(raw.dropFirst())
            return DiffLine(prefix: prefix, text: text)
        }
    }

    private func color(for line: DiffLine) -> Color {
        switch line.prefix {
        case "+": return .green
        case "-": return .red
        case "@": return Color.acruxAccent
        default: return .secondary
        }
    }

    private func background(for line: DiffLine) -> Color {
        switch line.prefix {
        case "+": return Color.green.opacity(0.08)
        case "-": return Color.red.opacity(0.08)
        case "@": return Color.acruxAccent.opacity(0.08)
        default: return Color.clear
        }
    }
}

extension String {
    func containsDiff() -> Bool {
        trimmingCharacters(in: .whitespacesAndNewlines).hasPrefix("--- ") ||
            trimmingCharacters(in: .whitespacesAndNewlines).hasPrefix("@@")
    }

    func extractDiff() -> String? {
        let marker = "```diff"
        if let start = range(of: marker) {
            let after = self[start.upperBound...]
            if let end = after.range(of: "```") {
                return String(after[..<end.lowerBound]).trimmingCharacters(in: .whitespacesAndNewlines)
            }
        }
        if containsDiff() { return self }
        return nil
    }
}
