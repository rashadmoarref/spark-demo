import pytest
from pyspark.sql import SparkSession

from app.config import settings


@pytest.fixture(scope="session", autouse=True)
def set_test_settings():
    settings.configure(FORCE_ENV_FOR_DYNACONF="testing")


@pytest.fixture(scope="session")
def spark():
    yield SparkSession.builder.master("local").getOrCreate()
