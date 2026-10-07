from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    bot_token: str = "8787639647:AAF8e01VFcO0J7eoVsfl-Qjomf8jOmlLv_4"
    owner_id: int = 8241795603

settings = Settings()
