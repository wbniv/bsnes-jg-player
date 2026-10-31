import SwiftUI

@MainActor
final class PlayerModel: ObservableObject {
    let controller = BJGPlayerController()
    @Published var paused = false {
        didSet { controller.userPaused = paused }
    }
    @Published var muted = false {
        didSet { controller.muted = muted }
    }
    @Published var status = "Loading…"
    @Published var diagnostics = ""
    init() {
        controller.stateChanged = { [weak self] status, diagnostics in
            DispatchQueue.main.async {
                guard let self else { return }
                self.status = status
                self.diagnostics = diagnostics
                if self.paused != self.controller.userPaused { self.paused = self.controller.userPaused }
            }
        }
    }
}

struct NativePlayer: UIViewControllerRepresentable {
    @ObservedObject var model: PlayerModel
    func makeUIViewController(context: Context) -> BJGPlayerController { model.controller }
    func updateUIViewController(_ controller: BJGPlayerController, context: Context) {}
    static func dismantleUIViewController(_ controller: BJGPlayerController, coordinator: ()) {
        controller.shutdown()
    }
}

struct PlayerShell: View {
    @StateObject private var model = PlayerModel()
    @Environment(\.scenePhase) private var scenePhase
    @State private var help = false
    private let testing = ProcessInfo.processInfo.environment["BJG_UI_TESTING"] == "1"
    var body: some View {
        VStack(spacing: 4) {
            HStack {
                VStack(alignment: .leading) {
                    Text("bsnes-jg-player").font(.headline)
                    Text(model.status).font(.caption).accessibilityIdentifier("playerStatus")
                }
                Spacer()
                Button(model.paused ? "Resume" : "Pause") { model.paused.toggle() }
                    .accessibilityIdentifier("pauseResume")
                Button(model.muted ? "Unmute" : "Mute") { model.muted.toggle() }
                    .accessibilityIdentifier("mute")
                Button { help = true } label: { Image(systemName: "questionmark.circle") }
                    .accessibilityLabel("Help").accessibilityIdentifier("help")
            }.padding(.horizontal, 12).padding(.top, 4)
            NativePlayer(model: model)
            if testing {
                Text(model.diagnostics).font(.system(size: 8, design: .monospaced))
                    .accessibilityIdentifier("diagnostics")
            }
        }
        .foregroundStyle(.white).background(Color.black)
        .preferredColorScheme(.dark)
        .onAppear {
            model.controller.applicationActive = scenePhase == .active
            if ProcessInfo.processInfo.arguments.contains("--self-test") {
                BJGPlayerController.runSelfTest()
            }
        }
        .onChange(of: scenePhase) { phase in
            model.controller.applicationActive = phase == .active
        }
        .sheet(isPresented: $help, onDismiss: { model.controller.applicationActive = scenePhase == .active }) {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text("SNES player").font(.title)
                    Text("Hold the touch buttons to play. A connected gamepad uses the same SNES positions: south is B, east is A, west is Y, north is X. Menu is Start; Options is Select.")
                    Text("Playback pauses when the app is inactive. Pause and Mute are independent controls. The bundled Raycaster demo runs itself; it is a core fidelity example.")
                    Text("Source and license").font(.headline)
                    Link("bsnes-jg-player source", destination: URL(string: "https://github.com/wbniv/bsnes-jg-player")!)
                    Text((try? String(contentsOf: Bundle.main.url(forResource: "NOTICE", withExtension: "txt")!)) ?? "GPL-3.0-only")
                    Button("Done") { help = false }
                }.padding()
            }.onAppear { model.controller.applicationActive = false }
        }
    }
}

@main
struct PlayerApp: App {
    var body: some Scene { WindowGroup { PlayerShell() } }
}
