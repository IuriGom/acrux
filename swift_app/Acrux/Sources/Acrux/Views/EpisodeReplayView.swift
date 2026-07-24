import SwiftUI

struct EpisodeReplayView: View {
    let sessionId: String
    let workspace: String?

    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject var acrux: AcruxService

    @State private var status: ReplayStatus?
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var autoApproveRemaining = false
    @State private var showAbortConfirmation = false
    @State private var pollTask: Task<Void, Never>?

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            header
            Divider()
            if let status {
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        statusSection(status)
                        if let action = status.originalAction {
                            actionSection(action)
                        }
                        if let output = status.outputPreview, !output.isEmpty {
                            outputSection(output)
                        }
                        if let diff = status.diff, !diff.isEmpty, diff != "(no difference)" {
                            diffSection(diff)
                        }
                        if let warnings = status.warnings, !warnings.isEmpty {
                            warningsSection(warnings)
                        }
                    }
                    .padding()
                }
                controlBar(status)
            } else {
                Spacer()
                ContentUnavailableView {
                    Label("Loading replay", systemImage: "clock.arrow.circlepath")
                } description: {
                    Text("Fetching replay status…")
                }
                Spacer()
            }
        }
        .frame(minWidth: 700, minHeight: 500)
        .task {
            await startReplay()
            beginPolling()
        }
        .onDisappear {
            pollTask?.cancel()
        }
        .alert("Error", isPresented: .constant(errorMessage != nil), presenting: errorMessage) { _ in
            Button("OK") { errorMessage = nil }
        } message: { message in
            Text(message)
        }
        .confirmationDialog("Abort replay?", isPresented: $showAbortConfirmation, titleVisibility: .visible) {
            Button("Abort", role: .destructive) {
                Task { await abort() }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This will stop the replay session without saving a new episode.")
        }
    }

    private var header: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("Episode Replay")
                    .font(.system(size: 22, weight: .bold))
                if let status {
                    Text("Step \(status.currentStep) of \(status.totalSteps)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            Spacer()
            Button {
                Task { await refreshStatus() }
            } label: {
                Image(systemName: "arrow.clockwise")
            }
            .buttonStyle(GraphiteButtonStyle())
            .disabled(isLoading)
            Button {
                dismiss()
            } label: {
                Text("Close")
            }
            .buttonStyle(GraphiteButtonStyle())
        }
        .padding()
    }

    @ViewBuilder
    private func statusSection(_ status: ReplayStatus) -> some View {
        HStack(spacing: 12) {
            StatusBadge(status: status.status)
            if status.gitCheckoutOk == true {
                Label("Git commit restored", systemImage: "checkmark.circle")
                    .font(.caption)
                    .foregroundStyle(.green)
            }
            Spacer()
        }
        if let message = status.message, !message.isEmpty {
            Text(message)
                .font(.callout)
                .foregroundStyle(.secondary)
        }
    }

    @ViewBuilder
    private func actionSection(_ action: ReplayAction) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Proposed Action")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(.secondary)
            HStack {
                Text(action.tool)
                    .font(.system(size: 12, weight: .bold))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.accentColor.opacity(0.15))
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                Spacer()
            }
            if !action.target.isEmpty {
                LabeledField(label: "Target", value: action.target)
            }
            if !action.command.isEmpty {
                LabeledField(label: "Command", value: action.command)
            }
            if !action.result.isEmpty {
                LabeledField(label: "Original Result", value: action.result)
                    .foregroundStyle(.secondary)
            }
        }
        .padding()
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    @ViewBuilder
    private func outputSection(_ output: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Output Preview")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(.secondary)
            ScrollView {
                Text(output)
                    .font(.system(size: 12, design: .monospaced))
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(maxHeight: 160)
        }
        .padding()
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    @ViewBuilder
    private func diffSection(_ diff: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Diff from Original")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(.secondary)
            ScrollView {
                Text(diff)
                    .font(.system(size: 12, design: .monospaced))
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(maxHeight: 200)
        }
        .padding()
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    @ViewBuilder
    private func warningsSection(_ warnings: [String]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Warnings")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(.orange)
            ForEach(warnings, id: \.self) { warning in
                HStack(alignment: .top, spacing: 6) {
                    Image(systemName: "exclamationmark.triangle")
                        .foregroundStyle(.orange)
                    Text(warning)
                        .font(.callout)
                }
            }
        }
        .padding()
        .background(.orange.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private func controlBar(_ status: ReplayStatus) -> some View {
        HStack(spacing: 12) {
            if status.status == "completed" {
                Label("Replay Complete", systemImage: "checkmark.circle.fill")
                    .foregroundStyle(.green)
                if let outcome = status.outcome {
                    Text(outcome)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
                Spacer()
                Button("Done") { dismiss() }
                    .buttonStyle(GraphitePrimaryButtonStyle())
            } else if status.status == "aborted" {
                Label("Replay Aborted", systemImage: "xmark.octagon.fill")
                    .foregroundStyle(.red)
                Spacer()
                Button("Done") { dismiss() }
                    .buttonStyle(GraphitePrimaryButtonStyle())
            } else {
                Toggle("Auto-approve remaining", isOn: $autoApproveRemaining)
                    .toggleStyle(.switch)
                Spacer()
                if status.status == "waiting" {
                    Button {
                        Task { await restoreCommit() }
                    } label: {
                        Label("Restore Commit", systemImage: "arrow.uturn.backward")
                    }
                    .buttonStyle(GraphiteButtonStyle())
                    Button {
                        Task { await startReplay(force: true) }
                    } label: {
                        Label("Force Start", systemImage: "play.fill")
                    }
                    .buttonStyle(GraphitePrimaryButtonStyle())
                } else {
                    Button {
                        showAbortConfirmation = true
                    } label: {
                        Label("Abort", systemImage: "stop.fill")
                    }
                    .buttonStyle(GraphiteButtonStyle())
                    Button {
                        Task { await step() }
                    } label: {
                        Label(status.requiresApproval ? "Approve Step" : "Run Step", systemImage: "play.fill")
                    }
                    .buttonStyle(GraphitePrimaryButtonStyle())
                    .disabled(isLoading)
                }
            }
        }
        .padding()
        .background(.ultraThinMaterial)
    }

    private func startReplay(force: Bool = false) async {
        isLoading = true
        defer { isLoading = false }
        status = await acrux.startReplay(sessionId: sessionId, workspace: workspace, force: force, autoApprove: autoApproveRemaining)
        if status == nil {
            errorMessage = "Could not start replay."
        }
    }

    private func refreshStatus() async {
        status = await acrux.fetchReplayStatus(sessionId: sessionId)
    }

    private func step() async {
        isLoading = true
        defer { isLoading = false }
        let newStatus = await acrux.stepReplay(sessionId: sessionId, autoApprove: autoApproveRemaining)
        if let newStatus {
            status = newStatus
            if newStatus.status == "completed" {
                pollTask?.cancel()
            }
        } else {
            errorMessage = "Step failed."
        }
    }

    private func abort() async {
        if await acrux.abortReplay(sessionId: sessionId) {
            pollTask?.cancel()
            await refreshStatus()
        } else {
            errorMessage = "Could not abort replay."
        }
    }

    private func restoreCommit() async {
        let newStatus = await acrux.restoreReplayCommit(sessionId: sessionId)
        if let newStatus {
            status = newStatus
        } else {
            errorMessage = "Could not restore original commit."
        }
    }

    private func beginPolling() {
        guard status?.status != "completed" && status?.status != "aborted" else { return }
        pollTask?.cancel()
        pollTask = Task {
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 2_000_000_000)
                if Task.isCancelled { break }
                await refreshStatus()
                if let status, status.status == "completed" || status.status == "aborted" {
                    break
                }
            }
        }
    }
}

private struct StatusBadge: View {
    let status: String

    var body: some View {
        Text(status.capitalized)
            .font(.system(size: 12, weight: .bold))
            .padding(.horizontal, 10)
            .padding(.vertical, 5)
            .foregroundStyle(statusColor)
            .background(statusColor.opacity(0.12))
            .clipShape(Capsule())
    }

    private var statusColor: Color {
        switch status {
        case "running": return .blue
        case "completed": return .green
        case "aborted": return .red
        case "waiting", "waiting_approval": return .orange
        default: return .secondary
        }
    }
}

private struct LabeledField: View {
    let label: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.system(size: 11, weight: .medium))
                .foregroundStyle(.secondary)
            Text(value)
                .font(.system(size: 12, design: .monospaced))
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}
