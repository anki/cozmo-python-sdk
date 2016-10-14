# Copyright (c) 2016 Anki, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''
Cozmo, by Anki.

Cozmo is a small robot with a big personality.

This library lets you take command of Cozmo and write programs for him.

Cozmo features:

    * A camera with advanced vision system
    * A robotic lifter
    * Independent tank treads
    * Pivotable head
    * An array of LEDs
    * An accelerometer
    * A gyroscope
    * Cliff detection
    * Face recognition
    * Path planning
    * Animation and behavior systems
    * Power cubes, with LEDs, an accelerometer and tap detection

This SDK provides users with access to take control of Cozmo and write simple
or advanced programs with him.

Requirements:
    * Python 3.5.1 or later

Optional requirements for camera image processing/display:
    * Tkinter (Usually supplied by default with Python)
    * Pillow
    * NumPy
'''


from setuptools import setup, find_packages
import os.path
import sys

if sys.version_info < (3,5,1):
    sys.exit('cozmo requires Python 3.5.1 or later')

here = os.path.abspath(os.path.dirname(__file__))


def fetch_version():
    with open(os.path.join(here, 'src', 'cozmo', 'version.py')) as f:
        ns = {}
        exec(f.read(), ns)
        return ns

version_data = fetch_version()
version = version_data['__version__']
cozmoclad_version = version_data['__cozmoclad_version__']

if cozmoclad_version is None:
    install_requires = ['cozmoclad']
else:
    install_requires = ['cozmoclad==' + cozmoclad_version]

setup(
    name='cozmo',
    version=version,
    description='SDK for Anki Cozmo, the small robot with the big personality',
    long_description=__doc__,
    url='https://developer.anki.com/cozmo/',
    author='Anki, Inc',
    author_email='cozmosdk@anki.com',
    license='Apache License, Version 2.0',
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.5',
    ],
    zip_safe=True,
    keywords='anki cozmo robot robotics sdk'.split(),
    package_dir={'': 'src'},
    packages=find_packages('src'),
    package_data={
        'cozmo': ['LICENSE.txt']
    },
    install_requires=install_requires,
    extras_require={
        'camera': ['Pillow>=3.3', 'numpy>=1.11'],
        'test': ['tox', 'pytest'],
    }
)
