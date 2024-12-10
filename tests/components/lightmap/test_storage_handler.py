"""Test Storage Handler."""

from collections.abc import AsyncGenerator
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from homeassistant.components.lightmap import const
from homeassistant.config import async_process_ha_core_config
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from tests.common import MockUser
from tests.typing import ClientSessionGenerator


@pytest.fixture
async def temp_dir(hass: HomeAssistant) -> AsyncGenerator[str]:
    """Return a temp dir."""
    with TemporaryDirectory() as tmpdirname:
        target_dir = Path(tmpdirname) / "another_subdir"
        target_dir.mkdir()
        await async_process_ha_core_config(
            hass, {"media_dirs": {"test_dir": str(target_dir)}}
        )
        assert await async_setup_component(hass, const.DOMAIN, {})

        yield str(target_dir)


async def test_upload_view(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    temp_dir: str,
    tmp_path: Path,
    hass_admin_user: MockUser,
) -> None:
    """Allow uploading media."""
    # We need a temp dir that's not under tempdir fixture
    extra_media_dir = tmp_path
    hass.config.media_dirs["another_path"] = temp_dir

    img = (Path(__file__).parent.parent / "image_upload/logo.png").read_bytes()

    def get_file(name):
        pic = io.BytesIO(img)
        pic.name = name
        return pic

    client = await hass_client()

    # Test normal upload
    res = await client.post(
        "/api/lightmap/storage_handler/upload",
        data={
            "media_content_id": "media-source://lightmap/test_dir/.",
            "file": get_file("logo.png"),
        },
    )

    assert res.status == 200
    assert (Path(temp_dir) / "logo.png").is_file()

    # Test with bad media source ID
    for bad_id in (
        # Subdir doesn't exist
        "media-source://lightmap/test_dir/some-other-dir",
        # Main dir doesn't exist
        "media-source://lightmap/test_dir2",
        # Location is invalid
        "media-source://lightmap/test_dir/..",
        # Domain != lightmap
        "media-source://nest/test_dir/.",
        # Other directory
        f"media-source://lightmap/another_path///{extra_media_dir}/",
        # Completely something else
        "http://bla",
    ):
        res = await client.post(
            "/api/lightmap/storage_handler/upload",
            data={
                "media_content_id": bad_id,
                "file": get_file("bad-source-id.png"),
            },
        )

        assert res.status == 400, bad_id
        assert not (Path(temp_dir) / "bad-source-id.png").is_file()

    # Test invalid POST data
    res = await client.post(
        "/api/lightmap/storage_handler/upload",
        data={
            "media_content_id": "media-source://lightmap/test_dir/.",
            "file": get_file("invalid-data.png"),
            "incorrect": "format",
        },
    )

    assert res.status == 400
    assert not (Path(temp_dir) / "invalid-data.png").is_file()

    # Test invalid content type
    text_file = io.BytesIO(b"Hello world")
    text_file.name = "hello.txt"
    res = await client.post(
        "/api/lightmap/storage_handler/upload",
        data={
            "media_content_id": "media-source://lightmap/test_dir/.",
            "file": text_file,
        },
    )

    assert res.status == 400
    assert not (Path(temp_dir) / "hello.txt").is_file()

    # Test invalid filename
    with patch(
        "aiohttp.formdata.guess_filename", return_value="../invalid-filename.png"
    ):
        res = await client.post(
            "/api/lightmap/storage_handler/upload",
            data={
                "media_content_id": "media-source://lightmap/test_dir/.",
                "file": get_file("../invalid-filename.png"),
            },
        )

    assert res.status == 400
    assert not (Path(temp_dir) / "../invalid-filename.png").is_file()

    # Remove admin access
    hass_admin_user.groups = []
    res = await client.post(
        "/api/lightmap/storage_handler/upload",
        data={
            "media_content_id": "media-source://lightmap/test_dir/.",
            "file": get_file("no-admin-test.png"),
        },
    )

    assert res.status == 401
    assert not (Path(temp_dir) / "no-admin-test.png").is_file()
