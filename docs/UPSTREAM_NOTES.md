# Notes for the original DynamicNotch developers

Hi! I use DynamicNotch and adapted this fork to the way I work on my Mac. I wanted screenshots straight to the clipboard, a small calculator, external-monitor volume, and a player that does not block access to the other tools. I am sharing the source and a community build so you can inspect the changes and reuse them if they fit the project.

Base: `jackson-storm/DynamicNotch`, 1.6.3,
[`deacd0f4275c73ae5d3328491d23d0e0dc0f6970`](https://github.com/jackson-storm/DynamicNotch/commit/deacd0f4275c73ae5d3328491d23d0e0dc0f6970).

The original upstream history and license are retained. The additional commits are split by feature/fix. The default branch of this fork is `community-tools`.

## Where to look

| Area | Main implementation |
| --- | --- |
| Screenshot hiding, capture and clipboard | `Features/ScreenshotHub/ViewModels/ScreenshotCaptureModel.swift`, `Services/ScreenshotCaptureFlow.swift`, `Services/ScreenshotRegionSelector.swift` |
| Calculator | `Features/Calculator/Models/MiniCalculatorEngine.swift`, `Views/CalculatorNotchView.swift` |
| Native/DDC volume | `Features/HUD/ViewModels/SoundControlModel.swift`, `Services/DisplayDDCVolumeService.swift`, `Services/DisplayDDCProtocol.swift` |
| Trackpad page ownership and motion | `Features/HomePage/Components/HomePageScrollGesture.swift`, `HomePageScrollInput.swift`, `HomePageScrollMotion.swift` |
| Page retention | `Features/HomePage/Models/HomePageSessionMemory.swift`, `Features/Notch/ViewModels/NotchViewModel.swift` |
| Media and timer coexistence | `Core/NotchEngine/NotchEngine.swift`, `Features/Notch/Components/SecondaryLiveActivityView.swift`, `Features/Timer/Views/TimerDetachedActivityView.swift` |
| Player-to-tools swipe | `Features/Notch/ViewModels/NotchViewModel.swift`, using explicit activity selection in the engine |
| Lock-overlay crash fix | `Application/AppContainer.swift`, `Features/LockScreen/Views/LockScreenLiveActivityOverlayView.swift`, `Features/LockScreen/Windowing/LockScreenLiveActivityWindowManager.swift` |
| Russian localization | `Resources/Localization/Localizable.xcstrings` |

Paths in the table are relative to `DynamicNotch/`.

## Reproduced bugs and fixes

### Unexpected collapse during page navigation

A transient SwiftUI hover-exit could arrive while the cursor remained inside the window. The containment guard used `NSApp.delegate as? AppDelegate`, but SwiftUI can wrap that delegate. The failed cast skipped the geometry check.

The actual window owner now supplies the interaction rectangle to the view model. A real pointer exit still collapses the island. A shorter page also retains enough panel area to keep a stationary pointer inside.

### Wrong-direction or crossing page animations

Independent insertion/removal transitions could retain a stale direction, while bottom alignment moved an outgoing card during panel resizing. Rows now share a single animated vertical position. The original spring and blur/opacity style is retained, with deterministic forward and reverse motion.

### Player blocking tools

Dismissing expanded media previously collapsed it, so the next hover reopened the same player. An upward player swipe now selects the home activity directly. The engine keeps that expanded activity focused through playback updates, and restores the default media presentation when tools close. Playback continues throughout.

### Crash after a retained lock/unlock overlay

Expanding Now Playing could terminate with:

```text
No ObservableObject of type SoundControlModel found
```

The main window had the model, but the retained lock-overlay root did not. Both roots observe the same view model, so even a hidden retained overlay could attempt to render the expanded player.

The app container now passes its existing `HomePageTools` through the overlay manager. Initial construction and root refresh both inject the same tools and sound instances. This also covers the home tools' environment dependency.

### Completed activities reappearing during collapse

Restoration used content captured before the animation. The engine now resolves the current visible activity at restoration time, so events that ended during collapse are not resurrected.

## Validation and limits

The repository contains four standalone runners:

- `run-island-tools.sh`: 53 focused calculator, protocol, flow, geometry and memory checks.
- `run-navigation-checks.py`: native AppKit event checks, home-page regressions including 100 rapid transitions, and five checks from rendered motion frames and the real calculator.
- `run-activity-checks.py`: real activity-engine checks plus real view-model checks with five-second waits, player-to-tools swipes and background playback updates.
- `run-presentation-checks.py`: primary, retained hidden overlay and both-window scenarios; 20 real player expansions and four shared-dependency identity checks.

The render harnesses isolate background services and outer input handling. They are focused regression tests, not a claim that the whole XCTest/UI suite ran.

I also confirmed real playback, clicks, player-to-tools swipes and bidirectional page navigation on my Mac. Hardware volume was exercised on Huawei MateView and restored after the test. The full physical lock/unlock cycle after the fix and end-to-end interactive region-selection flow are not separately claimed as verified.

The published binary is arm64, macOS 26+, ad-hoc signed and not notarized. Existing warnings in `NowPlayingApplicationBridge.swift` about actor isolation and the deprecated screenshot-monitor image API are outside these changes and remain visible in build output.

DDC uses dynamically resolved IOKit IOAV symbols and the monitor's volume VCP register. This is hardware dependent; the implementation validates replies and runs access off the main actor. Its m1ddc MIT notice is retained.

## Intended scope

I have kept the original app and attribution, added native SwiftUI/AppKit tools, and avoided another audio driver. My goal is to make the changes easy to review and pick up in the original project, rather than claim a replacement for it.
