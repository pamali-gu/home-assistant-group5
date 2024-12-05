"""The test for lightmap svg access functions."""

from homeassistant.components.lightmap.svg_accessor import (
    extract_rooms_from_svg,
    get_element,
    get_element_coordinates,
    get_room_from_element,
    get_translation_from_svg,
    get_room_rect_dimensions,
)

from lxml import etree

svg_path = "./tests/components/lightmap/Floorplan-2.svg"
test_element = "test_circle"
group_id = "Rooms"


def test_get_element() -> None:
    """Verify that get_element retrieves the correct SVG element by ID.

    The test checks that:
    - The element with the given ID exists in the SVG.
    - The retrieved element has the expected tag and attributes.
    - The retrieved element has the correct x coordinate
    """
    element = get_element(svg_path, test_element)
    assert element is not None
    assert element.tag.endswith("circle")
    assert element.attrib["cx"] == "80"


def test_extract_rooms_from_svg() -> None:
    """Ensure extract_rooms_from_svg retrieves all room elements from the 'Rooms' group.

    The test verifies:
    - The function correctly locates the 'Rooms' group.
    - The number of child elements are correct
    - The IDs of the extracted rooms match the expected values.
    """
    rooms = extract_rooms_from_svg(svg_path)
    assert len(rooms) == 8
    assert rooms[0].attrib["id"] == "LivingRoom"
    assert rooms is not None


def test_get_room_from_element() -> None:
    """Verify that get_room_from_element identifies the correct room containing a given element.

    The test checks:
    - The function correctly maps an element's position to the room it's located in.
    """
    room_id = get_room_from_element(svg_path, test_element)
    assert room_id == "LivingRoom"
    assert room_id is not None


def test_get_element_coordinates() -> None:
    """Check that get_element_coordinates retrieves the correct x and y coordinates for an element.

    The test validates:
    - The function returns the correct float values for the 'cx' and 'cy' attributes.
    """
    element_x, element_y = get_element_coordinates(svg_path, test_element)
    assert element_x == 80
    assert element_y == 100
    assert element_x is not None
    assert element_y is not None


def test_get_tranlation_from_svg() -> None:
    """Check that translation values for a specific group are returned correctly.

    The test validates:
    - The function returns the correct float values for translation_x and translation_y attributes.
    """
    translation_x, translation_y = get_translation_from_svg(svg_path, group_id)
    assert translation_x == -44.07671
    assert translation_y == -36.623283
    assert translation_x is not None
    assert translation_y is not None


def test_get_room_rect_dimensions() -> None:
    """
    Check that the dimensions of a rectangle child of a room element
    is correctly returned.

    The test validates:
    - The function returns the correct dict type and values inside of the dict.
    """

    def _create_test_element() -> etree.Element:

        namespaces = {
            None: "http://www.w3.org/2000/svg",  # Default namespace
            "xlink": "http://www.w3.org/1999/xlink",
            "svg": "http://www.w3.org/2000/svg",
        }

        # Create the root <g> element with namespaces
        g = etree.Element("g", nsmap=namespaces, id="LivingRoom")

        # Create the <rect> element as a child of <g>
        etree.SubElement(
            g,
            "{http://www.w3.org/2000/svg}rect",
            style="fill:#3e3e3e;fill-opacity:0.8;stroke:none;stroke-width:1.92996;stroke-dasharray:none;stroke-opacity:1;paint-order:stroke markers fill",
            id="rect2",
            width="60.730129",
            height="111.15349",
            x="108.80873",
            y="65.198082",
            ry="0",
        )

        print(etree.tostring(g, pretty_print=True).decode())
        return g

    expected = {
        "width": "60.730129",
        "height": "111.15349",
        "x": "108.80873",
        "y": "65.198082",
    }

    test_room_element = _create_test_element()

    result = get_room_rect_dimensions(test_room_element)

    assert expected == result
