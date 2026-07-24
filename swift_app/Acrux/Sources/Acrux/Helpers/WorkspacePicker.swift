import SwiftUI

@MainActor
struct WorkspacePicker {
    static func pick() -> String? {
        let panel = NSOpenPanel()
        panel.title = "Choose a workspace folder"
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.prompt = "Choose"

        guard panel.runModal() == .OK, let url = panel.url else { return nil }
        return url.path
    }
}
