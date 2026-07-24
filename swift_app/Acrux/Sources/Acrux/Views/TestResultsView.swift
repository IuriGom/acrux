import SwiftUI

struct TestResultsView: View {
    let project: String
    @State private var results: [TestResult] = []
    @State private var isLoading = false

    var passRate: String {
        let total = results.count
        let passed = results.filter(\.passed).count
        guard total > 0 else { return "—" }
        return String(format: "%d/%d (%.0f%%)", passed, total, Double(passed) / Double(total) * 100)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Tests: \(passRate)")
                    .font(.system(size: 18, weight: .bold))
                Spacer()
                Button {
                    Task { await load() }
                } label: {
                    Image(systemName: "arrow.clockwise")
                }
                .buttonStyle(GraphiteButtonStyle())
            }
            .padding()

            if isLoading {
                ProgressView()
                    .padding()
            } else if results.isEmpty {
                ContentUnavailableView("No tests", systemImage: "checkmark.seal", description: Text("No test results recorded for this project."))
            } else {
                List(results) { test in
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Image(systemName: test.passed ? "checkmark.circle.fill" : "xmark.circle.fill")
                                .foregroundStyle(test.passed ? .green : .red)
                            Text(test.testName)
                                .font(.system(size: 14, weight: .semibold))
                            Spacer()
                            Text(test.runAt, style: .date)
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                        if let path = test.filePath {
                            Text(path)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        if let rootCause = test.rootCause {
                            Text("Root cause: \(rootCause)")
                                .font(.caption)
                                .foregroundStyle(.red)
                        }
                        if let output = test.output, !output.isEmpty {
                            Text(output)
                                .font(.system(size: 11, design: .monospaced))
                                .lineLimit(4)
                                .padding(8)
                                .background(Color.acruxCodeBackground)
                                .clipShape(RoundedRectangle(cornerRadius: 8))
                        }
                    }
                    .padding(10)
                    .background(.ultraThinMaterial)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                    .listRowBackground(Color.clear)
                    .listRowSeparator(.hidden)
                }
                .scrollContentBackground(.hidden)
            }
        }
        .frame(minWidth: 420, minHeight: 400)
        .task { await load() }
    }

    private func load() async {
        guard let service = AcruxServiceReference.shared else { return }
        isLoading = true
        results = await service.fetchTestResults(project: project)
        isLoading = false
    }
}
