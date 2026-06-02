"""Unit tests for ImageGenerator — HTTP calls are mocked."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from src.image_generator import ImageGenerator, _MAX_RETRIES


def _make_generator(tmp_path: Path) -> ImageGenerator:
    return ImageGenerator(output_dir=str(tmp_path), width=512, height=512, seed=42)


class TestGenerateSlideImages:
    def test_creates_output_files(self, tmp_path):
        generator = _make_generator(tmp_path)
        slides = ["Slide one text", "Slide two text"]

        with patch.object(generator, "_download_image") as mock_dl:
            paths = generator.generate_slide_images(day=1, slides=slides)

        assert len(paths) == 2
        assert all(isinstance(p, Path) for p in paths)
        assert mock_dl.call_count == 2

    def test_raw_directory_created(self, tmp_path):
        generator = _make_generator(tmp_path)
        with patch.object(generator, "_download_image"):
            generator.generate_slide_images(day=3, slides=["text"])

        raw_dir = tmp_path / "day_03" / "raw"
        assert raw_dir.exists()

    def test_seed_varies_per_slide(self, tmp_path):
        generator = _make_generator(tmp_path)
        captured_seeds = []

        def fake_download(prompt, dest, seed):
            captured_seeds.append(seed)

        with patch.object(generator, "_download_image", side_effect=fake_download):
            generator.generate_slide_images(day=1, slides=["a", "b", "c"])

        # Each slide should get a unique seed
        assert len(set(captured_seeds)) == 3

    def test_sleeps_between_slides(self, tmp_path):
        generator = _make_generator(tmp_path)
        with patch.object(generator, "_download_image"), \
             patch("src.image_generator.time.sleep") as mock_sleep:
            generator.generate_slide_images(day=1, slides=["a", "b", "c"])

        # Should sleep between slides but not after the last one
        assert mock_sleep.call_count == 2


class TestDownloadImage:
    def test_saves_image_on_success(self, tmp_path):
        generator = _make_generator(tmp_path)
        dest = tmp_path / "test.png"
        fake_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # minimal PNG-like bytes

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.headers = {"content-type": "image/png"}
        mock_resp.iter_content.return_value = [fake_content]

        with patch.object(generator._session, "get", return_value=mock_resp):
            generator._download_image("test prompt", dest, seed=1)

        assert dest.exists()
        assert dest.read_bytes() == fake_content

    def test_retries_on_failure_then_raises(self, tmp_path):
        import requests as req
        generator = _make_generator(tmp_path)
        dest = tmp_path / "test.png"

        with patch.object(generator._session, "get", side_effect=req.ConnectionError("timeout")), \
             patch("src.image_generator.time.sleep"):
            with pytest.raises(RuntimeError, match="Image generation failed"):
                generator._download_image("prompt", dest, seed=1)

    def test_raises_on_wrong_content_type(self, tmp_path):
        generator = _make_generator(tmp_path)
        dest = tmp_path / "test.png"

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.headers = {"content-type": "text/html"}

        with patch.object(generator._session, "get", return_value=mock_resp), \
             patch("src.image_generator.time.sleep"):
            with pytest.raises(RuntimeError):
                generator._download_image("prompt", dest, seed=1)

    def test_url_contains_prompt_and_params(self, tmp_path):
        generator = _make_generator(tmp_path)
        captured_urls = []

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.headers = {"content-type": "image/png"}
        mock_resp.iter_content.return_value = [b"data"]

        def fake_get(url, **kwargs):
            captured_urls.append(url)
            return mock_resp

        dest = tmp_path / "out.png"
        with patch.object(generator._session, "get", side_effect=fake_get):
            generator._download_image("hacker avatar", dest, seed=99)

        url = captured_urls[0]
        assert "hacker" in url
        assert "width=512" in url
        assert "seed=99" in url
        assert "nologo=true" in url
