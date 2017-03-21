import sys
# Make sure we are running python3.5+
if 10 * sys.version_info[0]  + sys.version_info[1] < 35:
    sys.exit("Sorry, only Python 3.5+ is supported.")

from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='pypx',
      version='0.8',
      description='Wrapper around DCMTK for PACS related actions (echo, find, move and listen)',
      long_description=readme(),
      url='http://github.com/fnndsc/pypx',
      author='FNNDSC Developpers',
      author_email='dev@babymri.com',
      license='MIT',
      packages=['pypx'],
      install_requires=[
          'pydicom',
      ],
      test_suite='nose.collector',
      tests_require=['nose'],
      scripts=['bin/px-echo', 'bin/px-find', 'bin/px-listen', 'bin/px-move'],
      zip_safe=False)
