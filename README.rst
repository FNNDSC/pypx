####################################
pypx - 3.4.8
####################################

.. image:: https://badge.fury.io/py/pypx.svg
    :target: https://badge.fury.io/py/pypx

.. image:: https://travis-ci.org/FNNDSC/pypx.svg?branch=master
    :target: https://travis-ci.org/FNNDSC/pypx

.. image:: https://img.shields.io/badge/python-3.5%2B-blue.svg
    :target: https://badge.fury.io/py/pypx

.. contents:: Table of Contents

1. Overview
*****************

``pypx`` is a *complete* client-side PACS (Picture Archive and Communications System) Query/Retrieve/Storage solution that operates in stand-alone script mode in addition to providing a set of python modules for use in other packages. The modules/API provide a simple mechanism for a python program to interact with an appropriately configured remote PACS, while the stand alone scripts offer a convenient ability to directly Query/Retrieve/Store images from the command line.

``pypx`` was mostly developed for use in the ChRIS system as part of the ``pfdcm`` microservice; however the CLI scripts of ``pypx`` and the provided docker image offer a quick and powerful means of accessing a PACS without any additional overhead.

1.1 Complete **Client** Side
============================

This solution is **client**-side and cannot operate fully independently of an appropriately configured PACS. Unfortunately, simply downloading this repo/tools and pointing the scripts at some PACS is insufficient. The PACS itself (which is NOT part of this repo) needs to be configured to service communications and requests from these tools. See below for more information.

1.1.1 Quick PACS Primer
-----------------------

A PACS exists as a separate service on a network, and ``pypx`` communicates with a pre-configured PACS when asking for Query data and when Retrieving images. Importantly, from the client perspective, data is **PUSHED** from the PACS, and not **PULLED** from the client. This means that client software in essence "asks" the PACS for images and the PACS obliges by transmitting the images over the network to a pre-configured location.

Communications with a PACS are for the most insecure and reflected a circa 1990s view/model of internetworking. When a client communicates with a PACS, it sends along with every request string identifiers unique to the client and configured in the PACS. Typical identifiers are the ``AETitle`` and sometimes additionally the ``CalledAETitle``. The PACS examines these strings on receipt to identify/authenticate the client and also to identify a destination network ``IP:port`` to which data can be transmitted.

1.1.2 Configuring a PACS
-------------------------

In order to be fully complete, a destination PACS with which ``pypx`` modules wish to communicate needs to be configured with appropriate ``AETitle``, ``CalledAETitle``, as well as the network address IP and port of the ``pypx`` hosting machine. Configuring a PACS is obviously outside of the scope of this documentation. Consult your PACS for information on this configuration.

As a brief note, if the opensource ``orthanc`` PACS server is being used, the ``orthanc.json`` can be edited to include

.. code-block:: json

  { 
      "DicomAet" : "CHRISV3T"
  }

and 

.. code-block:: json

  {
     "CHRIS" : [ "CHRIS", "10.72.76.39", 10402 ],
     "CHRISLOCAL" : ["CHRISLOCAL", "192.168.1.189", 11113 ]
  }

where ``CHRISLOCAL`` for example defines a DICOM ``storescp`` service on the host ``192.168.1.189`` and port ``11113`` while ``CHRIS`` defines another destination ``storescp`` service .

1.1.3 Configuring ``pypx``
---------------------------

Locally, however, some configuration is required and conveniently located in the script ``PACS_QR.sh``. In the

.. code-block:: bash

    function institution_set
    {
        ...
    }

simply add another block reflecting the variables appropriate to your remote PACS service.

1.2 Components
==============

1.2.1 Environment
-----------------

``pypx`` can be thought of as a bridge connecting a PACS to a ChRIS instance. In between these services is a filesystem. A ``retrieve`` operation will request files from a PACS which arrive over the network and a separately configured listening service repacks these files in a specially configured location called the ``BASEMOUNT``. Once these files are received, they can be ``push`` -ed to special ChRIS friendly storage called swift, and once there they can be ``register`` -ed to ChRIS/CUBE. Each of these services (swift and CUBE) have network locations and login details which are stored in the ``BASEMOUNT`` in ``<BASEMOUNT>/services/[swift,cube].json``. Many different swift and CUBE configurations can in theory exist in these json files. Each configuration is identified by a key -- the ``SWIFTKEY`` for the swift service and the ``CUBEKEY`` for the CUBE service. Using these keys makes for a convenient way to push and register files without very verbose CLI.

See ``PACS_QR.sh -x`` for some in-line help on setting these keys.

1.2.2 Tools
-----------

Internally, the code wraps around DCMTK utilies as well as the PyDicom module. The following modules/scripts are provided:

- pfstorage_: Query / put files/objects into swift storage.

- px-do_: Perform various downstream utility functions once a ``px-find`` has completed.

- px-echo_: Ping the PACS to make sure it is online (``echoscu``).

- px-find_: Find (Query) a PACS in a variety of ways. The start point of almost all other workflows which are constructed as ``find`` _then_ ``do``.

- px-listen_: Deprecated listening service wrapper.

- px-move_: Move data from the PACS (``movescu``).

- px-push_: Push DICOM data to a remote node (either a PACS or a ChRIS swift object storage container).

- px-register_: A companion to ``px-push`` that registers files in ChRIS swift storage to the ChRIS CUBE backend.

- px-repack_: Read and repack DICOM files, organizing the destination in a human-friendly tree based layout.

