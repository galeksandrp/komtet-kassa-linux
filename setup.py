import os

from setuptools import find_packages, setup

with open('requirements.txt') as file:
    required = file.read().splitlines()

setup(
    name='komtet_kassa_linux',
    version='5.0.2',
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
