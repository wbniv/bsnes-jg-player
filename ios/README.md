# Native iOS example

The SwiftUI shell hosts a single bsnes-jg emulator instance through Objective-C++.
Metal presents the full picture at 4:3. `CADisplayLink` feeds a 60.0988 Hz clock
with bounded catch-up; AVAudioEngine consumes stereo 48 kHz PCM from a lock-free
ring. Touch and extended GameController inputs share the SNES button mapping.
Pause, app inactivity, audio interruption and teardown stop playback and clear input.

Validation on 2026-10-31: three XCTest cases passed on each of iPhone 16 and
iPad Pro 11-inch (M4), plus ROM/offline-audio checks and the unsigned iPhone SDK
build. See [proof and remaining physical checks](../docs/plans/2026-10-30-native-ios-player.md).

## Local core and host checks (Linux or macOS)

```sh
python3 ios/prepare.py
cmake -S ios -B ios/build-host -DCMAKE_BUILD_TYPE=Release
cmake --build ios/build-host -j 4
ctest --test-dir ios/build-host --output-on-failure
ios/build-host/core-smoke ios/generated/demo.sfc ios/generated/bsnes-2.1.0/Database
```

The host tests exercise stereo ordering, underrun, overflow, mute, concurrent ring
wrap-around, 60/120 Hz timing, stall recovery, and controller mapping. The core
check runs the exact SHA-256-pinned demo for 500 frames against its manifest.

## Simulator validation

Run the manual `ios-simulator` Codemagic workflow, or use its CMake/Xcode commands
on an Apple Silicon Mac. It installs the app, checks the ROM and AVAudioEngine
manual rendering, then runs `PlayerUITests` on iPhone and iPad in portrait and
landscape. The workflow also compiles the physical-device SDK target unsigned.
Artifacts include `.xcresult`, screenshots, self-check JSON and build/test logs.

`BJG_AUDIO_OFFLINE=1` selects offline audio rendering for headless CI, where
RemoteIO initialization can abort because no output device is available. This
uses the production ring and source node, but is **not audible speaker proof**.
`BJG_UI_TESTING=1` exposes diagnostics for XCTest. Normal launches use live audio.
The bundled Raycaster is an automatic demo; the tests check button values actually
polled by the core instead of inferring input from visible movement.

## Physical iPhone

For a Mac with Xcode signing configured, stage the assets and generate a device
project with your own team identifier:

```sh
cmake -S ios -B ios/build-device -G Xcode -DCMAKE_SYSTEM_NAME=iOS \
  -DCMAKE_OSX_SYSROOT=iphoneos -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DCMAKE_OSX_DEPLOYMENT_TARGET=16.0 -DBJG_DEVELOPMENT_TEAM=YOUR_TEAM_ID
open ios/build-device/BsnesPlayer.xcodeproj
```

Select BsnesPlayer, the connected iPhone and your signing team in Xcode, then Run.
For a preinstalled manual profile, also pass `-DBJG_PROFILE_SPECIFIER=PROFILE_NAME`.
Bundle identifier: `org.bsnesjg.player.ios`.

For Codemagic, upload an Apple Development certificate/private key and a matching
development provisioning profile that includes the test iPhone UDID to the team's
Code signing identities. Then manually run `ios-development`. It applies the
profile, archives and exports an IPA; it does not publish to TestFlight or the
App Store. See [Codemagic signing instructions](https://docs.codemagic.io/yaml-code-signing/signing-ios/).
Do not put signing secrets in Git or chat. The workflow is prepared but remains
unverified until signing identities and a physical iPhone are available.

Physical acceptance still requires:

- Install and launch with the default live audio mode; listen to both channels,
  mute/unmute, route changes, interruptions and background/foreground recovery.
  Use a ROM with known audio when evaluating audible output: the demo may be quiet.
- Verify all touch controls, simultaneous presses, connected controller mapping,
  controller disconnect, Pause/Resume and no stuck inputs.
- Check portrait/landscape, safe areas and sustained frame/audio pacing.
- Launch with `--self-test` from Xcode and retain Documents/selfcheck.json.
  This checks offline audio and ROM fidelity; it does not replace live listening.

## Shared Codemagic allowance

The app ID is `6ae5356ef8ef89f5624cab78`; credentials are in the existing user
Codemagic configuration described by WorldFoundry's setup documentation.
Use only the free M2 machine and check account-wide usage and active jobs before
starting a run. These manual workflows allow 30 minutes: reserve that capacity
plus a margin, and defer to the next UTC month if the free allowance is too close.
Do not shorten the timeout merely to fit remaining minutes. Other projects share
this account and its single concurrent build slot.
