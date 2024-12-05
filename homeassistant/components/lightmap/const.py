"""Constants for the lightmap integration."""

import re

from homeassistant.components.media_player import MediaClass

DOMAIN = "lightmap"
MEDIA_MIME_TYPES = "image"
MEDIA_CLASS_MAP = {
    "image": MediaClass.IMAGE,
}
URI_SCHEME = "media-source://"
URI_SCHEME_REGEX = re.compile(
    r"^media-source:\/\/(?:(?P<domain>(?!_)[\da-z_]+(?<!_))(?:\/(?P<identifier>(?!\/).+))?)?$"
)
