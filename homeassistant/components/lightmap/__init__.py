"""Lightmap Component for Home Assistant.

This component provides a custom visualization tool to display light readings
from sensors using an SVG-based floorplan.
"""

from datetime import timedelta
import logging

from homeassistant.components.lightmap.lightmap import LightMapSensor
from homeassistant.core import HomeAssistant

DOMAIN = "lightmap"
LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Setup the lightmap component"""

    sensor_config_list = config.get("mqtt", {}).get("sensor")

    lightmap_sensors = []
    for sensor in sensor_config_list:
        lightmap_sensors.append(
            LightMapSensor(
                sensor_svg_id=f"sensor.{sensor["name"]}",
                sensor_max=4095,
                sensor_min=0,
                hass=hass,
            ),
        )

    async def periodic_lightmap_update():
        """Action for periodically updating the lightmap"""
        for sensor in lightmap_sensors:
            await sensor.update_lightmap()

    hass.helpers.event.async_track_time_interval(
        hass, periodic_lightmap_update, timedelta(seconds=20)
    )

    return True
