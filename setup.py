import os
import re

from setuptools import find_packages, setup

with open('requirements.txt') as file:
    required = file.read().splitlines()

version = 'undefined'
if os.path.isfile('CHANGELOG.rst'):
    with open('CHANGELOG.rst', 'r', encoding="utf8") as file:
        for line in file:
            ver = re.match(r'^[0-9]+\.[0-9]+\.[0-9]', line)
            version = ver and ver.group(0)
            if version:
                break

setup(
    name='komtet_kassa_linux',
    version=version,
    packages=find_packages(),
    author='Motmom',
    author_email='motmom.dev@gmail.com',
    maintainer='Guryev Konstantin',
    maintainer_email='kosmini4@gmail.com',
    install_requires=required,
    include_package_data=True,
    zip_safe=False,
    data_files=[('requirements', ['requirements.txt', 'CHANGELOG.rst'])],
    entry_points={
        'console_scripts': [
            'kklinux = komtet_kassa_linux:run',
        ]
    }
)
