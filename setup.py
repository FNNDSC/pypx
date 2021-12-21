import sys
# Make sure we are running python3.5+
if 10 * sys.version_info[0]  + sys.version_info[1] < 35:
    sys.exit("Sorry, only Python 3.5+ is supported.")

from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

setup(
        name                =   'pypx',
        version             =   '3.4.10',
        description         =   'PACS/ChRIS core tools and utils',
        long_description    =   readme(),
        url                 =   'http://github.com/fnndsc/pypx',
        author              =   'FNNDSC Developers',
        author_email        =   'dev@babymri.com',
        license             =   'MIT',
        packages            =   ['pypx'],
        install_requires=[
            'terminaltables',
            'py-dateutil',
            'pydicom',
            'pfmisc',
            'dask',
            'retry',
            'psutil',
            'python-swiftclient',
            'pfstate',
            'webob',
            'python-chrisclient'
        ],
        test_suite          =   'nose.collector',
        tests_require       =   ['nose'],
        scripts             =   [
            'storescp.sh',
            'bin/pfstorage',
            'bin/px-do',
            'bin/px-echo',
            'bin/px-find',
            'bin/px-listen',
            'bin/px-move',
            'bin/px-push',
            'bin/px-register',
            'bin/px-repack',
            'bin/px-report',
            'bin/px-smdb',
            'bin/px-status'
        ],
        zip_safe            =   False
        )
