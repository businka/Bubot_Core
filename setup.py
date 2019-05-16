from setuptools import setup, find_packages, find_namespace_packages
from src.bubot.devices import Device as Device

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='bubot_Core',
    version=Device.__version__,
    author="Razgovorov Mikhail",
    author_email="1338833@gmail.com",
    description="iot framework based on OCF specification",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/businka/bubot_Core",
    package_dir={'': 'src'},
    package_data={
        '': ['*.md', '*.json'],
    },
    packages=find_namespace_packages(where='src'),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
		"Framework :: AsyncIO"
    ],
    python_requires='>=3.5.3',
    zip_safe=False,
    install_requires=[
        'cbor2'
    ]
)
