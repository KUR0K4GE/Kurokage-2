"""Carousel slide compositor using Pillow.

Builds three types of slides:
  • Cover   — character image + title + hook subtitle
  • Content — darkened character image + card overlay + slide text
  • CTA     — solid dark background + call-to-action + follow prompt

All slides are 1080×1080 px (or the configured size) in RGB PNG format.

Font resolution order:
  1. assets/fonts/ (place Inter-Bold.ttf or Roboto-Bold.ttf here)
  2. Common system paths (DejaVu, Liberation, Helvetica)
  3. PIL built-in bitmap font as last resort (fixed size, no scaling)
"""

import logging
import textwrap
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter

log = logging.getLogger(__name__)

# ── Brand palette ──────────────────────────────────────────────────────────────
_BG = (10, 10, 15)
_ACCENT = (0, 212, 255)        # Electric cyan
_WHITE = (255, 255, 255)
_GRAY = (176, 176, 192)
_CARD_BG = (10, 10, 15, 215)   # Semi-transparent dark card

_SIZE = (1080, 1080)
_W, _H = _SIZE

# ── Font search paths ──────────────────────────────────────────────────────────
_FONT_CANDIDATES = [
    Path("assets/fonts/Inter-Bold.ttf"),
    Path("assets/fonts/Roboto-Bold.ttf"),
    Path("assets/fonts/DejaVuSans-Bold.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Windows/Fonts/arialbd.ttf",
]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(str(candidate), size)
        except (OSError, IOError):
            continue
    log.warning("No TTF font found — using PIL default. Install a font in assets/fonts/ for better results.")
    return ImageFont.load_default()


def _text(draw: ImageDraw.ImageDraw, xy: tuple, msg: str, font, fill: tuple, anchor: str = "la") -> None:
    """Draw text with graceful fallback if the font doesn't support 'anchor'."""
    try:
        draw.text(xy, msg, font=font, fill=fill, anchor=anchor)
    except TypeError:
        draw.text(xy, msg, font=font, fill=fill)


def _gradient_overlay(draw: ImageDraw.ImageDraw, start_y: int, end_y: int, max_alpha: int = 220) -> None:
    """Draw a vertical gradient darkening strip from start_y to end_y."""
    span = max(end_y - start_y, 1)
    for y in range(start_y, end_y):
        alpha = int(max_alpha * (y - start_y) / span)
        draw.rectangle([(0, y), (_W, y + 1)], fill=(*_BG, min(alpha, max_alpha)))


class CarouselBuilder:
    def __init__(self, output_dir: str):
        self._root = Path(output_dir)

    # ── public API ─────────────────────────────────────────────────────────────

    def build_carousel(
        self,
        day: int,
        titulo: str,
        slides: list[str],
        raw_images: list[Path],
        cta: str,
    ) -> list[Path]:
        """Compose the full carousel and return paths to the finished slides.

        Slide order:
          slide_01_cover.png  — cover with title
          slide_02.png …      — one per content slide
          slide_NN_cta.png    — call-to-action finale
        """
        final_dir = self._root / f"day_{day:02d}" / "final"
        final_dir.mkdir(parents=True, exist_ok=True)

        output: list[Path] = []
        total_content = len(slides)
        total_slides = total_content + 1  # +1 for the CTA

        # Cover slide
        cover_img = raw_images[0] if raw_images else None
        cover_path = final_dir / "slide_01_cover.png"
        self._build_cover(titulo, slides[0] if slides else "", cover_img, cover_path)
        output.append(cover_path)

        # Content slides (slides[1:] paired with raw_images[1:])
        for idx, (slide_text, raw_img) in enumerate(zip(slides[1:], raw_images[1:]), start=2):
            path = final_dir / f"slide_{idx:02d}.png"
            self._build_content(slide_text, raw_img, idx, total_slides, path)
            output.append(path)

        # CTA slide
        cta_num = len(output) + 1
        cta_path = final_dir / f"slide_{cta_num:02d}_cta.png"
        self._build_cta(cta, cta_path)
        output.append(cta_path)

        log.info("Built %d carousel slides in %s", len(output), final_dir)
        return output

    # ── slide builders ─────────────────────────────────────────────────────────

    def _build_cover(
        self, titulo: str, hook: str, raw_img: Optional[Path], dest: Path
    ) -> None:
        base = self._load_bg(raw_img)
        overlay = Image.new("RGBA", _SIZE, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Dark gradient on the bottom half so text is readable
        _gradient_overlay(draw, _H // 3, _H, max_alpha=230)

        # Top accent bar
        draw.rectangle([(0, 0), (_W, 7)], fill=(*_ACCENT, 255))

        # Slide indicator top-right
        _text(draw, (_W - 55, 22), "01", _font(26), (*_ACCENT, 200), anchor="mm")

        # Title
        font_title = _font(56)
        y = _H - 240
        for line in textwrap.wrap(titulo, width=22)[:3]:
            _text(draw, (64, y), line, font_title, (*_WHITE, 255))
            y += 68

        # Hook subtitle
        font_hook = _font(33)
        for line in textwrap.wrap(hook, width=38)[:2]:
            _text(draw, (64, y + 8), line, font_hook, (*_GRAY, 225))
            y += 44

        # Bottom accent bar
        draw.rectangle([(0, _H - 7), (_W, _H)], fill=(*_ACCENT, 255))

        _composite_save(base, overlay, dest)
        log.debug("Cover saved to %s", dest)

    def _build_content(
        self,
        text: str,
        raw_img: Optional[Path],
        slide_num: int,
        total: int,
        dest: Path,
    ) -> None:
        base = self._load_bg(raw_img)
        # Darken base significantly so text card pops
        base = base.point(lambda p: int(p * 0.40))

        overlay = Image.new("RGBA", _SIZE, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Top accent bar
        draw.rectangle([(0, 0), (_W, 7)], fill=(*_ACCENT, 255))

        # Slide counter top-right
        counter = f"{slide_num:02d} / {total:02d}"
        _text(draw, (_W - 70, 28), counter, _font(24), (*_ACCENT, 220))

        # Content card
        cx, cy, cw, ch = 60, 260, _W - 120, 560
        draw.rounded_rectangle(
            [(cx, cy), (cx + cw, cy + ch)],
            radius=24,
            fill=_CARD_BG,
        )
        # Accent left stripe
        draw.rectangle([(cx, cy + 18), (cx + 6, cy + ch - 18)], fill=(*_ACCENT, 255))

        # Card text
        font_body = _font(40)
        ty = cy + 42
        for line in textwrap.wrap(text, width=30)[:8]:
            _text(draw, (cx + 34, ty), line, font_body, (*_WHITE, 255))
            ty += 58

        # Bottom accent bar
        draw.rectangle([(0, _H - 7), (_W, _H)], fill=(*_ACCENT, 255))

        _composite_save(base, overlay, dest)
        log.debug("Content slide %d saved to %s", slide_num, dest)

    def _build_cta(self, cta_text: str, dest: Path) -> None:
        img = Image.new("RGBA", _SIZE, (*_BG, 255))
        draw = ImageDraw.Draw(img)

        # Subtle radial-ish glow in centre (concentric dark rectangles fading outward)
        for i in range(10):
            margin = i * 20
            alpha = max(0, 30 - i * 3)
            draw.rectangle(
                [(margin, margin), (_W - margin, _H - margin)],
                outline=(*_ACCENT, alpha),
                width=1,
            )

        # Top + bottom thick accent bars
        draw.rectangle([(0, 0), (_W, 9)], fill=(*_ACCENT, 255))
        draw.rectangle([(0, _H - 9), (_W, _H)], fill=(*_ACCENT, 255))

        # Decorative outer box
        draw.rounded_rectangle(
            [(70, 180), (_W - 70, _H - 180)],
            radius=28,
            outline=(*_ACCENT, 160),
            width=2,
        )

        # "¿Quieres saber más?" header
        header_font = _font(36)
        _text(draw, (_W // 2, 260), "¿Quieres saber más?", header_font, (*_ACCENT, 255), anchor="mm")

        # Main CTA text
        cta_font = _font(48)
        ty = 370
        for line in textwrap.wrap(cta_text, width=22)[:4]:
            _text(draw, (_W // 2, ty), line, cta_font, (*_WHITE, 255), anchor="mm")
            ty += 66

        # Follow prompts at the bottom of the card
        small_font = _font(30)
        _text(draw, (_W // 2, _H - 270), "Síguenos para más contenido", small_font, (*_GRAY, 210), anchor="mm")
        _text(draw, (_W // 2, _H - 220), "↓  Guarda este post  ↓", small_font, (*_ACCENT, 210), anchor="mm")

        img.convert("RGB").save(dest, "PNG", optimize=True)
        log.debug("CTA slide saved to %s", dest)

    # ── helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _load_bg(path: Optional[Path]) -> Image.Image:
        if path and path.exists():
            return Image.open(path).convert("RGBA").resize(_SIZE, Image.LANCZOS)
        # Fallback: plain brand background
        return Image.new("RGBA", _SIZE, (*_BG, 255))


def _composite_save(base: Image.Image, overlay: Image.Image, dest: Path) -> None:
    Image.alpha_composite(base, overlay).convert("RGB").save(dest, "PNG", optimize=True)
