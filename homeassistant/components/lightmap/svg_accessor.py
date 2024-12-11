"""Handles svg-related operations for the Lightmap component."""

import re
from lxml.etree import Element, parse
from homeassistant.components.lightmap.types import RoomDimensions

# from defusedxml.ElementTree import parse
from typing import Optional

NS = {"svg": "http://www.w3.org/2000/svg"}


def extract_rooms_from_svg(svg_path: str) -> list[Element]:
    """Extract room names from an SVG file.

    Args:
        svg_path (str): Path to the SVG file.

    Returns:
        list[Element]: A list of room elements.

    """
    element_id = "Rooms"
    rooms_group = get_element(svg_path, element_id)

    return rooms_group.findall("svg:g", NS) if rooms_group is not None else []


def get_element_coordinates(svg_path: str, element_id: str) -> tuple[float, float]:
    """Extract the x and y coordinates of an SVG element by its ID relative to the document.

    Args:
        svg_path (str): Path to the SVG file.
        element_id (str): ID of the element to locate.

    Returns:
        Tuple[float, float]: A tuple (x, y) with the element's coordinates, or None if not found.

    """
    element = get_element(svg_path, element_id)

    if element is None:
        return 0, 0
    x = float(element.attrib.get("cx", 0))
    y = float(element.attrib.get("cy", 0))
    return x, y


def get_room_from_element(svg_path: str, element_id: str) -> str | None:
    """Extract the ID of the rect the given element is in.

    Args:
        svg_path (str): Path to the SVG file.
        element_id (str): ID of the element to locate.

    Returns:
        String representing the name of the room an element is in, or None if not found.

    """

    def is_element_within_room(
        element_x, element_y, room_x, room_y, room_width, room_height
    ):
        """Check if the element is within the bounds of the room."""
        return (
            room_width > 0
            and room_height > 0
            and room_x <= element_x <= (room_x + room_width)
            and room_y <= element_y <= (room_y + room_height)
        )

    element_x, element_y = get_element_coordinates(svg_path, element_id)
    if element_x is None or element_y is None:
        return None

    translate_x, translate_y = get_translation_from_svg(svg_path, "Rooms")
    rooms = extract_rooms_from_svg(svg_path)

    for room in rooms:
        room_rect = room.find("svg:rect", NS)
        if room_rect is None:
            continue

        room_x = float(room_rect.attrib.get("x", 0)) + translate_x
        room_y = float(room_rect.attrib.get("y", 0)) + translate_y
        room_width = float(room_rect.attrib.get("width", 0))
        room_height = float(room_rect.attrib.get("height", 0))

        if is_element_within_room(
            element_x, element_y, room_x, room_y, room_width, room_height
        ):
            return room.attrib.get("id")

    return None


def get_room_rect_dimensions(room_parent_element: Element) -> RoomDimensions | None:
    """
    Get the dimensions of a room rectangle

    Args:
        room_parent_element (str): Parent element of the room.

    Returns:
        A dict containing dimension information of the rectangle element.
    """
    rect = room_parent_element.find("svg:rect", NS)

    if rect is None:
        return None

    return {
        "width": rect.attrib.get("width"),
        "height": rect.attrib.get("height"),
        "x": rect.attrib.get("x"),
        "y": rect.attrib.get("y"),
    }


def get_element(svg_path: str, element_id: str) -> Optional[Element]:
    """Extract an element by its ID.

    Args:
        svg_path (str): Path to the SVG file.
        element_id (str): ID of the element to locate.

    Returns:
        The XML element matching the given ID, or None if not found.

    """
    tree = parse(svg_path)
    root = tree.getroot()

    element = root.find(f".//*[@id='{element_id}']", NS)
    if element is not None:
        return element

    return None


def get_translation_from_svg(svg_path: str, group_id: str) -> tuple[float, float]:
    """Extract the translation values from a group's transform attribute.

    Args:
        svg_path (str): Path to the SVG file.
        group_id (str): ID of the group to extract the translation from.

    Returns:
        tuple[float, float]: The translation values (translate_x, translate_y).

    """
    tree = parse(svg_path)
    root = tree.getroot()

    group = root.find(f".//svg:g[@id='{group_id}']", NS)
    if group is None:
        return (0.0, 0.0)

    transform = group.attrib.get("transform", "")
    match = re.search(r"translate\((-?\d+\.?\d*),\s*(-?\d+\.?\d*)\)", transform)
    if match:
        translate_x, translate_y = map(float, match.groups())
        return translate_x, translate_y

    return (0.0, 0.0)