- px-report_: Consume the JSON outputs of many of the tools (esp the ``px-find`` and generate various console-based reports).

- px-status_: Report on the status of query results in the ``BASEMOUNT``.

- px-smdb_: A simple file-system based database that provides tracking and query for processed DICOM files.

2. Installation
*****************

2.1 Prerequisites
=================

For all installation solutions, make sure that the machine receiving images from a PACS has approporate listening and repacking services and that the PACS itself has been configured to recognize this machine. While out of scope of this document, the simplest way to set this up is to use the ``pfdcm`` service (provided separately).

2.2 Using docker
================

Using the dockerized container is the recommended installation vector as the image contains all tools (dcmtk) that can interact both with a PACS as well as swift storage and CUBE without any additional software on the host system.

.. code-block:: bash

    docker pull fnndsc/pypx

Alternatively, you can build a local image with

.. code-block:: bash

    # If behing a proxy
    PROXY=http://some.proxy.com
    export UID=$(id -u)
    DOCKER_BUILDKIT=1 docker build --build-arg http_proxy=${PROXY} --build-arg UID=$UID -t local/pypx .

    # otherwise...
    export UID=$(id -u)
    DOCKER_BUILDKIT=1 docker build --build-arg UID=$UID -t local/pypx .

2.3 PyPI
========

For convenience, a PyPI installation is also available. This assumes additional non-python requirements such as ``dcmtk`` have been installed. This is recommended only for advanced users.

.. code-block:: bash

   apt-get update                                   \
   && apt-get install -y dcmtk                      \
   && apt-get install -y python3-pip python3-dev    \
   && pip3 install --upgrade pip                    \
   && pip install pypx

3. Configuring the containerized version
*******************************************

If using the container tool images directly, take care to assure that the machine receiving PACS transmissions is available and has a listener service accessible on an exposed port. This port should be accessible to the remote PACS. Our strong recommendation is to use the companion ``pfdcm`` container/repo to receive PACS data. Note that ``pfdcm`` itself contains ``pypx`` and will handle the reception and repacking of DICOM files using the correct ``pypx`` tools.

4 Usage
*********

4.1 ``PACS_QR.sh`` and ``workflow.sh``
======================================

For the most complete example, please consult the workflow.sh_ script in the source repository. This provides a Jupyter-notebook-shell-eque overview of most if not all the possible methods to call and use these tools.

For the most convenient example, use the ``PACS_QR.sh`` script -- consult its internal help with 

.. code-block:: bash 

  PACS_QR.sh -x

4.2 ``PACS_QR.sh`` quick-n-dirty
================================

The ``PACS_QR.sh`` has several implicit assumptions and values that can/should be set by approprate CLI. The entire scope is beyond this simple README, however, *assuming* these values are set (either by using the defaults or an appropriate/custom ``institution_set`` function), the workflow is rather simple. Assuming an MRN of say ``7654321``,

.. code-block:: bash

  # Query
  PACS_QR.sh -- "--PatientID 7654321"

  # Retrieve
  PACS_QR.sh --do retrieve -- "--PatientID 7654321"

  # Status
  PACS_QR.sh --do status -- "--PatientID 7654321"

  # Push to CUBE swift storage
  PACS_QR.sh --do push -- "--PatientID 7654321"

  # Register to CUBE internal DB
  PACS_QR.sh --do register -- "--PatientID 7654321"

Note carefully the syntax of the above commands! A ``--`` string separates script ``<key>/<value>`` pairs from a string defining the search parameters. Note that most valid DICOM tags can be used for this string. More tags can also make a search more specific, for instance

.. code-block:: bash

  "--PatientID 7654321 --StudyDate 19990909"

will limit returns only to hits performed on given ``StudyDate``.


5 Additional support (incomplete)
*********************************

Please see the relevant wiki pages for usage instructions (some are still under construction):

- pfstorage_
- px-do_
- px-echo_
- px-find_
- px-move_
- px-push_
- px-register_
- px-repack_
- px-report_
- px-status_
- px-smdb_

5. Credits
*****************

PyDicom_

-  Author(s): darcymason_

DCMTK_

-  Author(s): Dicom @ OFFIS Team

.. _px-repack: https://github.com/FNNDSC/pypx/wiki/1.-px-repack
.. _px-echo: https://github.com/FNNDSC/pypx/wiki/1.-px-echo
.. _px-find: https://github.com/FNNDSC/pypx/wiki/2.-px-find
.. _px-report: https://github.com/FNNDSC/pypx/wiki/4.-px-report
.. _px-move: https://github.com/FNNDSC/pypx/wiki/3.-px-move
.. _px-push: https://github.com/FNNDSC/pypx/wiki/3.-px-push
.. _px-register: https://github.com/FNNDSC/pypx/wiki/3.-px-register
.. _px-do: https://github.com/FNNDSC/pypx/blob/master/bin/px-do
.. _px-listen: https://github.com/FNNDSC/pypx/blob/master/bin/px-listen
.. _px-status: https://github.com/FNNDSC/pypx/blob/master/bin/px-status
.. _px-smdb: https://github.com/FNNDSC/pypx/wiki/3.-px-smdb
.. _workflow.sh: https://github.com/FNNDSC/pypx/blob/master/workflow.sh
.. _PyDicom: http://www.python.org/
.. _darcymason: https://github.com/darcymason
.. _DCMTK: http://dicom.offis.de/dcmtk.php.en
.. _pfstorage: https://github.com/FNNDSC/pypx/blob/master/bin/pfstorage

