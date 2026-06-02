"""Network Faceless Auto-Post — main orchestrator.

Execution flow:
  1. Load settings from environment (via .env).
  2. Calculate which day (1–30) of the content plan today falls on.
  3. Read that day's row from the Google Sheets planogram.
  4. Skip if already marked as published.
  5. Generate slide images with Pollinations.ai (free AI).
  6. Compose the carousel with Pillow (cover + content + CTA).
  7. Publish to Instagram via the Meta Graph API.
  8. Mark the row as published in the spreadsheet.

Usage:
  python main.py [--day N] [--dry-run]

  --day N      Override the auto-calculated day (useful for testing specific days).
  --dry-run    Execute everything except the actual Meta API publish call.
"""

import argparse
import logging
import sys
from datetime import date, datetime

from config.settings import Settings
from src.canvas_builder import CarouselBuilder
from src.image_generator import ImageGenerator
from src.meta_publisher import MetaPublisher
from src.sheets_manager import SheetsManager


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def _resolve_day(plan_start_date: str) -> int:
    """Return the current day number (1–30) relative to the plan start date."""
    start = datetime.strptime(plan_start_date, "%Y-%m-%d").date()
    delta = (date.today() - start).days + 1
    if not 1 <= delta <= 30:
        raise ValueError(
            f"Today is day {delta} relative to the plan start ({plan_start_date}). "
            "Only days 1–30 are valid. Update PLAN_START_DATE in your .env file."
        )
    return delta


def _build_caption(titulo: str, slides: list[str], cta: str) -> str:
    """Assemble the Instagram post caption from planogram content."""
    parts = [titulo, ""]
    parts.extend(slides[:3])          # Include first 3 slides in the caption text
    parts.extend(["", cta])
    return "\n".join(parts)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Network Faceless Auto-Post")
    parser.add_argument("--day", type=int, default=None, help="Override day number (1–30)")
    parser.add_argument("--dry-run", action="store_true", help="Skip the Meta API publish step")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    settings = Settings.load()
    _configure_logging(settings.log_level)
    log = logging.getLogger("main")

    # ── Step 1: Determine day ─────────────────────────────────────────────────
    try:
        day = args.day if args.day is not None else _resolve_day(settings.plan_start_date)
    except ValueError as exc:
        log.error("%s", exc)
        return 1

    log.info("=== Network Faceless Auto-Post | Day %d/30 ===", day)

    # ── Step 2: Read planogram ────────────────────────────────────────────────
    sheets = SheetsManager(
        credentials_path=settings.google_credentials_path,
        spreadsheet_id=settings.sheets_id,
        tab_name=settings.sheets_tab_name,
    )

    try:
        content = sheets.get_day_content(day)
    except RuntimeError as exc:
        log.error("Sheets error: %s", exc)
        return 1

    if content is None:
        log.error("No content found for day %d in sheet '%s'", day, settings.sheets_tab_name)
        return 1

    if content["published"]:
        log.info("Day %d ('%s') is already published — nothing to do.", day, content["titulo"])
        return 0

    log.info("Content ready: '%s' (%d slides)", content["titulo"], len(content["slides"]))

    # ── Step 3: Generate AI images ────────────────────────────────────────────
    generator = ImageGenerator(
        output_dir=settings.output_dir,
        width=settings.image_width,
        height=settings.image_height,
        seed=settings.character_seed,
    )

    try:
        raw_images = generator.generate_slide_images(day, content["slides"])
    except RuntimeError as exc:
        log.error("Image generation failed: %s", exc)
        return 1

    log.info("Generated %d raw images", len(raw_images))

    # ── Step 4: Compose carousel ──────────────────────────────────────────────
    builder = CarouselBuilder(output_dir=settings.output_dir)
    final_images = builder.build_carousel(
        day=day,
        titulo=content["titulo"],
        slides=content["slides"],
        raw_images=raw_images,
        cta=content["cta"],
    )

    log.info("Composed %d carousel slides", len(final_images))
    for path in final_images:
        log.debug("  → %s", path)

    # ── Step 5: Publish (or dry-run) ──────────────────────────────────────────
    if args.dry_run:
        log.info("[DRY RUN] Skipping Meta API publish. Final images are at:")
        for path in final_images:
            log.info("  %s", path)
        return 0

    publisher = MetaPublisher(
        access_token=settings.meta_access_token,
        instagram_account_id=settings.instagram_account_id,
        imgbb_api_key=settings.imgbb_api_key,
    )

    caption = _build_caption(content["titulo"], content["slides"], content["cta"])

    try:
        post_id = publisher.publish_carousel(final_images, caption)
    except RuntimeError as exc:
        log.error("Publish failed: %s", exc)
        return 1

    log.info("Carousel live — post ID: %s", post_id)

    # ── Step 6: Update spreadsheet ────────────────────────────────────────────
    try:
        sheets.mark_as_published(content["sheet_row"])
    except RuntimeError as exc:
        log.error("Published but failed to update Sheets: %s", exc)
        # Don't return 1 — the post IS live; warn and exit cleanly
        log.warning("Update the Estado column for day %d manually to avoid re-posting.", day)

    log.info("=== Done — day %d published successfully ===", day)
    return 0


if __name__ == "__main__":
    sys.exit(main())
