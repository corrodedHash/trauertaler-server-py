from dataclasses import dataclass
from typing import Generator


@dataclass
class Config:
    secret_key: str
    admin_pass: str
    algorithm: str
    access_token_exprire_minutes: int


config = Config(
    secret_key="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7",
    admin_pass="TraitorStrobeCleftBaffleArrest",
    algorithm="hs256",
    access_token_exprire_minutes=30,
)


def get_config() -> Generator[Config, None, None]:
    yield config
