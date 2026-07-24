import Foundation
import Combine

@MainActor
final class BackendProcess: ObservableObject {
    @Published var isRunning = false

    private var task: Process?

    private static var logFile: URL {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Logs/Acrux/backend.log")
    }

    private static var pidFile: URL {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".acrux/acrux.pid")
    }

    func start() {
        guard task == nil || !task!.isRunning else { return }

        killStaleBackend()
        killProcessOnPort(Constants.backendPort)

        let logURL = Self.logFile
        try? FileManager.default.createDirectory(at: logURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        if !FileManager.default.fileExists(atPath: logURL.path) {
            FileManager.default.createFile(atPath: logURL.path, contents: nil)
        }
        let logHandle = try? FileHandle(forWritingTo: logURL)
        logHandle?.seekToEndOfFile()

        let task = Process()
        task.executableURL = Constants.venvPythonURL
        var env = ProcessInfo.processInfo.environment
        env["PYTHONPATH"] = "\(Constants.acruxProjectDir)"
        env["PATH"] = "\(Constants.acruxProjectDir)/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        task.environment = env
        task.arguments = [
            "-c",
            "import uvicorn; uvicorn.run('acrux.app.main:app', host='\(Constants.backendHost)', port=\(Constants.backendPort), log_level='info')"
        ]
        task.currentDirectoryURL = Constants.projectURL
        task.standardOutput = logHandle
        task.standardError = logHandle

        task.terminationHandler = { [weak self] _ in
            Task { @MainActor in
                self?.isRunning = false
                try? FileManager.default.removeItem(at: Self.pidFile)
            }
        }

        do {
            try task.run()
            self.task = task
            isRunning = true
            writePid(task.processIdentifier)
        } catch {
            print("Failed to start backend: \(error)")
            isRunning = false
        }
    }

    func stop() {
        guard let task = task, task.isRunning else {
            self.task = nil
            isRunning = false
            try? FileManager.default.removeItem(at: Self.pidFile)
            return
        }

        let pid = task.processIdentifier

        task.interrupt()
        task.terminate()

        DispatchQueue.global(qos: .userInitiated).asyncAfter(deadline: .now() + 1.0) { [weak self] in
            if task.isRunning {
                kill(pid, SIGKILL)
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { [weak self] in
                guard let self = self else { return }
                self.task = nil
                self.isRunning = false
                try? FileManager.default.removeItem(at: Self.pidFile)
            }
        }
    }

    private func killStaleBackend() {
        guard FileManager.default.fileExists(atPath: Self.pidFile.path),
              let pidString = try? String(contentsOf: Self.pidFile, encoding: .utf8).trimmingCharacters(in: .whitespacesAndNewlines),
              let pid = Int32(pidString) else { return }

        if kill(pid, 0) == 0 {
            kill(pid, SIGTERM)
            Thread.sleep(forTimeInterval: 0.5)
            if kill(pid, 0) == 0 {
                kill(pid, SIGKILL)
                Thread.sleep(forTimeInterval: 0.2)
            }
        }
        try? FileManager.default.removeItem(at: Self.pidFile)
    }

    private func killProcessOnPort(_ port: Int) {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/sbin/lsof")
        task.arguments = ["-ti", ":\(port)"]
        let pipe = Pipe()
        task.standardOutput = pipe
        try? task.run()
        task.waitUntilExit()

        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        guard let output = String(data: data, encoding: .utf8) else { return }

        for line in output.split(separator: "\n").compactMap({ Int32($0.trimmingCharacters(in: .whitespacesAndNewlines)) }) {
            if line != ProcessInfo.processInfo.processIdentifier {
                kill(line, SIGTERM)
            }
        }
    }

    private func writePid(_ pid: Int32) {
        try? FileManager.default.createDirectory(at: Self.pidFile.deletingLastPathComponent(), withIntermediateDirectories: true)
        try? String(pid).write(toFile: Self.pidFile.path, atomically: true, encoding: .utf8)
    }
}
