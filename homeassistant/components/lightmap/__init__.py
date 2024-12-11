"""Lightmap Component for Home Assistant.

This component provides a custom visualization tool to display light readings
from sensors using an SVG-based floorplan.
"""

from __future__ import annotations
import asyncio

from datetime import timedelta
import logging
from typing import Protocol
from pathlib import Path

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
from homeassistant.components.lightmap.helpers import get_sensors
import os

DOMAIN = "lightmap"
LOGGER = logging.getLogger(__name__)
MEDIA_DIR = Path("config/media/")

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


def _initialize_lightmap(
    hass: HomeAssistant, config: ConfigType, svg_path: str
) -> None:
    # Check if SVG is stored. If not, then dont run the following code until it
    # is stored.
    light_sensors = get_sensors(hass)

    lightmap_sensors = []
    for sensor in light_sensors:
        lightmap_sensors.append(
            LightMapSensor(
                sensor_svg_id=sensor,
                sensor_max=4095,
                sensor_min=0,
                hass=hass,
                svg_containing_sensor_path=svg_path,  # Remove when have storage merged
            ),
        )

    async def periodic_lightmap_update(_now):
        """Action for periodically updating the lightmap"""
        for sensor in lightmap_sensors:
            sensor.update_lightmap()
        hass.bus.fire("lightmap_update_event", {"svg_path": "svg_path_string"})
        LOGGER.info("Lightmap update event has been fired")

    async_track_time_interval(hass, periodic_lightmap_update, timedelta(seconds=10))


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Setup the lightmap component"""
    hass.data[DOMAIN] = {}
    storage_handler.async_setup(hass)

    svg_files = await asyncio.to_thread(lambda: list(MEDIA_DIR.glob("*.svg")))
    if svg_files:
        # Accessing 'first' svg found because
        # we assume only one svg exists when using lightmap
        svg_file_path = str(svg_files[0])
        _initialize_lightmap(hass, config, svg_file_path)
    else:
        LOGGER.info("No SVG found, watching for upload")

        async def handle_svg_upload(event):
            """Initialize lightmap when an SVG is uploaded"""
            LOGGER.info("SVG uploaded, initializing lightmap")
            svg_path = event.data.get("svg_path")
            if svg_path:
                _initialize_lightmap(hass, config, svg_path)

        hass.bus.async_listen("svg_uploaded", handle_svg_upload)

    return True
