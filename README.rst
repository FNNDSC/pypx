####################################
pypx - 3.0.34
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

``pypx`` is a *complete* client-side PACS (Picture Archive and Communications System) Query/Retrieve/Storage solution that operates in stand-alone script mode in addition to providing a set of python modules for use in other packages. The modules/API provide a simple mechanism for a python program to interact with an appropriately configured remote PACS, while the stand alone scripts offer a convenient ability to directly Query/Retrieve/Storge images from the command line.

``pypx`` was mostly developed for use in the ChRIS system as part of the ``pfdcm`` microservice; however the CLI scripts of ``pypx`` and the provided docker image offer a quick and powerful means of accessing a PACS without any additional overhead.

1.1 Complete **Client** Side
============================

This solution is **client**-side and cannot operate fully independently of an appropriately configured PACS. Having said that, in the dockerized mode (either by building a local container or using the container provided on dockerhub (``fnndsc/pypx``) all the necessary infrastructure is provided to listen for and store incoming image data. Some minor post configuration might however be required.

1.1.1 Quick PACS Primer
-----------------------

A PACS exists as a separate service on a network, and ``pypx`` communicates with a pre-configured PACS when asking for Query data and when Retrieving images. Importantly, from the client perspective, data is **PUSHED** from the PACS, and not **PULLED** from the client. This means that client software in essence "asks" the PACS for images and the PACS obliges by transmitting the images over the network to a pre-configured location.

Communications with a PACS are for the most insecure and reflected a circa 1990s view/model of internetworking. When a client communicates with a PACS, it sends along with every request string identifiers unique to the client and configured in the PACS. Typical identifiers are the ``AETitle`` and sometimes additionally the ``CalledAETitle``. The PACS examines these strings on receipt to identify/authenticate the client and also to identify a destination network ``IP:port`` to which data can be transmitted.

1.1.2 Configuring a PACS
-------------------------

In order to be fully complete, a destination PACS with which ``pypx`` modules wish to communicate needs to be configured with appropriate ``AETitle``, ``CalledAETitle``, as well as the network address IP and port of the ``pypx`` hosting machine. Configuring a PACS is obviously outside of the scope of this documentation. Consult your PACS for information on this configuration.

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

Internally, the code wraps around DCMTK utilies as well as the PyDicom module. The following modules/scripts are provided:

- px-repack_: Read and repack DICOM files, organizing the destination in a human-friendly tree based layout.

- px-echo_: Ping the PACS to make sure it is online (``echoscu``).

- px-find_: Find data on the PACS (``findscu``).

- px-report_: Consume the JSON outputs of many of the tools (esp the ``px-find`` and generate various console-based reports).

- px-move_: Move data from the PACS (``movescu``).

- px-push_: Push DICOM data to a remote node (either a PACS or a ChRIS swift object storage container).

- px-register_: A companion to ``px-push`` that registers files in ChRIS swift storage to the ChRIS CUBE backend.

- px-smdb_: A simple file-system based database that provides tracking and query for processed DICOM files.

2. Installation
*****************

2.1 Using docker
================

Using the dockerized container is the recommended installation vector as the image contains a configured listener service that can receive image data without any additional software on the host system.

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

2.2 pypi
========

For convenience, a PyPI installation is also available. Note that to be useful for image reception, services on the host machine for listening on a given port and interacting with ``px-listen`` must be manually configured. This is recommended only for advanced users.

.. code-block:: bash

   apt-get update                                   \
   && apt-get install -y dcmtk                      \
   && apt-get install -y python3-pip python3-dev    \
   && pip3 install --upgrade pip                    \
   && pip install pypx

3. Configuring the containerized version
*******************************************

The container is preconfigured to receive image data on port 10402. This port should be accessible to the remote PACS, and note that if the docker container is run directly with the ``docker`` command be sure to publish this port with

.. code-block:: bash

    docker run  --rm -ti                        \
            -p 10402:10402                      \
            ...

If necessary, this port can be changed in the ``Dockerfile`` for a local build of the container.

4. Usage
*****************

For more complete examples, please consult the workflow.sh_ script in the source repository

Please see the relevant wiki pages for usage instructions:

- px-repack_
- px-echo_
- px-find_
- px-report_
- px-move_
- px-push_
- px-register_
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
.. _px-smdb: https://github.com/FNNDSC/pypx/wiki/3.-px-smdb
.. _workflow.sh: https://github.com/FNNDSC/pypx/blob/master/workflow.sh
.. _PyDicom: http://www.python.org/
.. _darcymason: https://github.com/darcymason
.. _DCMTK: http://dicom.offis.de/dcmtk.php.en
.. _echoscu: http://support.dcmtk.org/docs/echoscu.html
.. _findscu: http://support.dcmtk.org/docs/findscu.html
.. _movescu: http://support.dcmtk.org/docs/movescu.html
.. _storescp: http://support.dcmtk.org/docs/storescp.html
.. _DICOM_Listener: https://github.com/FNNDSC/pypx/wiki/dicom_listener
