"""Module for handling plant information requests using the Gemini API."""

import logging
from typing import Any

import aiohttp
from aiohttp import ClientTimeout
import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.websocket_api import bind_hass
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.typing import ConfigType

from .suggestion_helper import get_sensors_in_category_range

_LOGGER = logging.getLogger(__name__)

# Define the Gemini API URL
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
timeout = ClientTimeout(total=10.0)


@callback
def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up plant_placement."""
    if "lightmap" in config:
        gemini_api_key = config["lightmap"]["gemini_api_key"]
        hass.data["lightmap"] = {"gemini_api_key": gemini_api_key}

    websocket_api.async_register_command(hass, websocket_chat_gemini)
    return True


class PlantInfoView(HomeAssistantView):
    """Endpoint to fetch plant information using Gemini API."""

    url = "/api/light-map/plant-info"
    name = "api:light-map:plant-info"
    requires_auth = True


@bind_hass
async def async_access_gemini(hass: HomeAssistant, plant_name: str | None) -> str:
    """Return light density details from Gemini API based on the given plant name."""

    if not plant_name:
        raise HomeAssistantError("Plant name is required")

    # Prepare the Gemini API request
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"""how much light density {plant_name} plant need from the categories: low, medium, high?
                        provide only the correct level if it is close enough to a valid plant name.
                        If not return only INVALID. """
                    }
                ]
            }
        ]
    }
    headers = {"Content-Type": "application/json"}
    url = f"{GEMINI_API_URL}?key={hass.data["lightmap"]["gemini_api_key"]}"

    try:
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                url, json=payload, headers=headers, timeout=timeout
            ) as response,
        ):
            if response.status != 200:
                _LOGGER.error("Gemini API request failed: %s", await response.text())
                raise HomeAssistantError("Failed to fetch plant information")

            # Parse the JSON response
            gemini_response = await response.json()
            return (
                gemini_response.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
            )
    except aiohttp.ClientError as e:
        _LOGGER.error("HTTP request failed: %s", str(e))
        return ""


@websocket_api.websocket_command(
    {
        vol.Required("type"): "light-map/plant-info",
        vol.Required("plant_name"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_chat_gemini(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return plant placement suggestions with regard to sensor details."""
    try:
        gemini_response = await async_access_gemini(hass, msg["plant_name"])

        if gemini_response.lower() == "invalid" or all(
            word not in gemini_response.lower() for word in ("low", "medium", "high")
        ):
            connection.send_result(
                msg["id"],
                {
                    "light_density": gemini_response,
                    "sensors": {},
                    "message": "INVALID PLANT NAME",
                },
            )
            return

        sensor_list = await get_sensors_in_category_range(hass, gemini_response.lower())
        connection.send_result(
            msg["id"],
            {
                "light_density": gemini_response,
                "sensors": sensor_list,
                "message": "SUCCESS",
            },
        )
    except HomeAssistantError as ex:
        _LOGGER.error("Error requesting gemini: %s", ex)
        connection.send_error(msg["id"], "gemini_request_failed", str(ex))
