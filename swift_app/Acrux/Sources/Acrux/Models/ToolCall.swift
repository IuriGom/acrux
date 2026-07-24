import Foundation

struct ToolCall: Identifiable, Codable, Equatable {
    let id: String
    let name: String
    let arguments: [String: AnyCodable]
}

struct ToolResult: Identifiable, Codable, Equatable {
    let id: String
    let output: String
}

struct AnyCodable: Codable, Equatable {
    let value: Any

    init(_ value: Any) {
        self.value = value
    }

    static func == (lhs: AnyCodable, rhs: AnyCodable) -> Bool {
        let encoder = JSONEncoder()
        guard let l = try? encoder.encode(lhs),
              let r = try? encoder.encode(rhs) else { return false }
        return l == r
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let string = try? container.decode(String.self) { value = string }
        else if let int = try? container.decode(Int.self) { value = int }
        else if let double = try? container.decode(Double.self) { value = double }
        else if let bool = try? container.decode(Bool.self) { value = bool }
        else if let array = try? container.decode([AnyCodable].self) { value = array.map(\.value) }
        else if let dict = try? container.decode([String: AnyCodable].self) { value = dict.mapValues(\.value) }
        else { value = "" }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        if let string = value as? String { try container.encode(string) }
        else if let int = value as? Int { try container.encode(int) }
        else if let double = value as? Double { try container.encode(double) }
        else if let bool = value as? Bool { try container.encode(bool) }
        else if let array = value as? [Any] { try container.encode(array.map(AnyCodable.init)) }
        else if let dict = value as? [String: Any] { try container.encode(dict.mapValues(AnyCodable.init)) }
        else { try container.encode("\(value)") }
    }
}
