"""Lightmap Component for Home Assistant.

This component provides a custom visualization tool to display light readings
from sensors using an SVG-based floorplan.
"""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Protocol

from homeassistant.components.media_source import (
    MediaSource,
    MediaSourceError,
    MediaSourceItem,
)

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.lightmap.lightmap import LightMapSensor
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
import os

DOMAIN = "lightmap"
LOGGER = logging.getLogger(__name__)

from . import storage_handler
from .const import (
    DOMAIN,
    MEDIA_CLASS_MAP,
    MEDIA_MIME_TYPES,
    URI_SCHEME,
    URI_SCHEME_REGEX,
)


__all__ = [
    "DOMAIN",
    "is_media_source_id",
    "generate_media_source_id",
    "MediaSourceItem",
    "MediaSource",
    "MediaSourceError",
    "MEDIA_CLASS_MAP",
    "MEDIA_MIME_TYPES",
]

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


class LightMapProtocol(Protocol):
    """Define the format of lightmap platforms."""

    async def async_get_media_source(self, hass: HomeAssistant) -> MediaSource:
        """Set up media source."""


def is_media_source_id(media_content_id: str) -> bool:
    """Test if identifier is a media source."""
    return URI_SCHEME_REGEX.match(media_content_id) is not None


def generate_media_source_id(domain: str, identifier: str) -> str:
    """Generate a media source ID."""
    uri = f"{URI_SCHEME}{domain or ''}"
    if identifier:
        uri += f"/{identifier}"
    return uri


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Setup the lightmap component"""
    # Check if SVG is stored. If not, then dont run the following code until it
    # is stored.
    sensor_config_list = config.get("mqtt", {}).get("sensor")

    lightmap_sensors = []
    for sensor in sensor_config_list:
        lightmap_sensors.append(
            LightMapSensor(
                sensor_svg_id=f"sensor.{sensor["name"]}",
                sensor_max=4095,
                sensor_min=0,
                hass=hass,
                svg_containing_sensor_path=SVG_PATH,  # Remove when have storage merged
            ),
        )

    async def periodic_lightmap_update(_now):
        """Action for periodically updating the lightmap"""
        for sensor in lightmap_sensors:
            sensor.update_lightmap()
        hass.bus.fire("lightmap_update_event", {"svg_path": "svg_path_string"})
        LOGGER.info("Lightmap update event has been fired")

    async_track_time_interval(hass, periodic_lightmap_update, timedelta(seconds=60))

    hass.helpers.event.async_track_state_change(sensor_ids, sensor_state_change)
    hass.data[DOMAIN] = {}
    storage_handler.async_setup(hass)
    return True
