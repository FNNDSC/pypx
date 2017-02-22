####################################
PyPx - 0.7
####################################

.. image:: https://badge.fury.io/py/pypx.svg
    :target: https://badge.fury.io/py/pypx

.. image:: https://travis-ci.org/FNNDSC/pypx.svg?branch=master
    :target: https://travis-ci.org/FNNDSC/pypx

.. image:: https://img.shields.io/badge/python-3.5%2B-blue.svg
    :target: https://badge.fury.io/py/pypx

***************
1. Overview
***************

Pypx is a simple Python wrapper around DCMTK and PyDicom. It provides 4 simple way to interact with the PACS:

1. **px-echo:** Ping the PACS to make sure it is online (*echoscu*).

2. **px-find:** Find data on the PACS (*findscu*).

3. **px-move:** Move data on the PACS (*movescu*).

4. **px-listen:** Listen for incoming data from the PACS (*storescp*).

***************
2. Installation
***************

.. code-block:: bash
   
   pip install pypx

***************
3. Usage
***************

Scripts
===============

.. code-block:: bash

   px-echo --help

Modules
===============

.. code-block:: python

   # in yourscript.py
   import pypx

   options = {
     'executable': '/bin/echoscu',
     'aec': 'MY-AEC',
     'aet': 'MY-AET',
     'server_ip': '192.168.1.110',
     'server_port': '4242'
   }

   output = pypx.echo(options)
   print(output)

   # output:
   # {
   #   'command': '/bin/echoscu --timeout 5  -aec MY-AEC -aet MY-AET 192.168.1.110 4242',
   #   'data': '',
   #   'status': 'success'
   # }

***************
4. Credits
***************
   
PyDicom_

-  Author(s): darcymason_

DCMTK_

-  Author(s): Dicom @ OFFIS Team

.. _PyDicom: http://www.python.org/
.. _darcymason: https://github.com/darcymason
.. _DCMTK: http://dicom.offis.de/dcmtk.php.en