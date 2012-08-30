import sys
from setuptools import setup, find_packages


requirements = ['pyzmq']

if sys.version_info < (2, 6):
    requirements.append('simplejson')
if sys.version_info < (2, 7):
    requirements.append('argparse')

setup(
    name = "nozzle",
    version = "0.1",
    description = "OpenStack Load Balancer Server",
    long_description = "OpenStack Load Balancer Server",
    url = 'https://github.com/ljjjustin/nozzle',
    license = 'Apache',
    author = 'Sina Corp.',
    author_email = 'iamljj@gmail.com',
    packages = find_packages(exclude=['bin', 'tests', 'tools']),
    classifiers = [
        'Development Status :: 1 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    install_requires = requirements,
    scripts = [
        'bin/nozzle-api',
        'bin/nozzle-client',
    ],
)
