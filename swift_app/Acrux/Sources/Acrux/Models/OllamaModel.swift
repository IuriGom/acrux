import Foundation

struct OllamaModel: Codable, Identifiable, Equatable {
    let name: String
    let size: Int

    var id: String { name }
}
