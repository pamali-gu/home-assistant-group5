"""Test resources."""

from homeassistant.components.alexa.resources import AlexaCapabilityResource


def test_serialize_labels() -> None:
    """Test the serialize_labels function."""

    test_instance = AlexaCapabilityResource(["Alexa.Value.High"])

    # Test case with label in AlexaGlobalCatalog
    labels_known = ["Alexa.Value.High"]
    expected = {
        "friendlyNames": [{"@type": "asset", "value": {"assetId": "Alexa.Value.High"}}]
    }
    assert (
        AlexaCapabilityResource.serialize_labels(test_instance, labels_known)
        == expected
    )

    # Test case with label not in AlexaGlobalCatalog
    labels_unknown = ["Alexa.Value.Full"]
    expected = {
        "friendlyNames": [
            {"@type": "text", "value": {"text": "Alexa.Value.Full", "locale": "en-US"}}
        ]
    }
    assert (
        AlexaCapabilityResource.serialize_labels(test_instance, labels_unknown)
        == expected
    )

    # Test case with an empty list
    labels_empty = []
    expected = {"friendlyNames": []}
    assert (
        AlexaCapabilityResource.serialize_labels(test_instance, labels_empty)
        == expected
    )
