"""Person Notify: notify every device of a person."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_DATA,
    ATTR_MESSAGE,
    ATTR_PERSON,
    ATTR_TITLE,
    DOMAIN,
    SERVICE_GET_TARGETS,
    SERVICE_SEND,
)
from .resolver import NOTIFY_DOMAIN, NotifyTarget, resolve_targets

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]

SEND_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PERSON): cv.entity_ids,
        vol.Required(ATTR_MESSAGE): cv.string,
        vol.Optional(ATTR_TITLE): cv.string,
        vol.Optional(ATTR_DATA): dict,
    }
)
TARGETS_SCHEMA = vol.Schema({vol.Required(ATTR_PERSON): cv.entity_ids})


async def _notify(hass: HomeAssistant, target: NotifyTarget, call: ServiceCall) -> None:
    message = call.data[ATTR_MESSAGE]
    title = call.data.get(ATTR_TITLE)
    if target.kind == "service":
        payload: dict[str, Any] = {ATTR_MESSAGE: message}
        if title:
            payload[ATTR_TITLE] = title
        if ATTR_DATA in call.data:
            payload[ATTR_DATA] = call.data[ATTR_DATA]
        await hass.services.async_call(
            NOTIFY_DOMAIN, target.target, payload, blocking=True, context=call.context
        )
    else:
        payload = {"entity_id": target.target, ATTR_MESSAGE: message}
        if title:
            payload[ATTR_TITLE] = title
        await hass.services.async_call(
            NOTIFY_DOMAIN, "send_message", payload, blocking=True, context=call.context
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Person Notify from a config entry."""

    async def handle_send(call: ServiceCall) -> ServiceResponse:
        result: dict[str, Any] = {"notified": {}, "failed": {}, "warnings": []}
        targets: dict[NotifyTarget, None] = {}  # ordered, de-duplicated

        for person in call.data[ATTR_PERSON]:
            found = resolve_targets(hass, person)
            if not found:
                msg = f"No notify-capable devices found for {person}"
                _LOGGER.warning(msg)
                result["warnings"].append(msg)
            for t in found:
                targets.setdefault(t)

        outcomes = await asyncio.gather(
            *(_notify(hass, t, call) for t in targets), return_exceptions=True
        )
        for t, outcome in zip(targets, outcomes):
            if isinstance(outcome, Exception):
                _LOGGER.warning("Failed to notify %s: %s", t.display, outcome)
                result["failed"][t.display] = str(outcome)
            else:
                result["notified"][t.display] = t.device_name

        return result if call.return_response else None

    async def handle_get_targets(call: ServiceCall) -> ServiceResponse:
        return {
            person: [t.as_dict() for t in resolve_targets(hass, person)]
            for person in call.data[ATTR_PERSON]
        }

    hass.services.async_register(
        DOMAIN, SERVICE_SEND, handle_send, SEND_SCHEMA, SupportsResponse.OPTIONAL
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_TARGETS,
        handle_get_targets,
        TARGETS_SCHEMA,
        SupportsResponse.ONLY,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.services.async_remove(DOMAIN, SERVICE_SEND)
        hass.services.async_remove(DOMAIN, SERVICE_GET_TARGETS)
    return unloaded
