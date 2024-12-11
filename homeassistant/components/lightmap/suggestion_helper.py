"""Handles helper functions for the suggestion feature."""

from datetime import UTC, datetime, timedelta
import statistics

from homeassistant.components.lightmap.helpers import get_sensor_range, get_sensors
from homeassistant.core import HomeAssistant


async def get_average_light_sensors(hass: HomeAssistant, hours=48) -> dict:
    """Get average values of light sensors over the past X hours.

    Args:
        hass: hass object to access states.
        hours: representing the number of hours back from current time.

    Returns:
        dict of sensor average values over the period.

    """

    light_sensors = get_sensors(hass)

    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)

    history = await hass.async_add_executor_job(
        hass.components.recorder.history.get_significant_states,
        hass,
        start_time.astimezone(UTC),
        end_time.astimezone(UTC),
        light_sensors,
    )

    averages = {}
    for entity_id, states in history.items():
        values = [float(state.state) for state in states if is_number(state.state)]
        if values:
            averages[entity_id] = statistics.mean(values)

    return averages


async def get_sensors_in_category_range(hass: HomeAssistant, category: str) -> dict:
    """Extract sensors that fall within a category.

    Args:
        hass: hass object to access states.
        category: category to match sensors with

    Returns:
        A dict of sensors that fall within a given category

    """
    low_category_value: float = 0.0
    med_category_value: float = 0.0
    within_category = {}

    sensor_averages = await get_average_light_sensors(hass)
    if sensor_averages is not None:
        for entity_id, average_value in sensor_averages.items():
            sensor_range = get_sensor_range(hass, entity_id)
            if sensor_range is None:
                continue
            min_value, max_value = sensor_range
            min_value = int(min_value)
            max_value = int(max_value)
            updated_max = (
                max_value - min_value if min_value >= 0 else max_value + abs(min_value)
            )
            low_category_value = updated_max * (33 / 100)
            med_category_value = updated_max * (66 / 100)

            if (
                (category.lower() == "low" and average_value <= low_category_value)
                or (
                    category.lower() == "medium"
                    and low_category_value < average_value <= med_category_value
                )
                or (category.lower() == "high" and average_value > med_category_value)
            ):
                within_category[entity_id] = average_value

    return within_category


def is_number(value) -> bool:
    """Try parse the value to a float to confirm it's a number.

    Args:
        value: Numeric value to be parsed to float.

    Returns:
        True if value can be parsed or false if not.

    """
    try:
        float(value)
    except (ValueError, TypeError):
        return False
    else:
        return True
