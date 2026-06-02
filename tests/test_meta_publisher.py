"""Unit tests for MetaPublisher — all HTTP calls are mocked."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from src.meta_publisher import MetaPublisher


def _make_publisher() -> MetaPublisher:
    return MetaPublisher(
        access_token="fake_token_abc",
        instagram_account_id="123456789",
        imgbb_api_key="fake_imgbb_key",
    )


def _fake_image(tmp_path: Path, name: str = "slide.png") -> Path:
    from PIL import Image
    path = tmp_path / name
    Image.new("RGB", (100, 100), color=(0, 0, 0)).save(path, "PNG")
    return path


class TestPublishCarousel:
    def test_full_happy_path(self, tmp_path):
        publisher = _make_publisher()
        img = _fake_image(tmp_path)

        with patch.object(publisher, "_upload_image", return_value="https://i.ibb.co/abc.png") as mock_upload, \
             patch.object(publisher, "_create_item_container", return_value="item_id_1") as mock_item, \
             patch.object(publisher, "_create_carousel_container", return_value="carousel_id_99") as mock_carousel, \
             patch.object(publisher, "_publish_container", return_value="post_id_xyz") as mock_publish, \
             patch("src.meta_publisher.time.sleep"):
            post_id = publisher.publish_carousel([img], "caption text")

        assert post_id == "post_id_xyz"
        mock_upload.assert_called_once_with(img)
        mock_item.assert_called_once_with("https://i.ibb.co/abc.png")
        mock_carousel.assert_called_once_with(["item_id_1"], "caption text")
        mock_publish.assert_called_once_with("carousel_id_99")

    def test_raises_when_no_images(self):
        publisher = _make_publisher()
        with pytest.raises(ValueError, match="At least one image"):
            publisher.publish_carousel([], "caption")

    def test_multiple_images_create_multiple_items(self, tmp_path):
        publisher = _make_publisher()
        images = [_fake_image(tmp_path, f"slide_{i}.png") for i in range(3)]

        with patch.object(publisher, "_upload_image", side_effect=lambda p: f"https://img/{p.name}"), \
             patch.object(publisher, "_create_item_container", side_effect=lambda url: f"id_{url[-5:]}") as mock_item, \
             patch.object(publisher, "_create_carousel_container", return_value="car_id"), \
             patch.object(publisher, "_publish_container", return_value="post_id"), \
             patch("src.meta_publisher.time.sleep"):
            publisher.publish_carousel(images, "cap")
            assert mock_item.call_count == 3


class TestUploadImage:
    def test_returns_url_on_success(self, tmp_path):
        publisher = _make_publisher()
        img = _fake_image(tmp_path)

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "success": True,
            "data": {"url": "https://i.ibb.co/test.png"},
        }

        with patch.object(publisher._session, "post", return_value=mock_resp):
            url = publisher._upload_image(img)

        assert url == "https://i.ibb.co/test.png"

    def test_raises_on_imgbb_failure(self, tmp_path):
        publisher = _make_publisher()
        img = _fake_image(tmp_path)

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"success": False, "error": {"message": "Invalid key"}}

        with patch.object(publisher._session, "post", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="imgbb rejected"):
                publisher._upload_image(img)


class TestCreateItemContainer:
    def test_returns_container_id(self):
        publisher = _make_publisher()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"id": "media_container_001"}

        with patch.object(publisher._session, "post", return_value=mock_resp):
            result = publisher._create_item_container("https://img/photo.png")

        assert result == "media_container_001"

    def test_raises_when_id_missing(self):
        publisher = _make_publisher()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"error": {"message": "Invalid token"}}

        with patch.object(publisher._session, "post", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="container ID"):
                publisher._create_item_container("https://img/photo.png")


class TestPublishContainer:
    def test_returns_post_id(self):
        publisher = _make_publisher()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"id": "live_post_999"}

        with patch.object(publisher._session, "post", return_value=mock_resp):
            result = publisher._publish_container("carousel_abc")

        assert result == "live_post_999"

    def test_raises_on_http_error(self):
        import requests as req
        publisher = _make_publisher()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.HTTPError("403 Forbidden")
        mock_resp.status_code = 403
        mock_resp.text = '{"error": {"message": "Invalid OAuth access token"}}'

        with patch.object(publisher._session, "post", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="Meta API error"):
                publisher._publish_container("bad_container")
