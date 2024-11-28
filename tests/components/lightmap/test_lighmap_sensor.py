"""The test for lightmap svg access functions."""

from homeassistant.components.lightmap.lightmap import LightMapSensor

SVG_PATH = "./tests/components/lightmap/Floorplan-2.svg"
SENSOR_SVG_ID = "test_circle"
group_id = "Rooms"


SENSOR_MAX = 4095
SENSOR_MIN = 0


def test_calculate_light_radial() -> None:
    living_room_svg_sensor = LightMapSensor(
        sensor_svg_id=SENSOR_SVG_ID,
        sensor_reading=4095,
        sensor_max=SENSOR_MAX,
        sensor_min=SENSOR_MIN,
        svg_containing_sensor_path=SVG_PATH,
    )

    living_room_svg_sensor.calculate_light_radial()


def test_sensor_to_radius_conversion_happy() -> None:
    """tests the radius calculation"""

    living_room_svg_sensor = LightMapSensor(
        sensor_svg_id=SENSOR_SVG_ID,
        sensor_reading=4095,
        sensor_max=SENSOR_MAX,
        sensor_min=SENSOR_MIN,
        svg_containing_sensor_path=SVG_PATH,
    )

    expected_radius = 30.0
    result_radius = living_room_svg_sensor._convert_sensor_to_radius()

    assert expected_radius == result_radius


def test_sensor_normalization_happy() -> None:
    """Test the normalization of offset values"""

    living_room_svg_sensor = LightMapSensor(
        sensor_svg_id=SENSOR_SVG_ID,
        sensor_reading=4095,
        sensor_max=SENSOR_MAX,
        sensor_min=SENSOR_MIN,
        svg_containing_sensor_path=SVG_PATH,
    )

    result_offset = living_room_svg_sensor._normalize_sensor_reading()
    expected_offset = 1.0
    assert expected_offset == result_offset
