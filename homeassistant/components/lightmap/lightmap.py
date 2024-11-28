"""Core logic for the Lightmap component.

This module handles the integration of sensors, updates SVG styling
based on sensor values.



Assumptions and Scope:
  - Sensor placement:
    Either:
        - The sensors are placed at or near the light source.
            - In other words, if the sensor picks up a lightsource,
              we assume the further we move from the sensor in any direction,
              the less light we get.
    OR:
        - The sensors are placed on the plant itself.

    With both options we cannot ensure 100% accurate radials, but the above
    two options are ways to increase the accuracy.


    To ensure more accuracy, light radials of multiple sensors can overlap,
    where the radial with a higher reading takes precedence over lower level 
    radials.


    OR we just assume the point of the sensor WITHOUT gradient.
"""

from homeassistant.components.lightmap.svg_accessor import (
    get_room_from_element,
    get_element_coordinates,
    get_element,
    get_room_rect_dimensions,
    get_translation_from_svg,
)
from lxml.etree import Element, SubElement
from defusedxml.ElementTree import parse


class InvalidSensorReading(Exception):
    def __init__(self, message, errors):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)


class LightMapSensor:
    """Class that tracks sensors in the SVG"""

    _sensor_svg_id: str
    _sensor_reading: float
    _sensor_max: float
    _sensor_min: float
    _svg_path: str
    _MAX_RADIAL_RADIUS: float
    _MIN_RADIAL_RADIUS: float = 0.0

    # This was determine based on our Sensor with a max value of 4095,
    # where 4095 would correspond to a max radius of 30. (4095/30 = 136.5)
    # If a sensor has a different max, we will divide it by this constant to
    # determine the radius max accordingly.
    _RADIUS_CONSTANT: float = 136.5
    _MAX_OFFSET: float = 50.0

    def __init__(
        self,
        sensor_svg_id: str,
        sensor_reading: float,
        sensor_max: float,
        sensor_min: float,
        svg_containing_sensor_path: str,
    ):
        self._sensor_svg_id = sensor_svg_id
        self._sensor_reading = sensor_reading
        self._sensor_max = sensor_max
        self._sensor_min = sensor_min
        self._svg_path = svg_containing_sensor_path

        self._MAX_RADIAL_RADIUS = self._sensor_max / self._RADIUS_CONSTANT

    def set_sensor_id(self, sensor_id: str) -> None:
        """Set the sensor id"""
        self._sensor_svg_id = sensor_id

    def get_sensor_id(self) -> str:
        """Get the sensor id"""
        return self._sensor_id

    def set_sensor_reading(self, sensor_reading: float) -> None:
        """Set the sensor reading"""
        if sensor_reading < self._sensor_min or sensor_reading > self._sensor_max:
            raise InvalidSensorReading(
                f"""Sensor reading is not within the defined limits:
                {self._sensor_min}-{self._sensor_max}"""
            )
        self._sensor_reading = sensor_reading

    def get_sensor_reading(self) -> float:
        """Get the sensor reading"""
        return self._sensor_reading

    def set_sensor_max(self, max: float):
        self._sensor_max = max

    def get_sensor_max(self):
        return self._sensor_max

    def set_sensor_min(self, min: float):
        self._sensor_min = min

    def get_svg_containing_sensor_path(self) -> str:
        return self._svg_path

    def set_svg_containing_sensor_path(self, svg_path: str) -> None:
        self._svg_path = svg_path

    def _convert_sensor_to_radius(self) -> float:
        """Convert sensor reading to corresponding radius values."""
        return self._MIN_RADIAL_RADIUS + (
            (self._sensor_reading - self._sensor_min)
            / (self._sensor_max - self._sensor_min)
            * (self._MAX_RADIAL_RADIUS - self._MIN_RADIAL_RADIUS)
        )

    def _normalize_sensor_reading(self) -> float:
        return (self._sensor_reading - self._sensor_min) / (
            self._sensor_max - self._sensor_min
        )

    def calculate_light_radial(self):
        """
        Calculate light radial distance.

        Assumption: We assume that photoresistors are used where
        the light intesnity is proportional to the resistance -
        in other words, as light intensity increase, resistance increases.
        """
        room_id = get_room_from_element(
            self._svg_path, self._sensor_svg_id
        )  # Get room to know what to edit

        sensor_x, sensor_y = get_element_coordinates(
            self._svg_path, self._sensor_svg_id
        )  # Used for the center point of gradient

        # Now that we have the room element, we can get coords and put rectangle over it
        room_parent_element = get_element(self._svg_path, room_id)
        room_rectangle_dimensions = get_room_rect_dimensions(room_parent_element)

        new_rectangle = Element("rect")

        # Get translation of the Rooms element, make positive and put them on
        # the cx cy fx fy
        x_translation, y_translation = map(
            abs, get_translation_from_svg(self._svg_path, "Rooms")
        )

        # Get radial radius calculation.
        radius_val = self._convert_sensor_to_radius()

        # Get offset calculation
        radial_firststop_opacity = self._normalize_sensor_reading() * self._MAX_OFFSET

        # Process room element to get the coordinates of the rectangle.
        radial_gradient = Element("radialGradient")
        radial_gradient.set("id", f"radial-{self._sensor_svg_id}")
        radial_gradient.set("cx", str(sensor_x + x_translation))
        radial_gradient.set("cy", str(sensor_y + y_translation))
        radial_gradient.set("fx", str(sensor_x + x_translation))
        radial_gradient.set("fy", str(sensor_y + y_translation))
        radial_gradient.set("r", str(radius_val))
        radial_gradient.set("gradientTransfrom", "scale(1,1)")
        radial_gradient.set("gradientUnits", "userSpaceOnUse")

        first_gradient_stop = SubElement(radial_gradient, "stop")
        first_gradient_stop.set("offset", "0%")
        first_gradient_stop.set(
            "style",
            f"stop-color:rgba(255,255,10,1);stop-opacity:{str(radial_firststop_opacity)}",
        )
        first_gradient_stop.set("id", f"{radial_gradient.attrib.get("id")}-stop-1")

        second_gradient_stop = SubElement(radial_gradient, "stop")
        second_gradient_stop.set("offset", "100%")
        second_gradient_stop.set(
            "style", "stop-color:rgba(255,255,255,0); stop-opacity:0"
        )
        second_gradient_stop.set("id", f"{radial_gradient.attrib.get("id")}-stop-2")

        rect_params = {
            **room_rectangle_dimensions,
            "style": f"fill:url(#radial-{self._sensor_svg_id});fill-opacity:1;fill-rule:nonzero;stroke:#000000;stroke-width:4.17796;stroke-dasharray:none;stroke-opacity:0;paint-order:stroke markers fill",
        }

        for key, value in rect_params.items():
            new_rectangle.set(key, str(value))

        room_element_parent = room_parent_element.getparent()
        room_index = room_element_parent.index(room_parent_element)
        # Put new rectangle on top of old rectangle.
        room_element_parent.insert(room_index, new_rectangle)
        tree = room_element_parent.getroottree()
        root = tree.getroot()
        root.append(radial_gradient)
        tree.write(self._svg_path)
