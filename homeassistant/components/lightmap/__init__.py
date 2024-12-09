"""Lightmap Component for Home Assistant.

This component provides a custom visualization tool to display light readings
from sensors using an SVG-based floorplan.
"""

from datetime import timedelta
import logging

from homeassistant.components.lightmap.lightmap import LightMapSensor
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
import os

DOMAIN = "lightmap"
LOGGER = logging.getLogger(__name__)

SVG_PATH = os.path.join(os.path.dirname(__file__), "Floorplan-2.svg")


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
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

    async_track_time_interval(hass, periodic_lightmap_update, timedelta(seconds=5))

    return True
