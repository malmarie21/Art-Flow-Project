from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(slots=True)
class Config:
    bot_token: str
    db_path: str
    lumi_image_id: str | None


def load_config() -> Config:
    load_dotenv()
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ValueError("BOT_TOKEN is not set in .env")

    db_path = os.getenv("DB_PATH", "bot.sqlite3").strip() or "bot.sqlite3"
    lumi_image_id = os.getenv("LUMI_IMAGE_ID", "").strip() or None
    return Config(
        bot_token=bot_token,
        db_path=db_path,
        lumi_image_id=lumi_image_id,
    )
