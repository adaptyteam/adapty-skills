# The app's view on Android

Open this file only for a native Android app, at step 2 of
[custom-elements.md](../custom-elements.md#on-a-yes-the-apps-view). The steps, the rules and the
reply are there; this file holds what is particular to Android.

## The SDK

The view is served by the **Adapty Android SDK 4.4 and later**, with its UI module at the same
version. Write it the way the app draws its screens: a composable in a Compose app, an Android
`View` in a View-based one. Either works wherever the app shows flows.

An app below 4.4 needs both modules updated first. Ask before touching the dependency, and read
the release notes for every version in between
(https://github.com/adaptyteam/AdaptySDK-Android/releases) before you build.

## Registering the view

Find the Android custom elements page through the `adapty-docs` skill and follow it. Where no page
shows the call, read the SDK source at the release tag the app depends on
(https://github.com/adaptyteam/AdaptySDK-Android, search it for "custom element") rather than
guess a signature. The use-case recipes in the docs show iOS code; their Type, ID and fallback
conditions apply unchanged.

What the source requires of the code you write:

- **The registration is asked again on every redraw of the screen,** so deciding whether to return
  a view stays cheap: check that the file exists or the data is there, never load or compute it
  there. Return no view for any other Type and ID pair.
- **A per-flow registration replaces the app-wide one entirely,** even for Types it does not
  serve: hand every other Type on to the app-wide registration explicitly.
- **An Android `View` is created anew each time it appears,** and two can exist at once while a
  screen transition runs. Keep what is expensive (a player, the data) outside the view, and start
  anything that runs (a camera, a location update) when the view is attached and stop it when it
  is detached. A composable does the same when it leaves the screen.
- **Give the content a size it reports:** a lazy list or a size-measuring layout reports none, and
  the box's fixed height is what keeps it visible.

A permission the view needs is declared in `AndroidManifest.xml` and requested at runtime when
the view appears; "how to allow it in Settings" means the app's page in the system settings.

## Per use case

| Use case | What Android adds |
| :--- | :--- |
| [Lottie](lottie.md) | Lottie for Android (`com.airbnb.android:lottie-compose`, or `lottie` for a View); the animation file goes in `res/raw`, named after the ID |
| [Rive](rive.md) | the Rive Android runtime (`app.rive:rive-android`); the `.riv` file goes in `res/raw`, named after the ID |
| [Map](map.md) | the location permissions in the manifest. Google Maps (`com.google.maps.android:maps-compose` in a Compose app) needs the app's Maps API key in the manifest: use the app's own, and ask when it has none, never a placeholder |
| [Chart](chart.md) | Android has no built-in chart view: use the chart library the app already has, and ask before adding one |
| [Camera](camera.md) | the `CAMERA` permission in the manifest; CameraX (`androidx.camera`) bound to the view's lifecycle, so the camera stops when the view leaves. **Add Guava as the app's own dependency** (`com.google.guava:guava`, the `-android` version the Adapty UI module resolves to at runtime): the camera provider is returned as a Guava future, and without it the app does not compile, because Adapty brings Guava at runtime only |
