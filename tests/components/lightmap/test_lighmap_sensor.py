"""The test for lightmap svg access functions."""

import pytest
from homeassistant.components.lightmap.lightmap import LightMapSensor
from unittest.mock import MagicMock
from homeassistant.core import HomeAssistant

SVG_PATH = "./tests/components/lightmap/Floorplan-2.svg"
SENSOR_SVG_ID = "test_circle"
group_id = "Rooms"


SENSOR_MAX = 4095
SENSOR_MIN = 0


@pytest.fixture
def mock_hass(mocker, mock_sensor_value: float):
    """Fixture to mock HASS"""
    hass = MagicMock(spec=HomeAssistant)

    hass.states = MagicMock()

    hass.states.get.return_value = MagicMock(state=mock_sensor_value)

    return hass


@pytest.mark.parametrize("mock_sensor_value", [(4095)])
def test_calculate_light_radial(mock_hass) -> None:
    living_room_svg_sensor = LightMapSensor(
        sensor_svg_id=SENSOR_SVG_ID,
        sensor_max=SENSOR_MAX,
        sensor_min=SENSOR_MIN,
        svg_containing_sensor_path=SVG_PATH,
        hass=mock_hass,
    )

    living_room_svg_sensor.update_lightmap()


@pytest.mark.parametrize("mock_sensor_value", [(4095)])
def test_sensor_to_radius_conversion_happy(mock_hass) -> None:
    """tests the radius calculation"""

    living_room_svg_sensor = LightMapSensor(
        sensor_svg_id=SENSOR_SVG_ID,
        sensor_max=SENSOR_MAX,
        sensor_min=SENSOR_MIN,
        svg_containing_sensor_path=SVG_PATH,
        hass=mock_hass,
    )

    expected_radius = 30.0
    result_radius = living_room_svg_sensor._convert_sensor_to_radius(4095)

    assert expected_radius == result_radius


@pytest.mark.parametrize("mock_sensor_value", [(4095)])
def test_sensor_normalization_happy(mock_hass) -> None:
    """Test the normalization of offset values"""

    living_room_svg_sensor = LightMapSensor(
        sensor_svg_id=SENSOR_SVG_ID,
        sensor_max=SENSOR_MAX,
        sensor_min=SENSOR_MIN,
        svg_containing_sensor_path=SVG_PATH,
        hass=mock_hass,
    )

    result_offset = living_room_svg_sensor._normalize_sensor_reading(4095)
    expected_offset = 1.0
    assert expected_offset == result_offset
