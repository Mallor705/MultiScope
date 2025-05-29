from setuptools import setup, find_packages

setup(
    name="linux-coop",
    version="2.0.0",
    description="Launch multiple game instances using Proton and Gamescope",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "psutil>=5.9.0",
        "click>=8.0.0", 
        "pydantic>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "linux-coop=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
)