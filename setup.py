from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='ptk',
      version='0.1',
      description='Pacs ToolKit based on DCMTK',
      long_description=readme(),
      url='http://github.com/fnndsc/ptk',
      author='FNNDSC Developpers',
      author_email='dev@babymri.com',
      license='MIT',
      packages=['ptk'],
      install_requires=[
          'pydicom',
      ],
      scripts=['bin/ptk-echo', 'bin/ptk-find', 'bin/ptk-listen'],
      zip_safe=False)
