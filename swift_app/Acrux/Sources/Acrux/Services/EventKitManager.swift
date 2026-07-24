import Foundation
import EventKit

@MainActor
final class EventKitManager: ObservableObject {
    private let eventStore = EKEventStore()
    @Published var lastError: String?
    @Published var showError = false

    func requestReminderAccess() async -> Bool {
        let status = EKEventStore.authorizationStatus(for: .reminder)
        if status == .fullAccess { return true }
        if status == .denied || status == .restricted {
            lastError = "Reminders access is denied. Enable it in System Settings > Privacy & Security > Reminders."
            showError = true
            return false
        }
        do {
            return try await eventStore.requestFullAccessToReminders()
        } catch {
            lastError = "Could not access Reminders: \(error.localizedDescription)"
            showError = true
            return false
        }
    }

    func requestCalendarAccess() async -> Bool {
        let status = EKEventStore.authorizationStatus(for: .event)
        if status == .fullAccess { return true }
        if status == .denied || status == .restricted {
            lastError = "Calendar access is denied. Enable it in System Settings > Privacy & Security > Calendars."
            showError = true
            return false
        }
        do {
            return try await eventStore.requestFullAccessToEvents()
        } catch {
            lastError = "Could not access Calendar: \(error.localizedDescription)"
            showError = true
            return false
        }
    }

    func createReminder(title: String, notes: String) async {
        guard await requestReminderAccess() else { return }
        let reminder = EKReminder(eventStore: eventStore)
        reminder.title = title
        reminder.notes = notes
        guard let calendar = eventStore.defaultCalendarForNewReminders() else {
            lastError = "No default Reminders list found."
            showError = true
            return
        }
        reminder.calendar = calendar
        do {
            try eventStore.save(reminder, commit: true)
        } catch {
            lastError = "Could not save reminder: \(error.localizedDescription)"
            showError = true
        }
    }

    func createCalendarEvent(title: String, notes: String, startDate: Date? = nil) async {
        guard await requestCalendarAccess() else { return }
        let event = EKEvent(eventStore: eventStore)
        event.title = title
        event.notes = notes
        event.startDate = startDate ?? Date()
        event.endDate = Date(timeInterval: 3600, since: event.startDate)
        guard let calendar = eventStore.defaultCalendarForNewEvents else {
            lastError = "No default Calendar found."
            showError = true
            return
        }
        event.calendar = calendar
        do {
            try eventStore.save(event, span: .thisEvent, commit: true)
        } catch {
            lastError = "Could not save calendar event: \(error.localizedDescription)"
            showError = true
        }
    }
}
