"""Lightmap Component for Home Assistant.

This component provides a custom visualization tool to display light readings
from sensors using an SVG-based floorplan.
"""

from __future__ import annotations

import logging
from typing import Protocol

from homeassistant.components.media_source import (
    MediaSource,
    MediaSourceError,
    MediaSourceItem,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from . import plant_placement, storage_handler
from .const import (
    DOMAIN,
    MEDIA_CLASS_MAP,
    MEDIA_MIME_TYPES,
    URI_SCHEME,
    URI_SCHEME_REGEX,
)
from .plant_placement import PlantInfoView

LOGGER = logging.getLogger(__name__)

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
    """Set up the lightmap component."""
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
    hass.data[DOMAIN] = {}
    hass.http.register_view(PlantInfoView())
    storage_handler.async_setup(hass)
    plant_placement.async_setup(hass, config)
    return True
