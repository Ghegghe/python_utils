from setuptools import setup, find_packages

setup(
    name="gclient",
    version="1.0",
    author="Ghegghe",
    maintainer="Ghegghe",
    description="Python client using requests",
    packages=find_packages(),
    install_requires=[
        "gcode_utils",
        "Requests",
    ],
)
