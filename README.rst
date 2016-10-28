####################################
PyPx - v0.2
####################################
.. image:: https://badge.fury.io/py/pypx.svg
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

.. code-block::
   
   # pip package
   $> pip install pypx

***************
3. Usage
***************
Scripts
===============

.. code-block::

   # in a terminal
   $> px-echo

Modules
===============

.. code-block::

   # in yourscript.py
   import pypx

   output = pypx.echo(options)
   print(output)