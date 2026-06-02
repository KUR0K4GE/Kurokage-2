"""AI image generation using Pollinations.ai — free, public, no API key required.

Pollinations.ai wraps open-source models (Flux, Stable Diffusion) behind a simple
HTTP GET interface. Images are returned as PNG binary directly in the response body.

Rate-limit note: Pollinations imposes soft limits on burst traffic. The generator
sleeps 2 seconds between slides to stay within polite usage bounds.
"""

import logging
import time
import urllib.parse
from pathlib import Path

import requests

from config.character_prompt import build_slide_prompt

log = logging.getLogger(__name__)

_BASE_URL = "https://image.pollinations.ai/prompt"
_MODEL = "flux"          # Best free model on Pollinations as of 2025
_TIMEOUT = 90            # seconds — image generation can be slow on free tier
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 6    # seconds — doubles on each retry


class ImageGenerator:
    def __init__(
        self,
        output_dir: str,
        width: int = 1080,
        height: int = 1080,
        seed: int = 1337,
    ):
        self._output_dir = Path(output_dir)
        self._width = width
        self._height = height
        self._seed = seed
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "NetworkFacelessAutoPost/1.0"})

    # ── public API ────────────────────────────────────────────────────────────

    def generate_slide_images(self, day: int, slides: list[str]) -> list[Path]:
        """Generate one background image per slide and return their local paths.

        Images are saved to output/day_XX/raw/slide_NN.png.
        The seed offset per slide keeps each scene unique while the character
        seed anchor maintains visual consistency across the full carousel.
        """
        raw_dir = self._output_dir / f"day_{day:02d}" / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        paths: list[Path] = []
        for idx, slide_text in enumerate(slides, start=1):
            dest = raw_dir / f"slide_{idx:02d}.png"
            log.info("Generating image for slide %d/%d…", idx, len(slides))
            prompt = build_slide_prompt(slide_text, slide_index=idx)
            # Vary seed slightly per slide so scenes differ while character stays constant
            slide_seed = self._seed + (idx * 7)
            self._download_image(prompt, dest, slide_seed)
            paths.append(dest)
            if idx < len(slides):
                time.sleep(2)

        return paths

    # ── private helpers ───────────────────────────────────────────────────────

    def _build_url(self, prompt: str, seed: int) -> str:
        encoded = urllib.parse.quote(prompt, safe="")
        return (
            f"{_BASE_URL}/{encoded}"
            f"?width={self._width}"
            f"&height={self._height}"
            f"&seed={seed}"
            f"&model={_MODEL}"
            f"&nologo=true"
            f"&enhance=true"
        )

    def _download_image(self, prompt: str, dest: Path, seed: int) -> None:
        url = self._build_url(prompt, seed)
        last_error: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = self._session.get(url, timeout=_TIMEOUT, stream=True)
                resp.raise_for_status()

                content_type = resp.headers.get("content-type", "")
                if "image" not in content_type:
                    raise ValueError(f"Unexpected content-type: {content_type}")

                with open(dest, "wb") as fh:
                    for chunk in resp.iter_content(chunk_size=8192):
                        fh.write(chunk)

                log.debug("Saved image to %s", dest)
                return

            except (requests.RequestException, ValueError, OSError) as exc:
                last_error = exc
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                log.warning(
                    "Image generation attempt %d/%d failed: %s — retrying in %ds",
                    attempt, _MAX_RETRIES, exc, delay,
                )
                if attempt < _MAX_RETRIES:
                    time.sleep(delay)

        raise RuntimeError(
            f"Image generation failed after {_MAX_RETRIES} attempts. "
            f"Last error: {last_error}"
        )
