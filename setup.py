import os

from setuptools import find_packages, setup


setup(
    name='komtet_kassa_linux',
    version=os.environ.get('VERSION', 'undefined'),
    packages=find_packages(),
    author='Motmom',
    author_email='motmom.dev@gmail.com',
    maintainer='Guryev Konstantin',
    maintainer_email='kosmini4@gmail.com',
    install_requires=[
        'Flask==1.1.2',
        'SQLAlchemy==1.3.17',
        'alembic==1.4.2',
        'psutil==5.7.0',
        'pyudev==0.22.0',
        'raven==6.10.0',
        'requests==2.23.0',
        'itsdangerous==2.0.1'
    ],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'kklinux = komtet_kassa_linux:run',
        ]
    }
)
