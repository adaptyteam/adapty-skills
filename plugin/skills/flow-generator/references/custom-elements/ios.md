# The app's view on iOS

Open this file only for a native iOS app, at step 2 of
[custom-elements.md](../custom-elements.md#on-a-yes-the-apps-view). The steps, the rules and the
reply are there; this file holds what is particular to iOS.

## The SDK

The view is served by the **Adapty iOS SDK 4.4 and later**. It is a SwiftUI view; a UIKit view is
wrapped in one.

An app below 4.4 needs the SDK updated first, and **4.4 breaks code that builds today**: flows
need iOS 16, so an app that targets iOS 15 wraps its flow code in an availability check; a custom
action's handler and custom asset names change; and the fallback file's old format fails silently
with no build error. Say so, and ask before touching the dependency; on a yes, apply
https://adapty.io/docs/migration-to-ios-sdk-44.md and tell the user to download the fallback file
again for 4.4.

## Registering the view

Follow https://adapty.io/docs/ios-flow-custom-elements.md and the use case's recipe. Where the
page does not show the call, read the SDK source at the release tag the app depends on
(https://github.com/adaptyteam/AdaptySDK-iOS, search it for "custom element") rather than guess a
signature.

A permission the view needs has its usage description in `Info.plist`; add it with the view.

## Per use case

| Use case | What iOS adds |
| :--- | :--- |
| [Lottie](lottie.md) | the `lottie-ios` package; the animation file goes in the app bundle |
| [Rive](rive.md) | the Rive runtime for Apple platforms (the `RiveRuntime` package); the `.riv` file goes in the app bundle |
| [Map](map.md) | `NSLocationWhenInUseUsageDescription` in `Info.plist`. Apple's newest map view needs iOS 17; on iOS 16 the app uses the older map view or draws nothing |
| [Chart](chart.md) | Swift Charts. Dragging along the chart needs iOS 17; on iOS 16 the line still draws |
| [Camera](camera.md) | `NSCameraUsageDescription` in `Info.plist` |
