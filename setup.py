from setuptools import setup, find_packages
from pathlib import Path

# Legge il README per la descrizione lunga
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="pygeoapiingv_plugin_pygeoapi",                # Nome del pacchetto
    version="0.1.0",                # Versione iniziale
    description="Plugin INGV per pygeoapi",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Francesco Martinelli",
    author_email="francesco.martinelli@ingv.it",
    url="https://github.com/francescoingv/pygeoapi",
    packages=find_packages(include=["ingv_plugin_pygeoapi", "ingv_plugin_pygeoapi.*"]),  # include pygeoapi e sottopacchetti
    python_requires=">=3.12",         # versione minima di Python
    install_requires=[               # dipendenze richieste
        # "requests>=2.28",
        # "numpy>=1.25",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,       # include anche file non .py come dati
    zip_safe=False,
)

