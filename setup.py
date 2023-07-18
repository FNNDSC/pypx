from setuptools import setup


def readme():
    with open('README.rst') as f:
        return f.read()

setup(
        name                =   'pypx',
        version             =   '3.11.1-pre4',
        description         =   'PACS/ChRIS core tools and utils',
        long_description    =   readme(),
        python_requires     =   ">= 3.8",
        url                 =   'http://github.com/FNNDSC/pypx',
        author              =   'FNNDSC Developers',
        author_email        =   'dev@babyMRI.org',
        license             =   'MIT',
        packages            =   ['pypx'],
        install_requires=[
            'pudb',
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
            'python-chrisclient',
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
        zip_safe            =   False,
        extras_require={
            "none": [],
            "re": [
                'redis[hiredis]~=4.6',
                'px-recount==3.11.0-rc3'
            ],
        },
        )
