# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

setup(
    name="multiscope",
    version="0.8.0",
    description="MultiScope is an open-source tool for Linux that enables the creation and management of gamescope sessions of steam, allowing several players to play simultaneously on a single computer",
    author="Mallor",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=2.0.0",
        "PyGObject>=3.42.0",
    ],
    entry_points={
        "gui_scripts": [
            "multiscope=multiscope:main",
        ]
    },
)
