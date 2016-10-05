from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='pypx',
      version='0.1',
      description='Pacs ToolKit based on DCMTK',
      long_description=readme(),
      url='http://github.com/fnndsc/pypx',
      author='FNNDSC Developpers',
      author_email='dev@babymri.com',
      license='MIT',
      packages=['pypx'],
      install_requires=[
          'pydicom',
      ],
      scripts=['bin/px-echo', 'bin/px-find', 'bin/px-listen'],
      zip_safe=False)
