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
