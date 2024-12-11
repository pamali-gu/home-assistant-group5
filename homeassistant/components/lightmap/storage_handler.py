"""Handles persistent storage for the Lightmap component.

This module manages the storage of the svg file.
"""

from __future__ import annotations

import logging
from pathlib import Path
import shutil

from aiohttp import web
from aiohttp.web_request import FileField
import voluptuous as vol

from homeassistant.components import http
from homeassistant.components.http import require_admin
from homeassistant.components.media_source import (
    MediaSource,
    MediaSourceItem,
    Unresolvable,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import raise_if_invalid_filename, raise_if_invalid_path

from .const import DOMAIN

MAX_UPLOAD_SIZE = 1024 * 1024 * 10
LOGGER = logging.getLogger(__name__)


@callback
def async_setup(hass: HomeAssistant) -> None:
    """Set up storage handler source."""
    source = StorageHandler(hass)
    hass.data[DOMAIN][DOMAIN] = source
    hass.http.register_view(UploadSVGImageView(hass, source))


class StorageHandler(MediaSource):
    """Provide local directories as media sources."""

    name: str = "SVG media"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize storage handler."""
        super().__init__(DOMAIN)
        self.hass = hass

    @callback
    def async_full_path(self, source_dir_id: str, location: str) -> Path:
        """Return full path."""
        base_path = self.hass.config.media_dirs[source_dir_id]
        full_path = Path(base_path, location)
        full_path.relative_to(base_path)
        return full_path

    @callback
    def async_parse_identifier(self, item: MediaSourceItem) -> tuple[str, str]:
        """Parse identifier."""
        if item.domain != DOMAIN:
            raise Unresolvable("Unknown domain.")

        source_dir_id, _, location = item.identifier.partition("/")
        if source_dir_id not in self.hass.config.media_dirs:
            raise Unresolvable("Unknown source directory.")

        try:
            raise_if_invalid_path(location)
        except ValueError as err:
            raise Unresolvable("Invalid path.") from err

        if Path(location).is_absolute():
            raise Unresolvable("Invalid path.")

        return source_dir_id, location


class UploadSVGImageView(http.HomeAssistantView):
    """View to upload svg images."""

    url = "/api/lightmap/storage_handler/upload"
    name = "api:lightmap:storage_handler:upload"

    def __init__(self, hass: HomeAssistant, source: StorageHandler) -> None:
        """Initialize the media view."""
        self.hass = hass
        self.source = source
        self.schema = vol.Schema(
            {
                "media_content_id": str,
                "file": FileField,
            }
        )

    @require_admin
    async def post(self, request: web.Request) -> web.Response:
        """Handle upload."""
        # Increase max payload
        request._client_max_size = MAX_UPLOAD_SIZE  # noqa: SLF001

        try:
            data = self.schema(dict(await request.post()))
        except vol.Invalid as err:
            LOGGER.error("Received invalid upload data: %s", err)
            raise web.HTTPBadRequest from err

        try:
            item = MediaSourceItem.from_uri(self.hass, data["media_content_id"], None)
        except ValueError as err:
            LOGGER.error("Received invalid upload data: %s", err)
            raise web.HTTPBadRequest from err

        try:
            source_dir_id, location = self.source.async_parse_identifier(item)
        except Unresolvable as err:
            LOGGER.error("Invalid local source ID")
            raise web.HTTPBadRequest from err

        uploaded_file: FileField = data["file"]

        if not uploaded_file.content_type.startswith("image/"):
            LOGGER.error("Content type not allowed")
            raise vol.Invalid("Only SVG images are allowed")

        try:
            raise_if_invalid_filename(uploaded_file.filename)
        except ValueError as err:
            LOGGER.error("Invalid filename")
            raise web.HTTPBadRequest from err

        try:
            await self.hass.async_add_executor_job(
                self._move_file,
                self.source.async_full_path(source_dir_id, location),
                uploaded_file,
            )
        except ValueError as err:
            LOGGER.error("Moving upload failed: %s", err)
            raise web.HTTPBadRequest from err

        # Fire an event that the SVG has been successfully uploaded
        self.hass.bus.fire(
            "svg_uploaded",
            {
                "svg_path": str(
                    self.source.async_full_path(source_dir_id, location)
                    / uploaded_file.filename
                )
            },
        )
        return self.json(
            {"media_content_id": f"{data['media_content_id']}/{uploaded_file.filename}"}
        )

    def _move_file(self, target_dir: Path, uploaded_file: FileField) -> None:
        """Move file to target."""
        if not target_dir.is_dir():
            raise ValueError("Target is not an existing directory")

        target_path = target_dir / uploaded_file.filename

        target_path.relative_to(target_dir)
        raise_if_invalid_path(str(target_path))

        with target_path.open("wb") as target_fp:
            shutil.copyfileobj(uploaded_file.file, target_fp)
