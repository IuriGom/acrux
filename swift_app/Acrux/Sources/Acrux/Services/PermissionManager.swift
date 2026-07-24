import Foundation
import AppKit

/// Detects and reports macOS privacy access issues for the Acrux project directory.
///
/// When Acrux.app is launched from the Dock or Finder it does not inherit the
/// terminal's TCC permissions. Python initialization hangs while listing files
/// in the project directory because the system blocks the read. We detect this
/// before launching the backend and explain how to fix it.
@MainActor
final class PermissionManager {
    static let shared = PermissionManager()

    private let projectURL = URL(fileURLWithPath: Constants.acruxProjectDir)

    /// Returns true if the app can already read the project directory.
    func hasAccess() -> Bool {
        let testFile = projectURL.appendingPathComponent("acrux/app/main.py")
        return (try? Data(contentsOf: testFile)) != nil
    }

    /// If access is missing, shows an alert with instructions and returns false.
    /// If access is present, returns true immediately.
    func ensureAccess() -> Bool {
        if hasAccess() { return true }
        showAccessAlert()
        return false
    }

    private func showAccessAlert() {
        let alert = NSAlert()
        alert.messageText = "Acrux needs permission to access its project folder"
        alert.informativeText = """
        The backend could not start because macOS is blocking access to:
        \(Constants.acruxProjectDir)

        To use Acrux from the Dock or Finder:
        1. Open System Settings → Privacy & Security → Full Disk Access
        2. Click the lock and add Acrux.app from ~/Applications
        3. Quit and reopen Acrux

        Until then, launch Acrux from Terminal with:
        open -a Terminal ~/Applications/Acrux.app/Contents/MacOS/Acrux
        """
        alert.alertStyle = .warning
        alert.addButton(withTitle: "Open System Settings")
        alert.addButton(withTitle: "OK")

        if alert.runModal() == .alertFirstButtonReturn {
            if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles") {
                NSWorkspace.shared.open(url)
            }
        }
    }
}
