# Person Notify

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/maximosstratis/person_notify/actions/workflows/validate.yml/badge.svg)](https://github.com/maximosstratis/person_notify/actions/workflows/validate.yml)

Notify **a person** instead of individual devices. Person Notify looks at the
`device_trackers` of a `person` entity, finds the devices behind them and sends
the notification to every notifier on those devices (phone, watch, tablet …).

## Features
- `person_notify.send` action with a person picker (multiple people allowed)
- Full `data:` passthrough for Companion App notifications (actions, images, channels…)
- Also supports devices exposing `notify.*` entities (via `notify.send_message`)
- A diagnostic sensor per person – `sensor.<person>_notify_targets` – showing
  which notifiers will be used
- `person_notify.get_targets` action returning the notifiers for given people
- Warning in the log (and in the action response) if a person has no notifiers

## Installation
1. HACS → ⋮ → **Custom repositories** → add `https://github.com/maximosstratis/person_notify`, type **Integration**
2. Install **Person Notify** and restart Home Assistant
3. Settings → Devices & Services → **Add integration** → *Person Notify*

## Usage
```yaml
action: person_notify.send
data:
  person:
    - person.admin
  title: Front door
  message: The front door was opened
  data:
    actions:
      - action: LOCK
        title: Lock it
```

Check targets:
```yaml
action: person_notify.get_targets
data:
  person: person.admin
response_variable: targets
```

## How targets are resolved
1. `person.*` → `device_trackers` attribute
2. Each tracker → its device in the device registry (trackers without a device, e.g. router based, are skipped)
3. Mobile app device → `notify.mobile_app_<device_name>` (supports `data`)
4. Other devices → their enabled `notify.*` entities (`message` and `title` only)

## License
MIT
