"""Unit tests for CarouselBuilder — verifies slide creation without real AI images."""

import pytest
from pathlib import Path
from PIL import Image

from src.canvas_builder import CarouselBuilder

_SLIDES = ["Hook que engancha al lector", "Contenido del slide dos", "Contenido del slide tres"]
_CTA = "Síguenos para más contenido exclusivo"
_TITULO = "3 Secretos del Hacker Anónimo"


def _make_dummy_image(path: Path, size: tuple = (1080, 1080)) -> Path:
    img = Image.new("RGB", size, color=(30, 30, 60))
    img.save(path, "PNG")
    return path


class TestCarouselBuilder:
    def test_build_carousel_returns_correct_count(self, tmp_path):
        builder = CarouselBuilder(output_dir=str(tmp_path))
        raw_dir = tmp_path / "day_01" / "raw"
        raw_dir.mkdir(parents=True)

        raw_images = [_make_dummy_image(raw_dir / f"slide_{i:02d}.png") for i in range(1, 4)]
        slides = _SLIDES[:3]

        paths = builder.build_carousel(
            day=1, titulo=_TITULO, slides=slides, raw_images=raw_images, cta=_CTA
        )

        # cover + (len(slides)-1 content) + CTA = 1 + 2 + 1 = 4
        assert len(paths) == 4

    def test_all_output_files_exist(self, tmp_path):
        builder = CarouselBuilder(output_dir=str(tmp_path))
        raw_dir = tmp_path / "day_02" / "raw"
        raw_dir.mkdir(parents=True)

        raw_images = [_make_dummy_image(raw_dir / f"slide_{i:02d}.png") for i in range(1, 4)]

        paths = builder.build_carousel(
            day=2, titulo=_TITULO, slides=_SLIDES, raw_images=raw_images, cta=_CTA
        )

        for path in paths:
            assert path.exists(), f"Missing slide: {path}"

    def test_output_images_are_rgb_png(self, tmp_path):
        builder = CarouselBuilder(output_dir=str(tmp_path))
        raw_dir = tmp_path / "day_03" / "raw"
        raw_dir.mkdir(parents=True)

        raw_images = [_make_dummy_image(raw_dir / "slide_01.png")]

        paths = builder.build_carousel(
            day=3, titulo="Test", slides=["Single slide"], raw_images=raw_images, cta="CTA"
        )

        for path in paths:
            img = Image.open(path)
            assert img.mode == "RGB", f"Expected RGB, got {img.mode}"
            assert img.format == "PNG"

    def test_output_images_have_correct_size(self, tmp_path):
        builder = CarouselBuilder(output_dir=str(tmp_path))
        raw_dir = tmp_path / "day_04" / "raw"
        raw_dir.mkdir(parents=True)

        raw_images = [_make_dummy_image(raw_dir / "slide_01.png")]

        paths = builder.build_carousel(
            day=4, titulo="T", slides=["S"], raw_images=raw_images, cta="C"
        )

        for path in paths:
            img = Image.open(path)
            assert img.size == (1080, 1080), f"Unexpected size: {img.size}"

    def test_build_works_without_raw_images(self, tmp_path):
        builder = CarouselBuilder(output_dir=str(tmp_path))
        # No raw images provided — should fall back to solid background
        paths = builder.build_carousel(
            day=5, titulo="T", slides=["S"], raw_images=[], cta="C"
        )
        # Should still produce slides (cover + CTA at minimum)
        assert len(paths) >= 1

    def test_final_dir_is_created(self, tmp_path):
        builder = CarouselBuilder(output_dir=str(tmp_path))
        builder.build_carousel(
            day=6, titulo="T", slides=["S"], raw_images=[], cta="C"
        )
        assert (tmp_path / "day_06" / "final").exists()

    def test_cover_slide_named_correctly(self, tmp_path):
        builder = CarouselBuilder(output_dir=str(tmp_path))
        paths = builder.build_carousel(
            day=7, titulo="T", slides=["S"], raw_images=[], cta="C"
        )
        assert any("cover" in p.name for p in paths)

    def test_cta_slide_named_correctly(self, tmp_path):
        builder = CarouselBuilder(output_dir=str(tmp_path))
        paths = builder.build_carousel(
            day=8, titulo="T", slides=["S"], raw_images=[], cta="C"
        )
        assert any("cta" in p.name for p in paths)
