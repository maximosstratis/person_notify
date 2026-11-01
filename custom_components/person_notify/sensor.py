"""Sensors showing the notify targets of each person."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, EntityCategory
from homeassistant.core import CoreState, Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN
from .resolver import resolve_targets


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create one sensor per person."""
    known: set[str] = set()

    @callback
    def add_new(_event: Event | None = None) -> None:
        new = [p for p in hass.states.async_entity_ids("person") if p not in known]
        known.update(new)
        if new:
            async_add_entities(PersonTargetsSensor(p) for p in new)

    add_new()
    if hass.state is not CoreState.running:
        entry.async_on_unload(
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, add_new)
        )


class PersonTargetsSensor(SensorEntity):
    """Number of notify targets for a person; list in attributes."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:bell-ring-outline"
    _attr_native_unit_of_measurement = "devices"

    def __init__(self, person_id: str) -> None:
        self._person_id = person_id
        self._attr_unique_id = f"{DOMAIN}_{person_id}"
        self.entity_id = f"sensor.{person_id.split('.', 1)[1]}_notify_targets"

    @property
    def name(self) -> str:
        state = self.hass.states.get(self._person_id) if self.hass else None
        friendly = state.name if state else self._person_id
        return f"{friendly} notify targets"

    @callback
    def _refresh(self, _event: Event | None = None) -> None:
        targets = resolve_targets(self.hass, self._person_id)
        self._attr_native_value = len(targets)
        self._attr_extra_state_attributes = {
            "person": self._person_id,
            "targets": [t.display for t in targets],
            "devices": sorted({t.device_name for t in targets}),
        }
        if self.entity_id and self.hass:
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_track_state_change_event(self.hass, [self._person_id], self._refresh)
        )
        self.async_on_remove(
            self.hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, self._refresh)
        )
        self.async_on_remove(
            self.hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, self._refresh)
        )
        self._refresh()
