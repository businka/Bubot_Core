from setuptools import setup, find_namespace_packages
from src.BubotObj.OcfDevice.subtype.Device import __version__

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='Bubot_Core',
    version=__version__,
    author="Razgovorov Mikhail",
    author_email="1338833@gmail.com",
    description="iot framework based on OCF specification",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/businka/Bubot_Core",
    package_dir={'': 'src'},
    package_data={
        '': ['*.md', '*.json'],
    },
    packages=find_namespace_packages(where='src'),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha"
        "Framework :: AsyncIO",
        "Framework :: Bubot",
    ],
    python_requires='>=3.8',
    zip_safe=False,
    install_requires=[
        'Bubot_Helpers'
    ]
)
