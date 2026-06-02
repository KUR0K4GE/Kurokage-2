"""Central configuration loader — reads environment variables (via .env) and validates them."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

_REQUIRED: dict[str, str] = {
    "GOOGLE_CREDENTIALS_PATH": "path to the Google service account JSON file",
    "SHEETS_ID": "Google Spreadsheet ID (from the URL)",
    "META_ACCESS_TOKEN": "Meta long-lived access token",
    "INSTAGRAM_ACCOUNT_ID": "Instagram Business Account numeric ID",
    "IMGBB_API_KEY": "imgbb.com free API key",
    "PLAN_START_DATE": "start date for the 30-day plan (YYYY-MM-DD)",
}


@dataclass(frozen=True)
class Settings:
    google_credentials_path: str
    sheets_id: str
    sheets_tab_name: str
    plan_start_date: str
    character_seed: int
    image_width: int
    image_height: int
    imgbb_api_key: str
    meta_access_token: str
    instagram_account_id: str
    output_dir: str
    log_level: str

    @classmethod
    def load(cls) -> "Settings":
        missing = [k for k in _REQUIRED if not os.getenv(k)]
        if missing:
            lines = "\n".join(f"  {k}: {_REQUIRED[k]}" for k in missing)
            raise EnvironmentError(
                f"Missing required environment variables:\n{lines}\n"
                "Copy .env.example to .env and fill in the values."
            )

        return cls(
            google_credentials_path=os.environ["GOOGLE_CREDENTIALS_PATH"],
            sheets_id=os.environ["SHEETS_ID"],
            sheets_tab_name=os.getenv("SHEETS_TAB_NAME", "Planograma"),
            plan_start_date=os.environ["PLAN_START_DATE"],
            character_seed=int(os.getenv("CHARACTER_SEED", "1337")),
            image_width=int(os.getenv("IMAGE_WIDTH", "1080")),
            image_height=int(os.getenv("IMAGE_HEIGHT", "1080")),
            imgbb_api_key=os.environ["IMGBB_API_KEY"],
            meta_access_token=os.environ["META_ACCESS_TOKEN"],
            instagram_account_id=os.environ["INSTAGRAM_ACCOUNT_ID"],
            output_dir=os.getenv("OUTPUT_DIR", "output"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
