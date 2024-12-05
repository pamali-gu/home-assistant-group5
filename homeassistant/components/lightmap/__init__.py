"""Lightmap Component for Home Assistant.

This component provides a custom visualization tool to display light readings
from sensors using an SVG-based floorplan.
"""

from __future__ import annotations

from typing import Protocol

from homeassistant.components.media_source import (
    MediaSource,
    MediaSourceError,
    MediaSourceItem,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

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
    """Set up the lightmap component."""
    hass.data[DOMAIN] = {}
    storage_handler.async_setup(hass)
    return True
