import Foundation

enum ChatLayout: String, CaseIterable {
    case single
    case dual
    case quad

    var maxVisible: Int {
        switch self {
        case .single: return 1
        case .dual: return 2
        case .quad: return 4
        }
    }

    var menuTitle: String {
        switch self {
        case .single: return "Single view"
        case .dual: return "2-way split"
        case .quad: return "4-way split"
        }
    }
}
