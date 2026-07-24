import Foundation
import Combine

@MainActor
final class ChatStore: ObservableObject {
    @Published var chats: [Chat] = []

    private let url = FileManager.default
        .homeDirectoryForCurrentUser
        .appendingPathComponent(".acrux/app/swift_chats.json")

    func load() {
        guard FileManager.default.fileExists(atPath: url.path),
              let data = try? Data(contentsOf: url) else {
            chats = []
            return
        }
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        do {
            chats = try decoder.decode([Chat].self, from: data)
        } catch {
            chats = []
        }
    }

    func save(_ chat: Chat) {
        if let index = chats.firstIndex(where: { $0.id == chat.id }) {
            chats[index] = chat
        } else {
            chats.append(chat)
        }
        persist()
    }

    func delete(_ chat: Chat) {
        chats.removeAll { $0.id == chat.id }
        persist()
    }

    func chat(id: UUID) -> Chat? {
        chats.first { $0.id == id }
    }

    @discardableResult
    func importChat(from url: URL) -> Chat? {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        guard let data = try? Data(contentsOf: url),
              var chat = try? decoder.decode(Chat.self, from: data) else {
            return nil
        }
        chat.id = UUID()
        chat.createdAt = Date()
        chat.updatedAt = Date()
        save(chat)
        return chat
    }

    private func persist() {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = .prettyPrinted
        guard let data = try? encoder.encode(chats) else { return }
        try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try? data.write(to: url)
    }
}
