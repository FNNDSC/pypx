# Turn off all logging for modules in this libary!!
# Any log noise from pydicom will BREAK receiving
# DICOM data from the remote PACS since the log messages
# will pollute and destroy the DICOM storescp protocol.
import logging
logging.disable(logging.CRITICAL)

from    argparse            import  Namespace

# Global modules
import  os
from    os                  import  listdir
from    os.path             import  isfile, join
import  subprocess
import  uuid
import  shutil
import  configparser
import  json
from    pathlib             import  Path
import  uuid
import  pathlib
import  datetime
import  inspect

import  re

# PyDicom module
import  pydicom             as      dicom
from    chrisclient         import  client

# PYPX modules
import  pypx.utils
import  pypx.smdb
import  pypx.repack

# Debugging
import  pudb
from    pudb.remote         import  set_trace
import  pfmisc

class Register():
    """
    The core class of the register module -- this class essentially reads
    a DICOM file, parses its tags, and then registers tags of that file
    with a ChRIS/CUBE instance. This of course assumes that the file has been
    pushed to CUBE using some mechanism (most typically ``pfstorage``).
    """

    def loggers_create(self):
        """
        >>>>>>>>>>>>>>   Debugging control  <<<<<<<<<<<<<<<<
        Essentially we create some pfmisc.debug objects that
        write to files and also give them some shortcut names
        """
        str_thisMRsession       = pathlib.PurePath(self.args.str_xcrdir).name
        self.str_debugFile      = '%s/register.log'       % self.args.str_logDir
        self.dp                 = pfmisc.debug(
                                            verbosity   = int(self.args.verbosity),
                                            level       = 2,
                                            within      = self.__name__,
                                            debugToFile = self.args.b_debug,
                                            debugFile   = self.str_debugFile
                                            )
        self.log                = self.dp.qprint

    def filesToRegister_determine(self):
        """
        Based on the pattern of CLI calling flags, determine which
        files to register.
        """
        if self.args.str_filesubstr:
            # First create a list of all the files...
            self.l_files    = [
                f                                                       \
                    for f in listdir(self.args.str_xcrdir)              \
                        if isfile(join(self.args.str_xcrdir, f))
            ]
            # Now filter them according to the passed filesubstr
            self.l_files    = [
                x                                                       \
                    for y in self.args.str_filesubstr.split(',')        \
                        for x in self.l_files if y in x
            ]
        elif self.args.str_xcrdirfile:
            self.l_files.append(self.args.str_xcrfile)
        elif len(self.args.localFileList):
            self.l_files    = self.args.localFileList

    def __init__(self, args):

        self.__name__           : str   = 'register'
        self.l_files            : list  = []

        # Check if an upstream 'reportData' exists, and if so
        # merge those args with the current namespace:
        d_args                          = vars(args)
        if 'upstream' in d_args.keys():
            d_argCopy           = d_args.copy()
            # "merge" these 'arg's with upstream.
            d_args.update(d_args['upstream'])
            [setattr(args, k, v) for k,v in d_args.items()]
        self.args                       = args

        if len(self.args.str_xcrdirfile):
            self.args.str_xcrdir        = os.path.dirname(
                                                self.args.str_xcrdirfile
                                        )
            self.args.str_xcrfile       = os.path.basename(
                                                self.args.str_xcrdirfile
                                        )

        self.smdb                       = pypx.smdb.SMDB(args)
        self.packer                     = pypx.repack.Process(
                                            pypx.repack.args_impedanceMatch(args)
                                        )
        self.CUBE                       = client.Client(
                                            self.args.str_CUBEURL,
                                            self.args.str_CUBEusername,
                                            self.args.str_CUBEuserpasswd
                                        )

        self.filesToRegister_determine()
        self.loggers_create()
        self.log(
            'Register DICOM dir: %s' % (self.args.str_xcrdir),
            level = 2
        )
        for str_file in self.l_files:
            self.log(
                'Regsiter DICOM file: %s' % (str_file),
                level = 2
            )
        self.initDone   = True


    def run(self, opt) -> dict:
        """
        Main entry point for registration. This will, for each DICOM file
        to process, read the DICOM, perform some preprocessing on the meta
        tag  space,  and then register the already existing object in
        object storage.

        A CRITICAL assumption here is that the file to be registered already
        exists in storage! For now, this assumption is not verified/tested!
        """
        dl_run      : list  = []
        d_run       : dict  = {'status' : False}
        for str_file in self.l_files:
            d_run           = self.DICOMfile_mapsUpdate(
                                self.DICOMfile_register(
                                    self.packer.DICOMfile_read(
                                        file = '%s/%s' % (
                                                self.args.str_xcrdir,
                                                str_file
                                            )
                                    ),
                                str_file)
                            )
            # Before returning, we need to "sanitize" some of the
            # DICOMfile_read fields, specifically the DICOM read
            # payload that can be very full/noisy. Here we just
            # remove it.
            d_run['d_DICOMfile_register']['d_DICOMfile_read']\
                    .pop('d_DICOM')
            dl_run.append(d_run)

        return {
            'status'    : d_run['status'],
            'run'       : dl_run
        }

    def DICOMfile_register(self, d_DICOMfile_read, str_file)    -> dict:
        """
        Register the DICOM file described by the passed dictionary
        structure. If the self.arg['objectFileList'] is empty, this
        method will ask the repack module where to file would have
        been packed into storage.
        """
        b_status        :   bool    = False
        d_pacsData      :   dict    = {}
        d_register      :   dict    = {}
        ld_register     :   list    = []
        l_DICOMtags     :   list    = [
            'PatientID',    'PatientName',      'PatientBirthDate',
            'PatientAge',   'PatientSex',       'ProtocolName',
            'StudyDate',    'StudyDescription', 'StudyInstanceUID',
            'Modality',     'SeriesDescription','SeriesInstanceUID'
        ]
        if d_DICOMfile_read['status']:
            for k in l_DICOMtags:
                d_pacsData[k] = d_DICOMfile_read['d_DICOM']['d_dicomSimple'][k]
            d_pacsData['pacs_name']     = self.args.str_swiftServicesPACS
            if len(self.args.objectFileList):
                i = self.args.localFileList.index(str_file)
                d_pacsData['path']      = self.args.objectFileList[i]
            else:
                d_path                  =  self.packer.packPath_resolve(d_DICOMfile_read)

                d_pacsData['path']      = 'SERVICES/PACS/%s/%s/%s' % \
                    (
                        self.arg['str_swiftPACS'],
                        d_path['packDir'],
                        d_path['imageFIle']
                    )
            try:
                d_register = self.CUBE.register_pacs_file(d_pacsData)
            except Exception as e:
                d_register = {
                    'path'          : d_pacsData['path'],
                    'msg'           : '%s' % str(e)
                }
        return {
            'status'                    :   True,
            'd_DICOMfile_read'          :   d_DICOMfile_read,
            'd_CUBE_register_pacs_file' :   d_register
        }

    def DICOMfile_mapsUpdate(self, d_DICOMfile_register)    -> dict:
        """
        Interact with the SMDB object to update JSON mapping information
        relative to this save operation.
        """
        b_status        :   bool    = False

        if d_DICOMfile_register['status']:
            b_status    = True
            self.smdb.housingDirs_create()
            # self.smdb.DICOMobj_set(d_DICOMfile_save ['d_DICOMfile_read']\
            #                                         ['d_DICOM']\
            #                                         ['d_dicomSimple'])
            # self.smdb.mapsUpdateForFile(
            #         '%s/%s' % ( d_DICOMfile_save['outputDir'],
            #                     d_DICOMfile_save['outputFile'])
            # )

        return {
            'status'                : b_status,
            'd_patientInfo'         : self.smdb.d_patientInfo,
            'd_studyInfo'           : self.smdb.d_studyInfo,
            'd_seriesInfo'          : self.smdb.d_seriesInfo,
            'd_DICOMfile_register'  : d_DICOMfile_register
        }

