import SwiftUI
import Speech
import AVFoundation
import AppKit

final class DictationManager: NSObject, ObservableObject, @unchecked Sendable {
    @Published var isListening = false
    @Published var fallbackMessage: String?

    private var speechRecognizer: SFSpeechRecognizer?
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private let audioEngine = AVAudioEngine()
    private let audioQueue = DispatchQueue(label: "com.acrux.dictation.audio")
    private var onResult: ((String) -> Void)?
    private var lastTranscription = ""

    func toggle(completion: @escaping (String) -> Void) {
        if isListening {
            stop()
        } else {
            start(completion: completion)
        }
    }

    func start(completion: @escaping (String) -> Void) {
        onResult = completion
        fallbackMessage = nil
        lastTranscription = ""

        let status = SFSpeechRecognizer.authorizationStatus()
        if status == .authorized {
            requestMicrophoneAndBegin()
        } else if status == .notDetermined {
            SFSpeechRecognizer.requestAuthorization { [weak self] newStatus in
                DispatchQueue.main.async {
                    guard let self = self else { return }
                    if newStatus == .authorized {
                        self.requestMicrophoneAndBegin()
                    } else {
                        self.showFallback()
                    }
                }
            }
        } else {
            showFallback()
        }
    }

    func stop() {
        audioQueue.async { [weak self] in
            guard let self = self else { return }
            self.audioEngine.stop()
            self.audioEngine.inputNode.removeTap(onBus: 0)
            self.recognitionRequest?.endAudio()
            self.recognitionRequest = nil
            self.recognitionTask?.cancel()
            self.recognitionTask = nil
            DispatchQueue.main.async {
                self.isListening = false
            }
        }
    }

    private func requestMicrophoneAndBegin() {
        if #available(macOS 14.0, *) {
            switch AVAudioApplication.shared.recordPermission {
            case .undetermined:
                AVAudioApplication.requestRecordPermission { [weak self] granted in
                    DispatchQueue.main.async {
                        guard let self = self else { return }
                        if granted {
                            self.beginSFSpeechRecognition()
                        } else {
                            self.showFallback()
                        }
                    }
                }
            case .denied:
                showFallback()
            case .granted:
                beginSFSpeechRecognition()
            @unknown default:
                beginSFSpeechRecognition()
            }
        } else {
            beginSFSpeechRecognition()
        }
    }

    private func beginSFSpeechRecognition() {
        guard let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US")), recognizer.isAvailable else {
            showFallback()
            return
        }

        speechRecognizer = recognizer
        let request = SFSpeechAudioBufferRecognitionRequest()
        recognitionRequest = request
        request.shouldReportPartialResults = true
        request.requiresOnDeviceRecognition = false

        recognitionTask = recognizer.recognitionTask(with: request) { [weak self] result, error in
            let text = result?.bestTranscription.formattedString ?? ""
            let isFinal = result?.isFinal ?? false
            let hasError = error != nil
            DispatchQueue.main.async {
                guard let self = self else { return }
                let delta = String(text.dropFirst(self.lastTranscription.count))
                self.lastTranscription = text
                if !delta.isEmpty {
                    self.onResult?(delta)
                }
                if isFinal || hasError {
                    self.stop()
                }
            }
        }

        audioQueue.async { [weak self] in
            guard let self = self else { return }
            let inputNode = self.audioEngine.inputNode
            let recordingFormat = inputNode.outputFormat(forBus: 0)
            guard recordingFormat.sampleRate > 0, recordingFormat.channelCount > 0 else {
                DispatchQueue.main.async { self.showFallback() }
                return
            }
            inputNode.removeTap(onBus: 0)
            inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { [weak self] buffer, _ in
                self?.recognitionRequest?.append(buffer)
            }
            self.audioEngine.prepare()
            do {
                try self.audioEngine.start()
                DispatchQueue.main.async {
                    self.isListening = true
                }
            } catch {
                DispatchQueue.main.async {
                    self.showFallback()
                }
            }
        }
    }

    private func showFallback() {
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            self.stop()
            self.fallbackMessage = "Speech recognition needs microphone permission. Use the system dictation shortcut (usually press Fn twice) to dictate text into the input field."
        }
    }
}
