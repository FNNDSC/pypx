####################################
PyPx - 0.8
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

Pypx is a simple Python wrapper around DCMTK and PyDicom. It provides 4 simple way to interact with the PACS:

- **px-echo:** Ping the PACS to make sure it is online (*echoscu*).

- **px-find:** Find data on the PACS (*findscu*).

- **px-move:** Move data from the PACS (*movescu*).

- **px-listen:** Listen for incoming data from the PACS (*storescp*).

2. Installation
*****************

.. code-block:: bash

   apt-get update \
   && apt-get install -y dcmtk \
   && apt-get install -y python3-pip python3-dev \
   && pip3 install --upgrade pip \
   && pip install pypx

3. Usage
*****************

px-echo
===============

about px-echo
-------------------
``px-echo`` is a wrapper around dcmtk echoscu_.

::

    It sends a DICOM C-ECHO message to a Service Class Provider (SCP) and waits for a response.
    The application can be used to verify basic DICOM connectivity.
    -- DCMTK, about echoscu.

px-echo script
-------------------
.. code-block:: bash

   # need some help?
   px-echo --help


   # ping Orthanc PACS server
   # calling aet: CHIPS
   # called aet: ORTHANC
   # Orthanc PACS server IP: 127.0.0.1
   # Orthanc PACS server port: 4242
   # echoscu executable: /usr/local/bin/echoscu
   px-echo --aet CHIPS --aec ORTHANC --serverIP 127.0.0.1 --serverPort 4242 --executable /usr/local/bin/echoscu

   # output
   #   { 'status': 'success',
   #     'command': '/usr/local/bin/echoscu --timeout 5  -aec ORTHANC -aet CHIPS 127.0.0.1 4242',
   #     'data': ''}

px-echo module
-------------------

.. code-block:: python

   # in yourscript.py
   import pypx

   pacs_settings = {
     'executable': '/usr/local/bin/echoscu',
     'aec': 'ORTHANC',
     'aet': 'CHIPS',
     'server_ip': '127.0.0.1',
     'server_port': '4242',
   }

   output = pypx.echo(pacs_settings)
   print(output)

   # output:
   # {
   #   'command': '/bin/echoscu --timeout 5  -aec MY-AEC -aet MY-AET 192.168.1.110 4242',
   #   'data': '',
   #   'status': 'success'
   # }

px-find
===============

about px-find
-------------------
``px-find`` is a wrapper around dcmtk findscu_.

Find series on a PACS server given a vast array of parameters. See ``px-find --help`` for the full list.

::

    It sends query keys to an SCP and awaits responses.
    The application can be used to test SCPs of the Query/Retrieve and Basic Worklist Management Service Classes.
    -- DCMTK, about findscu.

px-find script
-------------------
.. code-block:: bash

   # need some help?
   px-find --help


   # find data in Orthanc PACS server
   # calling aet: CHIPS
   # called aet: ORTHANC
   # Orthanc PACS server IP: 127.0.0.1
   # Orthanc PACS server port: 4242
   # findscu executable: /usr/local/bin/findscu
   px-find --aet CHIPS --aec ORTHANC --serverIP 127.0.0.1 --serverPort 4242 --executable /usr/local/bin/findscu \
     --patientID 32124

   # output
   #   {'status': 'success',
   #    'command': '/usr/local/bin/findscu -xi -S 
   #      -k InstanceNumber
   #      -k ModalitiesInStudy
   #      -k NumberOfSeriesRelatedInstances
   #      -k PatientBirthDate
   #      -k "PatientID=32124"
   #      -k PatientName
   #      -k PatientSex
   #      -k PerformedStationAETitle
   #      -k "QueryRetrieveLevel=SERIES"
   #      -k SeriesDate
   #      -k SeriesDescription
   #      -k SeriesInstanceUID
   #      -k StudyDate
   #      -k StudyDescription
   #      -k StudyInstanceUID 
   #      -aec ORTHANC -aet CHIPS 127.0.0.1 4242',
   #    'data': [lot of stuff if a match] # [] if no results
   #    }

px-find module
-------------------

.. code-block:: python

   # in yourscript.py
   import pypx

   pacs_settings = {
     'executable': '/usr/local/bin/findscu',
     'aec': 'ORTHANC',
     'aet': 'CHIPS',
     'server_ip': '127.0.0.1',
     'server_port': '4242',
   }

   # query parameters
   query_settings = {
       'PatientID': 32124,
    }

   # python 3.5 ** syntax
   output = pypx.find({**pacs_settings, **query_settings})
   print(output)

   # output
   #   {'status': 'success',
   #    'command': '/usr/local/bin/findscu -xi -S 
   #      -k InstanceNumber
   #      -k ModalitiesInStudy
   #      -k NumberOfSeriesRelatedInstances
   #      -k PatientBirthDate
   #      -k "PatientID=32124"
   #      -k PatientName
   #      -k PatientSex
   #      -k PerformedStationAETitle
   #      -k "QueryRetrieveLevel=SERIES"
   #      -k SeriesDate
   #      -k SeriesDescription
   #      -k SeriesInstanceUID
   #      -k StudyDate
   #      -k StudyDescription
   #      -k StudyInstanceUID 
   #      -aec ORTHANC -aet CHIPS 127.0.0.1 4242',
   #    'data': [lot of stuff if a match] # [] if no results
   #    }

