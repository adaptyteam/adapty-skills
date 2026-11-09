# Template: a camera preview

Rules, shape and the reply: [custom-elements.md](../custom-elements.md). This file holds only what
is particular to the camera.

**Fits** a live camera on a screen: a preview before a body or skin scan, a mirror, a barcode or
document scanner, a "point at your plant" step in an onboarding.

**Does not fit** a result the app works out from the camera and the flow then branches on: the
camera view cannot tell the flow anything. When the next screen depends on the scan, the scan is
the app's own screen, reached through a custom action, and the flow continues as a second flow.

## The box

| Field | Value |
| :--- | :--- |
| Type | `camera_preview` |
| ID | what it is for, such as `skin_scan` |
| Height | fixed, never `hug`; usually tall (360–480 pt) or a square |
| Width | `fill`, with `borderRadius` and `clip=True` |

```python
fk.custom_element('camera_preview', 'skin_scan', fixed_h=420, corner=fk.radius(24), clip=True,
                  fallback=[fk.image(fk.PLACEHOLDER, fixed_h=420, fit='cover',
                                     corner=fk.radius(24))])
```

**Fallback:** a photo or an illustration of what the camera would show.

**Around the box:** one line that says why the app wants the camera, above the box. The system
camera prompt appears when the view opens.

## What the app's view does

- Asks for camera access when it appears, only if the user has not answered yet; the app needs its
  camera usage description (`NSCameraUsageDescription`) in `Info.plist`.
- Starts the camera session when the view appears and **stops it when the view disappears**: the
  view goes away when the user moves to the next screen, and a session left running keeps the
  camera on.
- Draws nothing when the user denied camera access, so the fallback shows.

Docs: https://adapty.io/docs/flow-custom-elements.md and the iOS setup at
https://adapty.io/docs/ios-flow-custom-elements.md

## On the device

Allow the camera, check the preview fills the rounded box; go to the next screen and check the
camera indicator goes off; deny the camera in Settings and reopen to see the fallback.
