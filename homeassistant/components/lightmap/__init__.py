"""Lightmap Component for Home Assistant.

This component provides a custom visualization tool to display light readings
from sensors using an SVG-based floorplan.
"""

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_state_change
import logging

DOMAIN = "lightmap"
LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Setup the lightmap component"""

    sensor_config_list = config.get("mqtt", {}).get("sensor")

    sensor_ids = []
    for sensor in sensor_config_list:
        sensor_ids.append(f"sensor.{sensor["name"]}")

    async def sensor_state_change(entity_id, old_state, new_state):
        if new_state:
            LOGGER.debug(f"sensor with id: {entity_id} has new reading: {new_state}")
        else:
            LOGGER.debug("no change")

    hass.helpers.event.async_track_state_change(sensor_ids, sensor_state_change)
    return True
