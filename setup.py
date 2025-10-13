# -*- coding: utf-8 -*-

"""
This setup.py script is used to package and distribute the Proton-Coop
application. It defines metadata, dependencies, and entry points needed for
installation via pip and other package managers.
"""

from setuptools import find_packages, setup

setup(
    name="proton-coop",
    version="2.0.0",
    description="A tool to launch multiple instances of games using Proton, with features like device isolation and splitscreen.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Mallor",
    author_email="",
    url="https://github.com/Mallor705/Proton-Coop",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "psutil>=5.9.0",
        "pydantic>=2.0.0",
        "PyGObject>=3.42.0",
    ],
    entry_points={
        "console_scripts": [
            "protoncoop=protoncoop:main",
        ],
        "gui_scripts": [
            "protoncoop-gui=protoncoop:main",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Games/Entertainment",
    ],
    keywords="gaming linux proton steam coop local-multiplayer",
)
