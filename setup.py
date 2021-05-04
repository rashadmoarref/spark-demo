from typing import List

from setuptools import setup


def parse_requirements(filename: str) -> List[str]:
    """ load requirements from a pip requirements file """
    lineiter = (line.strip() for line in open(filename))
    return [str(line) for line in lineiter if line and not line.startswith("#")]


# Essential requirements
INSTALL_REQUIRES = parse_requirements("/requirements.txt")

setup(
    name="spark_demo",
    version="v1.0.0",
    packages=["app"],
    install_requires=INSTALL_REQUIRES,
)
