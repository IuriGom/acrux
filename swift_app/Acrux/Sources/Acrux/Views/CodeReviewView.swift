import SwiftUI

struct CodeReviewView: View {
    let project: String
    @State private var reviews: [CodeReview] = []
    @State private var isLoading = false
    @State private var newFilePath = ""
    @State private var newLineRange = ""
    @State private var newComment = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Code reviews")
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

            HStack(spacing: 10) {
                TextField("File path", text: $newFilePath)
                    .textFieldStyle(.plain)
                    .frame(minWidth: 160)
                TextField("Lines", text: $newLineRange)
                    .textFieldStyle(.plain)
                    .frame(width: 80)
                TextField("Comment", text: $newComment)
                    .textFieldStyle(.plain)
                Button("Add") {
                    Task { await add() }
                }
                .buttonStyle(GraphitePrimaryButtonStyle())
                .disabled(newFilePath.isEmpty || newComment.isEmpty)
            }
            .padding()
            .background(.ultraThinMaterial)

            if isLoading {
                ProgressView()
                    .padding()
            } else if reviews.isEmpty {
                ContentUnavailableView("No reviews", systemImage: "checkmark.bubble", description: Text("No review comments recorded."))
            } else {
                List(reviews) { review in
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Text(review.filePath)
                                .font(.system(size: 13, weight: .semibold))
                            if let range = review.lineRange, !range.isEmpty {
                                Text("lines \(range)")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            if let resolution = review.resolution {
                                Text(resolution.uppercased())
                                    .font(.system(size: 9, weight: .bold))
                                    .foregroundStyle(resolution == "accepted" ? .green : (resolution == "rejected" ? .red : .yellow))
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(color(for: resolution).opacity(0.12))
                                    .clipShape(Capsule())
                            }
                        }
                        Text(review.comment)
                            .font(.system(size: 13))
                        if let reviewer = review.reviewer {
                            Text("By \(reviewer)")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
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
        .frame(minWidth: 500, minHeight: 400)
        .task { await load() }
    }

    private func load() async {
        guard let service = AcruxServiceReference.shared else { return }
        isLoading = true
        reviews = await service.fetchReviews(project: project)
        isLoading = false
    }

    private func add() async {
        guard let service = AcruxServiceReference.shared else { return }
        let request = AddReviewRequest(filePath: newFilePath, lineRange: newLineRange.isEmpty ? nil : newLineRange, comment: newComment, reviewer: "user")
        if await service.addReview(project: project, request: request) {
            newFilePath = ""
            newLineRange = ""
            newComment = ""
            await load()
        }
    }

    private func color(for resolution: String) -> Color {
        switch resolution {
        case "accepted": return .green
        case "rejected": return .red
        default: return .yellow
        }
    }
}
