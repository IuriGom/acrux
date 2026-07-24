import Foundation

enum Constants {
    static let backendHost = "127.0.0.1"
    static let backendPort = 11438
    static let backendURL = "http://\(backendHost):\(backendPort)"
    static let wsURL = "ws://\(backendHost):\(backendPort)"

    static let acruxProjectDir = ProcessInfo.processInfo.environment["ACRUX_PROJECT_DIR"] ?? "~/acrux"
    static let pythonPath = ProcessInfo.processInfo.environment["ACRUX_PYTHON"] ?? "/usr/bin/env python3"
    static let appName = "Acrux"

    static var venvPythonPath: String {
        "\(acruxProjectDir)/.venv/bin/python"
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
