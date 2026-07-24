import SwiftUI

struct CodeBlock: Identifiable {
    let id = UUID()
    let language: String
    let code: String
}

struct CodeBlockView: View {
    let blocks: [CodeBlock]
    let onRun: ((String) -> Void)?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            ForEach(blocks) { block in
                VStack(alignment: .leading, spacing: 0) {
                    HStack {
                        Text(block.language.isEmpty ? "code" : block.language)
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(.secondary)
                            .textCase(.uppercase)
                        Spacer()
                        if let onRun {
                            Button {
                                onRun(block.code)
                            } label: {
                                Label("Run", systemImage: "play.fill")
                                    .font(.system(size: 11, weight: .semibold))
                            }
                            .buttonStyle(AnimatedIconButtonStyle())
                            .foregroundStyle(Color.acruxAccent)
                        }
                        Button {
                            copy(block.code)
                        } label: {
                            Label("Copy", systemImage: "doc.on.doc")
                                .font(.system(size: 11, weight: .semibold))
                        }
                        .buttonStyle(AnimatedIconButtonStyle())
                        .foregroundStyle(.secondary)
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(Color.acruxCodeBackground)

                    Text(block.code)
                        .font(.system(size: 12, design: .monospaced))
                        .padding(10)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color.acruxSurface)
                }
                .background(Color.acruxSurface)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(Color.acruxSubtleBorder, lineWidth: 1)
                )
                .clipShape(RoundedRectangle(cornerRadius: 12))
            }
        }
    }

    private func copy(_ text: String) {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(text, forType: .string)
    }
}

extension String {
    func extractCodeBlocks() -> [CodeBlock] {
        let pattern = "```([\\w]*)(?:\\r?\\n)?(.*?)```"
        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.dotMatchesLineSeparators]) else { return [] }
        let ns = self as NSString
        var blocks: [CodeBlock] = []
        for match in regex.matches(in: self, options: [], range: NSRange(location: 0, length: ns.length)) {
            let lang = match.range(at: 1).location != NSNotFound ? ns.substring(with: match.range(at: 1)) : ""
            let code = match.range(at: 2).location != NSNotFound ? ns.substring(with: match.range(at: 2)) : ""
            blocks.append(CodeBlock(language: lang.trimmingCharacters(in: .whitespacesAndNewlines),
                                    code: code.trimmingCharacters(in: .whitespacesAndNewlines)))
        }
        return blocks
    }

    func removingCodeBlocks() -> String {
        let pattern = "```[\\w]*(?:\\r?\\n)?.*?```"
        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.dotMatchesLineSeparators]) else { return self }
        let ns = self as NSString
        let mutable = NSMutableString(string: self)
        let matches = regex.matches(in: self, options: [], range: NSRange(location: 0, length: ns.length))
        for match in matches.reversed() {
            mutable.replaceCharacters(in: match.range, with: "")
        }
        return mutable as String
    }
}
