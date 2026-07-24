import Foundation

struct AcruxStatus: Codable {
    let running: Bool
    let profile: String
    let reflectionModel: String
    let embeddingModel: String
    let provider: String
    let facts: Int
    let skills: Int
    let episodes: Int
    let dataDir: String?
    let storageUsedBytes: Int?
    let storageLimitBytes: Int?
    let storagePercent: Double?
}
