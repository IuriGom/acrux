import Foundation

/// Provides the local API token from ~/.acrux/config.yaml so the app can
/// authenticate against the Acrux backend (TokenAuthMiddleware).
enum AcruxAuth {
    static let token: String? = loadToken()

    /// Query suffix for the chat WebSocket, e.g. "?token=abc".
    static var tokenQuery: String {
        token.map { "?token=\($0)" } ?? ""
    }

    private static func loadToken() -> String? {
        let url = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".acrux/config.yaml")
        guard let text = try? String(contentsOf: url, encoding: .utf8) else { return nil }
        for line in text.split(separator: "\n") {
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            guard trimmed.hasPrefix("api_token:") else { continue }
            let value = trimmed
                .dropFirst("api_token:".count)
                .trimmingCharacters(in: .whitespaces)
                .trimmingCharacters(in: CharacterSet(charactersIn: "\"'"))
            return value.isEmpty ? nil : value
        }
        return nil
    }
}

extension URLRequest {
    /// Request to the local Acrux backend with the API token attached.
    static func acrux(url: URL) -> URLRequest {
        var request = URLRequest(url: url)
        if let token = AcruxAuth.token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return request
    }
}
