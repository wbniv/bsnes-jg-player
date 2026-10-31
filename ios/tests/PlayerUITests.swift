import XCTest

final class PlayerUITests: XCTestCase {
    var app: XCUIApplication!
    override func setUpWithError() throws {
        continueAfterFailure = false
        XCUIDevice.shared.orientation = .portrait
        app = XCUIApplication(bundleIdentifier: "org.bsnesjg.player.ios")
        app.launchEnvironment = ["BJG_UI_TESTING": "1", "BJG_AUDIO_OFFLINE": "1"]
        app.launch()
        XCTAssertTrue(app.staticTexts["diagnostics"].waitForExistence(timeout: 30))
        waitFor("running=1")
    }
    override func tearDownWithError() throws {
        app.terminate()
        XCUIDevice.shared.orientation = .portrait
    }
    func diagnostics() -> String { app.staticTexts["diagnostics"].label }
    func value(_ key: String) -> Int {
        let field = diagnostics().split(separator: ";").first { $0.hasPrefix(key + "=") }
        return field.flatMap { Int($0.split(separator: "=").last!) } ?? -1
    }
    func waitFor(_ text: String) {
        let predicate = NSPredicate(format: "label CONTAINS %@", text)
        expectation(for: predicate, evaluatedWith: app.staticTexts["diagnostics"])
        waitForExpectations(timeout: 15)
    }
    func capture(_ name: String) {
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
    func assertLayout() {
        let screen = app.otherElements["gameScreen"].firstMatch
        XCTAssertTrue(screen.exists)
        let rect = screen.frame
        XCTAssertGreaterThan(rect.width, 100)
        XCTAssertEqual(rect.width / rect.height, 4.0 / 3.0, accuracy: 0.03)
        for key in ["up", "down", "left", "right", "select", "start", "y", "x", "b", "a", "l", "r"] {
            let button = app.buttons["pad." + key]
            XCTAssertTrue(button.isHittable, key)
            XCTAssertGreaterThanOrEqual(button.frame.width, 43)
            XCTAssertGreaterThanOrEqual(button.frame.height, 43)
            XCTAssertFalse(rect.intersects(button.frame), key)
        }
    }
    func testTouchButtonsAndRelease() {
        let buttons: [(String, Int)] = [("up", 1 << 11), ("down", 1 << 10), ("left", 1 << 9), ("right", 1 << 8), ("select", 1 << 13), ("start", 1 << 12), ("y", 1 << 14), ("x", 1 << 6), ("b", 1 << 15), ("a", 1 << 7), ("l", 1 << 5), ("r", 1 << 4)]
        for (name, mask) in buttons {
            app.buttons["pad." + name].press(forDuration: 0.4)
            waitFor("lastTouch=\(mask);")
            waitFor("observed=\(mask);") // input actually polled by bsnes, not just a UI flag
            waitFor("pad=0;")
        }
        XCTAssertGreaterThanOrEqual(value("touchEvents"), 12)
        capture("touch-controls")
    }
    func testPauseBackgroundResumeAndAudio() {
        let runningFrames = value("frames")
        sleep(1)
        XCTAssertGreaterThan(value("frames"), runningFrames)
        XCTAssertGreaterThan(value("audio"), 0) // core PCM traversed AVAudioEngine offline render
        app.buttons["pauseResume"].tap()
        waitFor("running=0")
        let frozen = value("frames")
        sleep(1)
        XCTAssertEqual(value("frames"), frozen)
        app.buttons["pad.a"].press(forDuration: 0.3)
        XCTAssertEqual(value("pad"), 0)
        XCUIDevice.shared.press(.home)
        sleep(1)
        app.activate()
        waitFor("running=0") // user pause must survive background/foreground
        XCTAssertEqual(value("frames"), frozen)
        app.buttons["pauseResume"].tap()
        waitFor("running=1")
        sleep(1)
        XCTAssertGreaterThan(value("frames"), frozen)
        app.buttons["mute"].tap(); waitFor("muted=1")
        app.buttons["mute"].tap(); waitFor("muted=0")
        XCUIDevice.shared.press(.home)
        sleep(1)
        app.activate()
        waitFor("running=1")
        waitFor("pad=0;")
        capture("resumed")
    }
    func testPortraitLandscapeAndHelp() {
        assertLayout(); capture("portrait")
        XCUIDevice.shared.orientation = .landscapeLeft
        sleep(2)
        assertLayout(); capture("landscape")
        app.buttons["help"].tap()
        XCTAssertTrue(app.buttons["Done"].waitForExistence(timeout: 5))
        app.buttons["Done"].tap()
        waitFor("running=1")
        XCUIDevice.shared.orientation = .portrait
        sleep(2)
        assertLayout()
    }
}
