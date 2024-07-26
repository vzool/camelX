from setuptools import find_packages, setup
from io import open


setup(
    name='camelx',
    version='0.0.1',
    description="Python serialization for adults",
    long_description=open('README.txt', encoding='utf8').read(),
    url="https://github.com/vzool/camelx",
    author="vzool (Abdelaziz Elrashed)",
    author_email="aeemh.sdn@gmail.com",
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    packages=find_packages(),
    install_requires=['pyyaml'],
    tests_require=['pytest'],
)
