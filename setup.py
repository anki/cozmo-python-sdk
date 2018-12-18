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
The Cozmo SDK is a flexible vision-based robotics platform used in enterprise, education, and entertainment.

Cozmo’s pioneering combination of advanced robotics hardware and software are part of what make him an innovative consumer experience. But it’s also what makes him, in conjunction with the Cozmo SDK, a groundbreaking robotics platform that’s expressive, engaging, and entertaining.

We built the Cozmo SDK to be robust enough for enterprise and research, but simple enough for anyone with a bit of technical know-how to tap into our sophisticated robotics and AI technologies. Organizations and institutions using the Cozmo SDK include SAP, Oracle, Carnegie Mellon University, and Georgia Tech. Find out more at developer.anki.com

Cozmo SDK documentation: http://cozmosdk.anki.com/docs/

Official developer forum: https://forums.anki.com/

Requirements:
    * Python 3.5.1 or later
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
    url='https://developer.anki.com',
    author='Anki, Inc',
    author_email='developer@anki.com',
    license='Apache License, Version 2.0',
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
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
        'cozmo': ['LICENSE.txt', 'assets/*.obj', 'assets/*.mtl', 'assets/*.jpg',
                  'assets/LICENSE.txt']
    },
    install_requires=install_requires,
    extras_require={
        '3dviewer': ['PyOpenGL>=3.1',
                     'Pillow>=3.3', 'numpy>=1.11'],
        'camera': ['Pillow>=3.3', 'numpy>=1.11'],
        'test': ['tox', 'pytest'],
    }
)
