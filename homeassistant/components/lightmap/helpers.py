from homeassistant.core import HomeAssistant


def get_sensors(hass: HomeAssistant) -> list:
    """Function to retrieve all lightmap sensors"""
    all_states = hass.states.async_all()
    return [
        state.entity_id
        for state in all_states
        if state.entity_id.startswith("sensor.")
        and (
            state.attributes.get("device_class") == "illuminance"
            or state.attributes.get("unit_of_measurement") == "lux"
        )
    ]


def get_sensor_range(hass: HomeAssistant, entity_id) -> tuple[float, float] | None:
    """Retrieve the defined min and max range of a sensor.

    Args:
        hass: hass object to access states.
        entity_id: sensor ID that range is from

    Returns:
        tuple{min, max} representing the range of the sensor

    """
    state = hass.states.get(entity_id)
    if not state:
        return None

    min_value = state.attributes.get("min_value")
    max_value = state.attributes.get("max_value")
    if min_value is None or max_value is None:
        return None
    return min_value, max_value
