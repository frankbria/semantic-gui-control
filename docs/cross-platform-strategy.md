# Cross-Platform Strategy

## Why Not Windows-Only?

The generic problem should not be oversteered toward Windows. Windows is an important first target because it has large amounts of legacy business software and a mature automation/accessibility stack. But the architecture should assume multiple desktop environments from the beginning.

The right abstraction is not “Windows UI automation.” The right abstraction is:

> Discover an interactive environment's affordances, normalize them, execute actions, and verify state changes.

## Platform Adapter Model

```text
Core Protocol / Agent API
        ↓
Affordance Model
        ↓
Platform Adapter Interface
        ↓
Windows UIA | macOS AX | Linux AT-SPI | Browser DOM | Vision/OCR
```

The core should not know whether a button came from UIA, AX, AT-SPI, DOM, or OCR. It should know that an affordance exists:

```json
{
  "id": "control_17",
  "role": "button",
  "label": "Save",
  "enabled": true,
  "visible": true,
  "actions": ["focus", "invoke"],
  "source": "platform_accessibility",
  "confidence": 0.94
}
```

## Candidate Platform Sources

### Windows

Primary source:

- Microsoft UI Automation / UIA

Secondary sources:

- Win32 metadata
- COM automation for Office-class apps
- PowerShell
- pywinauto / FlaUI
- screenshot/OCR fallback

### macOS

Primary source:

- Accessibility API / AXUIElement

Secondary sources:

- AppleScript
- Shortcuts
- CGWindow APIs
- screenshot/OCR fallback

### Linux Desktop

Primary source:

- AT-SPI accessibility bus

Secondary sources:

- xdotool / ydotool
- wmctrl
- dbus
- Wayland compositor-specific APIs
- screenshot/OCR fallback

Linux is likely messier because desktop environments and Wayland security models vary. The abstraction should expect uneven capability.

### Browser

Primary source:

- DOM via Playwright or browser automation protocol

Browser automation should eventually be treated as an adapter, not as a separate product.

## Design Principle

Platform adapters should emit the same normalized model:

```text
Window
Panel
Menu
Toolbar
Button
Input
Table
Row
Cell
Dialog
Notification
State
Action
Constraint
Risk
```

Adapters can differ internally. The agent-facing vocabulary should not.

## Initial Recommendation

Build the first spike on the platform that is easiest to test immediately, but define the core interfaces as cross-platform from day one.

Recommended implementation order:

1. Define platform-neutral schemas.
2. Implement one Windows adapter or one Linux adapter for the first spike.
3. Keep adapter calls behind an interface.
4. Add macOS/Linux/Windows adapters later without changing the command vocabulary.

## Avoid This Trap

Do not create a Windows-shaped core and then later pretend it is cross-platform.

The core should say:

```text
find controls where role=button and label contains Save
```

Not:

```text
find UIA ButtonControlType with InvokePattern
```

The platform-specific details belong below the adapter boundary.
