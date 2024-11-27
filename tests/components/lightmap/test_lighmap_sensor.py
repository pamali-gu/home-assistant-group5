"""The test for lightmap svg access functions."""

from homeassistant.components.lightmap.lightmap import LightMapSensor

SVG_PATH = "./tests/components/lightmap/Floorplan-2.svg"
SENSOR_SVG_ID = "test_circle"
group_id = "Rooms"


SENSOR_MAX = 4096
SENSOR_MIN = 0


def test_calculate_light_radial() -> None:
    living_room_svg_sensor = LightMapSensor(
        sensor_svg_id=SENSOR_SVG_ID,
        sensor_reading=500.5,
        sensor_max=SENSOR_MAX,
        sensor_min=SENSOR_MIN,
        svg_containing_sensor_path=SVG_PATH,
    )

    living_room_svg_sensor.calculate_light_radial()
