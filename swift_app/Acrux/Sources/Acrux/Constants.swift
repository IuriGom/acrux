import Foundation

enum Constants {
    static let backendHost = "127.0.0.1"
    static let backendPort = 11438
    static let backendURL = "http://\(backendHost):\(backendPort)"
    static let wsURL = "ws://\(backendHost):\(backendPort)"

    /// Acrux project directory (the repo/install root containing `.venv` and
    /// the `acrux` package). Resolution order:
    /// 1. `ACRUX_PROJECT_DIR` environment variable
    /// 2. Path written in `~/.acrux/project_dir` (set by the installer)
    /// 3. `~/.pia` when it contains a venv (install.sh default INSTALL_HOME)
    /// 4. `~/acrux` as a last resort
    static let acruxProjectDir: String = resolveProjectDir()

    private static func resolveProjectDir() -> String {
        if let env = ProcessInfo.processInfo.environment["ACRUX_PROJECT_DIR"], !env.isEmpty {
            return (env as NSString).expandingTildeInPath
        }
        let marker = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".acrux/project_dir")
        if let text = try? String(contentsOf: marker, encoding: .utf8) {
            let path = (text.trimmingCharacters(in: .whitespacesAndNewlines) as NSString)
                .expandingTildeInPath
            if !path.isEmpty {
                return path
            }
        }
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        let pia = "\(home)/.pia"
        if FileManager.default.fileExists(atPath: "\(pia)/.venv/bin/python") {
            return pia
        }
        return "\(home)/acrux"
    }
    static let pythonPath = ProcessInfo.processInfo.environment["ACRUX_PYTHON"] ?? "/usr/bin/env python3"
    static let appName = "Acrux"

    static var venvPythonPath: String {
        // Repo layout uses `.venv`, the installer layout uses `venv`.
        let dotVenv = "\(acruxProjectDir)/.venv/bin/python"
        if FileManager.default.fileExists(atPath: dotVenv) {
            return dotVenv
        }
        return "\(acruxProjectDir)/venv/bin/python"
    }

    static var venvPythonURL: URL {
        URL(fileURLWithPath: venvPythonPath)
    }

    static var pythonPathURL: URL {
        URL(fileURLWithPath: pythonPath)
    }

    static var projectURL: URL {
        URL(fileURLWithPath: acruxProjectDir)
    }
}
