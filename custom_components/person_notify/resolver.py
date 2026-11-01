"""Resolve a person entity into the notify targets of its devices."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import slugify

from .const import MOBILE_APP_DEVICE_NAME, MOBILE_APP_DOMAIN

NOTIFY_DOMAIN = "notify"


@dataclass(frozen=True)
class NotifyTarget:
    """A single notification target."""

    kind: str  # "service" (legacy notify.<name>) or "entity" (notify entity)
    target: str  # service name (without domain) or entity_id
    device_name: str

    @property
    def display(self) -> str:
        """Human readable id, e.g. notify.mobile_app_pixel."""
        return f"{NOTIFY_DOMAIN}.{self.target}" if self.kind == "service" else self.target

    def as_dict(self) -> dict[str, str]:
        """Serialize for service responses / attributes."""
        return {"kind": self.kind, "target": self.display, "device": self.device_name}


def person_device_ids(hass: HomeAssistant, person_id: str) -> list[str]:
    """Return device ids linked to a person via its device trackers."""
    state = hass.states.get(person_id)
    if state is None:
        return []
    ent_reg = er.async_get(hass)
    device_ids: list[str] = []
    for tracker in state.attributes.get("device_trackers", []) or []:
        entry = ent_reg.async_get(tracker)
        if entry and entry.device_id and entry.device_id not in device_ids:
            device_ids.append(entry.device_id)
    return device_ids


def _mobile_app_service(hass: HomeAssistant, device: dr.DeviceEntry) -> str | None:
    """Return legacy mobile_app notify service name for a device, if any."""
    for entry_id in device.config_entries:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != MOBILE_APP_DOMAIN:
            continue
        name = entry.data.get(MOBILE_APP_DEVICE_NAME) or device.name
        if not name:
            continue
        service = f"{MOBILE_APP_DOMAIN}_{slugify(name)}"
        if hass.services.has_service(NOTIFY_DOMAIN, service):
            return service
    return None


def resolve_targets(hass: HomeAssistant, person_id: str) -> list[NotifyTarget]:
    """Return all notify targets for a person."""
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    targets: list[NotifyTarget] = []

    for device_id in person_device_ids(hass, person_id):
        device = dev_reg.async_get(device_id)
        if device is None:
            continue
        device_name = device.name_by_user or device.name or device_id

        # Prefer the mobile_app service: it supports `data` passthrough.
        if service := _mobile_app_service(hass, device):
            targets.append(NotifyTarget("service", service, device_name))
            continue

        for entry in er.async_entries_for_device(ent_reg, device_id):
            if entry.domain == NOTIFY_DOMAIN and not entry.disabled:
                targets.append(NotifyTarget("entity", entry.entity_id, device_name))

    return targets


__all__ = ["NotifyTarget", "resolve_targets", "person_device_ids", "ATTR_DEVICE_ID"]
