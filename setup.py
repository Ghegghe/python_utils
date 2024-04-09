from setuptools import setup, find_packages

setup(
    name="gcode_utils",
    version="1.1.1",
    author="Ghegghe",
    maintainer="Ghegghe",
    description="Ghegghe's Python coding utils",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
    ],
)
