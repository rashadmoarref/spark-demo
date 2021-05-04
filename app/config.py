import os

from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="DYNACONF",
    environments=True,
    settings_files=[f"{os.path.dirname(__file__)}/settings.toml", ".secrets.toml"],
)
