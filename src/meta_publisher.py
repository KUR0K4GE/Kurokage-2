"""Instagram carousel publisher via the Meta Graph API (free tier).

Flow:
  1. Each final image is uploaded to imgbb.com to obtain a public HTTPS URL.
     (Instagram requires publicly reachable URLs — local paths won't work.)
  2. One media container is created per image (carousel item).
  3. A CAROUSEL container is created referencing all item IDs.
  4. The carousel is published via /media_publish.

Prerequisites (all free):
  • imgbb.com account + API key (https://imgbb.com/login → API)
  • Facebook App with instagram_content_publish permission approved
  • Long-lived User Token (valid 60 days; refresh via the token debug tool)
  • Instagram Business or Creator account linked to a Facebook Page

Meta Graph API version: v19.0
"""

import base64
import logging
import time
from pathlib import Path

import requests

log = logging.getLogger(__name__)

_GRAPH = "https://graph.facebook.com/v19.0"
_IMGBB = "https://api.imgbb.com/1/upload"
_TIMEOUT = 45          # seconds
_PUBLISH_DELAY = 6     # seconds to wait between container creation and publish


class MetaPublisher:
    def __init__(
        self,
        access_token: str,
        instagram_account_id: str,
        imgbb_api_key: str,
    ):
        self._token = access_token
        self._ig_id = instagram_account_id
        self._imgbb_key = imgbb_api_key
        self._session = requests.Session()

    # ── public API ─────────────────────────────────────────────────────────────

    def publish_carousel(self, image_paths: list[Path], caption: str) -> str:
        """Upload images, assemble a carousel, publish it, and return the post ID."""
        if not image_paths:
            raise ValueError("At least one image is required to publish a carousel.")

        log.info("Uploading %d images to imgbb…", len(image_paths))
        public_urls = [self._upload_image(p) for p in image_paths]

        log.info("Creating Instagram media containers…")
        item_ids = [self._create_item_container(url) for url in public_urls]

        log.info("Creating carousel container…")
        carousel_id = self._create_carousel_container(item_ids, caption)

        log.info("Publishing carousel (waiting %ds for Meta to process containers)…", _PUBLISH_DELAY)
        time.sleep(_PUBLISH_DELAY)

        post_id = self._publish_container(carousel_id)
        log.info("Carousel published — post ID: %s", post_id)
        return post_id

    # ── image hosting ──────────────────────────────────────────────────────────

    def _upload_image(self, path: Path) -> str:
        """Upload a local PNG to imgbb.com and return its public URL."""
        with open(path, "rb") as fh:
            encoded = base64.b64encode(fh.read()).decode("utf-8")

        resp = self._session.post(
            _IMGBB,
            data={"key": self._imgbb_key, "image": encoded, "name": path.stem},
            timeout=_TIMEOUT,
        )
        self._raise_for_api_error(resp, "imgbb upload")
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(f"imgbb rejected the upload: {data}")

        url: str = data["data"]["url"]
        log.debug("Uploaded %s → %s", path.name, url)
        return url

    # ── Meta Graph API calls ───────────────────────────────────────────────────

    def _create_item_container(self, image_url: str) -> str:
        """Create a single carousel item and return its container ID."""
        resp = self._session.post(
            f"{_GRAPH}/{self._ig_id}/media",
            data={
                "image_url": image_url,
                "is_carousel_item": "true",
                "access_token": self._token,
            },
            timeout=_TIMEOUT,
        )
        self._raise_for_api_error(resp, "create item container")
        container_id: str = resp.json().get("id", "")
        if not container_id:
            raise RuntimeError(f"Meta did not return a container ID: {resp.json()}")
        return container_id

    def _create_carousel_container(self, item_ids: list[str], caption: str) -> str:
        """Create the top-level CAROUSEL container."""
        resp = self._session.post(
            f"{_GRAPH}/{self._ig_id}/media",
            data={
                "media_type": "CAROUSEL",
                "children": ",".join(item_ids),
                "caption": caption,
                "access_token": self._token,
            },
            timeout=_TIMEOUT,
        )
        self._raise_for_api_error(resp, "create carousel container")
        carousel_id: str = resp.json().get("id", "")
        if not carousel_id:
            raise RuntimeError(f"Meta did not return a carousel ID: {resp.json()}")
        return carousel_id

    def _publish_container(self, container_id: str) -> str:
        """Publish the ready container and return the live post ID."""
        resp = self._session.post(
            f"{_GRAPH}/{self._ig_id}/media_publish",
            data={
                "creation_id": container_id,
                "access_token": self._token,
            },
            timeout=_TIMEOUT,
        )
        self._raise_for_api_error(resp, "media_publish")
        post_id: str = resp.json().get("id", "")
        if not post_id:
            raise RuntimeError(f"Meta did not return a post ID: {resp.json()}")
        return post_id

    # ── error handling ─────────────────────────────────────────────────────────

    @staticmethod
    def _raise_for_api_error(resp: requests.Response, step: str) -> None:
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            body = resp.text[:500]
            raise RuntimeError(f"Meta API error at '{step}' (HTTP {resp.status_code}): {body}") from exc
