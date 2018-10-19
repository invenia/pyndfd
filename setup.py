from __future__ import absolute_import, division, print_function, unicode_literals

from setuptools import find_packages, setup

TEST_DEPS = ["coverage", "pytest", "pytest-cov"]
EXTRAS = {"test": TEST_DEPS}

setup(
    name="pyndfd",
    packages=find_packages(exclude=["tests"]),
    version="0.9",
    license="MIT License",
    description="Python routines for easy caching/retrieval of NWS's NDFD variables",
    author="Marty J. Sullivan",
    author_email="marty.sullivan@cornell.edu",
    url="https://github.com/marty-sullivan/pyndfd",
    download_url="https://github.com/marty-sullivan/pyndfd/archive/0.9.tar.gz",
    install_requires=["numpy", "pyproj", "pygrib", "six"],
    test_require=TEST_DEPS,
    extras_require=EXTRAS,
    keywords=[
        "noaa",
        "ndfd",
        "nws",
        "weather",
        "forecast",
        "cornell",
        "atmospheric",
        "science",
    ],
)
