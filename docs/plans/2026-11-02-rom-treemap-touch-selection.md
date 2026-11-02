# ROM Treemap touch selection and launch

## Goal

Make a touch on a ROM tile safe for browsing. A single touch selects the ROM and updates its details without starting gameplay. Launch remains available through the selected ROM's **Play this ROM** button, and a deliberate long press on a tile also launches it.

## Current behavior

Each ROM in the treemap is a button. Focus updates the selected-ROM details, but the tile's click handler immediately calls `launch(r)`. A phone tap therefore selects and launches in one gesture. The detail panel already has a Play button, but it only becomes useful after changing the tile behavior.

## Interaction

- A short touch on a tile selects it, moves the selection outline, and updates the preview and details. It must not call `launch`.
- Holding a touch on the same tile for 550 ms launches that ROM once. Movement of 12 CSS pixels or more, `pointercancel`, or releasing before the threshold cancels the hold.
- The click event synthesized after a touch must not launch a second time after a long press, nor launch after a short tap.
- The selected-ROM Play button continues to launch the current selection. Keyboard and TV remote activation retain their existing behavior.
- Update the treemap hint so it distinguishes touch selection from the launch gestures.

## Scope

Change only the ROM Treemap tile interaction and its hint. Keep Quick Launch and Cartridge Flow activation unchanged. Reuse Pointer Events, timers, and the existing selected-ROM detail and Play-button paths; do not introduce dependencies or APIs newer than the supported WebView 91 baseline.

## Acceptance

1. A short phone tap on a different tile changes selection and details but leaves the library open.
2. Tapping **Play this ROM** launches the selected tile, not the tile that was previously selected.
3. A stationary touch held past 550 ms launches once; releasing it does not launch again.
4. A hold canceled by movement, `pointercancel`, or early release does not launch.
5. Mouse and keyboard/remote tile activation keep their current behavior.
6. Quick Launch and Cartridge Flow retain their current activation behavior.
