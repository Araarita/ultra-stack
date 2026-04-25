from functools import lru_cache
from pydantic_settings import BaseSettings


class ProposalConfig(BaseSettings):
    generation_interval_minutes: int = 30
    max_pending: int = 5
    min_impact: str = "medium"
    auto_approve_safe: bool = False
    quiet_hours_start: int = 23
    quiet_hours_end: int = 7
    timezone: str = "America/Mexico_City"
    telegram_notifications: bool = True
    push_notifications: bool = True

    class Config:
        env_prefix = "PROPOSAL_"
        env_file = "/opt/ultra/.env"
        extra = "ignore"


@lru_cache(maxsize=1)
def get_config() -> ProposalConfig:
    return ProposalConfig()