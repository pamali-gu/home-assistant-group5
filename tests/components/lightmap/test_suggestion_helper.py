"""The test for suggestion feature helper functions."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.components.lightmap.suggestion_helper import (
    get_average_light_sensors,
    get_sensor_range,
    get_sensors_in_category_range,
    is_number,
)
from homeassistant.core import HomeAssistant


@pytest.mark.asyncio
async def test_get_average_light_sensors() -> None:
    """Test the get_average_light_sensors function.

    The test checks that:
    - The correct average values are returned given the mocked data
    """
    mock_hass = MagicMock()
    mock_hass.states.async_all.return_value = [
        MagicMock(
            entity_id="sensor.light_1",
            attributes={"device_class": "illuminance", "unit_of_measurement": "lux"},
        ),
        MagicMock(
            entity_id="sensor.temperature",
            attributes={"device_class": "temperature", "unit_of_measurement": "°C"},
        ),
        MagicMock(
            entity_id="sensor.light_2",
            attributes={"device_class": "illuminance", "unit_of_measurement": "lux"},
        ),
    ]

    mock_history = {
        "sensor.light_1": [
            MagicMock(state="100"),
            MagicMock(state="200"),
            MagicMock(state="300"),
        ],
        "sensor.light_2": [
            MagicMock(state="400"),
            MagicMock(state="500"),
        ],
    }

    mock_hass.async_add_executor_job = AsyncMock(return_value=mock_history)

    averages = await get_average_light_sensors(mock_hass, hours=24)

    assert averages == {
        "sensor.light_1": 200.0,
        "sensor.light_2": 450.0,
    }
    assert averages is not None


@pytest.mark.asyncio
async def test_get_sensors_in_category_range(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the get_sensors_in_category_range function.

    The test checks that:
    - The correct sensors are returned for a given category based on the mocked data
    """
    mock_hass = MagicMock()
    mock_hass.states.get = MagicMock(
        side_effect={
            "sensor.light_1": MagicMock(attributes={"min_value": 0, "max_value": 300}),
            "sensor.light_2": MagicMock(attributes={"min_value": 0, "max_value": 600}),
        }.get
    )

    async def mock_get_average_light_sensors(hass: HomeAssistant):
        return {"sensor.light_1": 50, "sensor.light_2": 450}

    monkeypatch.setattr(
        "homeassistant.components.lightmap.suggestion_helper.get_average_light_sensors",
        mock_get_average_light_sensors,
    )

    low_sensors = await get_sensors_in_category_range(mock_hass, category="low")
    medium_sensors = await get_sensors_in_category_range(mock_hass, category="medium")
    high_sensors = await get_sensors_in_category_range(mock_hass, category="high")

    assert low_sensors == {"sensor.light_1": 50}
    assert medium_sensors == {}
    assert high_sensors == {"sensor.light_2": 450}
    assert low_sensors is not None


def test_get_sensor_range() -> None:
    """Test the get_sensor_range function.

    The test checks that:
    - The correct min and max values are returned given the mocked data
    """
    mock_hass = MagicMock()
    mock_hass.states.get = MagicMock(
        return_value=MagicMock(attributes={"min_value": 0, "max_value": 500})
    )

    min_value, max_value = get_sensor_range(mock_hass, "sensor.light_1")
    assert min_value == 0
    assert max_value == 500

    mock_hass.states.get = MagicMock(return_value=None)
    sensor_range = get_sensor_range(mock_hass, "sensor.unknown")
    assert sensor_range is None


def test_is_number() -> None:
    """Test the is_number function.

    The test checks that:
    - The correct boolean values are returned for a given value parameter
    """
    assert is_number("100") is True
    assert is_number("abc") is False
    assert is_number(None) is False
    assert is_number("123.45") is True
    assert is_number("-123.45") is True
    assert is_number("1") is not None
