import setuptools
from bubot.devices import Device as Device

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='bubot_Core',
    version=Device.__version__,
    author="Razgovorov Mikhail",
    author_email="1338833@gmail.com",
    description="iot framework based on OCF specification",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/businka/bubot_Core",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache License 2.0",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.5.3',
    install_requires=[
        'cbor2'
    ],
    include_package_data=True,
)
