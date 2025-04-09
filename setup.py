# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import os
import re

import setuptools


PACKAGE_NAME = "azureml-inference-server-http"
PACKAGE_DIR = PACKAGE_NAME.replace("-", "_")
VERSION_FILENAME = "_version.py"


def get_version():
    with open(os.path.join(PACKAGE_DIR, VERSION_FILENAME)) as fp:
        data = fp.read()

    m = re.search(r'__version__ = "([^"]+)"', data)
    if not m:
        raise RuntimeError(f"Failed to extract version from {VERSION_FILENAME}. Content:\n{data}")

    return m.group(1)


def get_long_description():
    with open("changes/README.rst", encoding="utf-8") as fp:
        readme = fp.read()

    with open("CHANGELOG.rst", encoding="utf-8") as fp:
        changelog = fp.read()

    return readme + changelog


def get_license():
    with open(".inlinelicense", "r", encoding="utf-8") as fp:
        return fp.read()


setuptools.setup(
    name=PACKAGE_NAME,
    version=get_version(),
    license=get_license(),
    author="Microsoft Corp",
    author_email="amlInferenceImages@microsoft.com",
    description="Azure Machine Learning inferencing server.",
    long_description=get_long_description(),
    long_description_content_type="text/x-rst",
    packages=setuptools.find_packages(exclude=["tests"]),
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: Other/Proprietary License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.9",
    install_requires=[
        "flask~=3.0.0",
        "flask-cors~=5.0.0",
        'gunicorn>=23.0.0; platform_system!="Windows"',
        "inference-schema~=1.8.0",
        "opentelemetry-sdk",
        "opentelemetry-exporter-otlp",
        "opentelemetry-instrumentation-logging",
        "opentelemetry-instrumentation-flask",
        "azure-monitor-opentelemetry-exporter",
        'psutil<6.0.0; platform_system=="Windows"',
        "pydantic~=2.9.0",
        "pydantic-settings",
        'waitress>=3.0.1; platform_system=="Windows"',
        "werkzeug>=3.0.3",  # Werkzeug 3.x breaks back-compatibility of urls package
        "certifi>=2024.7.4",  # Python (Pip) Security Update for certifi (GHSA-248v-346w-9cwc)
    ],
    extras_require={
        "dev": [
            "azure-monitor-query",
            "black",
            "coverage",
            "debugpy",
            "flake8",
            "flake8-comprehensions",
            "flake8-import-order",
            "junitparser==2.0.0",
            "numpy",
            "pandas",
            "pre-commit",
            "pytest",
            "pytest-asyncio",
            "pytest-benchmark",
            "pytest-cov",
            "requests",
            "towncrier==21.9.0",
            "wheel",
        ]
    },
    entry_points={"console_scripts": [f"azmlinfsrv={PACKAGE_DIR}.amlserver:run"]},
    include_package_data=True,
)
