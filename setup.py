from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='pypx',
      version='0.2',
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
      scripts=['bin/px-echo', 'bin/px-find', 'bin/px-listen', 'bin/px-move'],
      zip_safe=False)
