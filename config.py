from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    bot_token: str
    owner_id: int

    @staticmethod
    def load():
        token = os.getenv("BOT_TOKEN")
        owner = os.getenv("ADMIN_ID")
        if not token or not owner:
            raise RuntimeError("Set BOT_TOKEN and ADMIN_ID in .env")
        return Settings(token, int(owner))

settings = Settings.load()