px-move
===============

about px-move
-------------------
``px-move`` is a wrapper around dcmtk movescu_.

Move series given its SeriesUID. SeriesUID can be retrieved with ``px-find``.

::

    It sends query keys to an SCP and awaits responses.
    The application can be used to test SCPs of the Query/Retrieve Service Class. The movescu application can initiate the transfer of images to a third party or can retrieve images to itself.
    -- DCMTK, about movescu.

px-move script
-------------------
.. code-block:: bash

   px-move --help

   # move data from Orthanc PACS server to AETL
   # calling aet: CHIPS
   # calling aet that will receive the data: CHIPS
   # called aet: ORTHANC
   # Orthanc PACS server IP: 127.0.0.1
   # Orthanc PACS server port: 4242
   # movescu executable: /usr/local/bin/movescu
   px-move --aet CHIPS --aetl CHIPS --aec ORTHANC --serverIP 127.0.0.1 --serverPort 4242 --executable /usr/local/bin/movescu \
     --seriesUID 1.3.12.2.1107.5.2.32.35235.2012041417312491079284166.0.0.0

   # output
   #   {'status': 'success',
   #    'command': '/usr/local/bin/movescu --move CHIPS --timeout 5
   #      -k QueryRetrieveLevel=SERIES
   #      -k SeriesInstanceUID=1.3.12.2.1107.5.2.32.35235.2012041417312491079284166.0.0.0 
   #      -aec ORTHANC -aet CHIPS 127.0.0.1 4242',
   #    'data': ''
   #    }

px-move module
-------------------

.. code-block:: python

   # in yourscript.py
   import pypx

   pacs_settings = {
     'executable': '/usr/local/bin/findscu',
     'aec': 'ORTHANC',
     'aet': 'CHIPS',
     'server_ip': '127.0.0.1',
     'server_port': '4242',
   }

   # query parameters
   query_settings = {
       'SeriesInstanceUID': '1.3.12.2.1107.5.2.32.35235.2012041417312491079284166.0.0.0',
    }

   # python 3.5 ** syntax
   output = pypx.move({**pacs_settings, **query_settings})
   print(output)

   # output
   #   {'status': 'success',
   #    'command': '/usr/local/bin/movescu --move CHIPS --timeout 5
   #      -k QueryRetrieveLevel=SERIES
   #      -k SeriesInstanceUID=1.3.12.2.1107.5.2.32.35235.2012041417312491079284166.0.0.0 
   #      -aec ORTHANC -aet CHIPS 127.0.0.1 4242',
   #    'data': ''
   #    }

px-listen
===============

about px-listen
-------------------
``px-listen`` is a wrapper around dcmtk storescp_.

It should be connected to a daemon/service in order to act as a DICOM_Listener_.

::

     It listens on a specific TCP/IP port for incoming association requests from a Storage Service Class User (SCU).
     It can receive both DICOM images and other DICOM composite objects.
    -- DCMTK, about storescp.

px-listen script
-------------------
.. code-block:: bash

   px-listen --help

   # receive DICOM data Orthanc PACS server
   # tmp directory to store the data before ordering: /tmp
   # log directory to log all incoming/processing data : /incoming/log
   # data directory to store ordered data : /incoming/data
   # storescp executable: /usr/local/bin/storescp
   px-listen -t /tmp -l /incoming/log -d /incoming/data --executable /usr/local/bin/storescp

4. Credits
*****************
   
PyDicom_

-  Author(s): darcymason_

DCMTK_

-  Author(s): Dicom @ OFFIS Team

.. _PyDicom: http://www.python.org/
.. _darcymason: https://github.com/darcymason
.. _DCMTK: http://dicom.offis.de/dcmtk.php.en
.. _echoscu: http://support.dcmtk.org/docs/echoscu.html
.. _findscu: http://support.dcmtk.org/docs/findscu.html
.. _movescu: http://support.dcmtk.org/docs/movescu.html
.. _storescp: http://support.dcmtk.org/docs/storescp.html
.. _DICOM_Listener: https://github.com/FNNDSC/pypx/wiki/dicom_listener
