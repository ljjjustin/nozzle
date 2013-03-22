import sys
from setuptools import setup, find_packages


requirements = ['pyzmq']

if sys.version_info < (2, 6):
    requirements.append('simplejson')
if sys.version_info < (2, 7):
    requirements.append('argparse')

setup(
    name="nozzle",
    version="2.0",
    description="OpenStack Load Balancer Server",
    long_description="OpenStack Load Balancer Server",
    url='https://github.com/ljjjustin/nozzle',
    license='Apache',
    author='UnitedStack Corp.',
    author_email='iamljj@gmail.com',
    packages=find_packages(exclude=['bin', 'tests', 'tools']),
    classifiers=[
        'Development Status :: 1 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    install_requires=requirements,
    scripts=[
        'bin/nozzle-api',
        'bin/nozzle-server',
        'bin/nozzle-worker',
    ],
    entry_points={
        'console_scripts': [
            'nozzle = nozzle.client.shell:main',
        ]
    },
)
