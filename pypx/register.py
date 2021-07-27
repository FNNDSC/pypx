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
import  sys
import  subprocess
import  uuid
import  shutil
import  configparser
import  json
from    pathlib             import  Path
import  uuid
import  pathlib
import  datetime
from    datetime            import  date, datetime
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

from    argparse            import  Namespace, ArgumentParser
from    argparse            import  RawTextHelpFormatter

def parser_setup(str_desc):
    parser = ArgumentParser(
                description         = str_desc,
                formatter_class     = RawTextHelpFormatter
            )

    # JSONarg
    parser.add_argument(
        '--JSONargs',
        action  = 'store',
        dest    = 'JSONargString',
        type    = str,
        default = '',
        help    = 'JSON equivalent of CLI key/values')

    # db access settings
    parser.add_argument(
        '--db',
        action  = 'store',
        dest    = 'str_logDir',
        type    = str,
        default = '/tmp/log',
        help    = 'path to base dir of receipt database')

    parser.add_argument(
        '--upstreamFile',
        action  = 'store',
        dest    = 'upstreamFile',
        type    = str,
        default = '',
        help    = 'JSON report contained in file from upstream process')
    parser.add_argument(
        '--upstream',
        action  = 'store',
        dest    = 'reportData',
        type    = str,
        default = '',
        help    = 'JSON report from upstream process')

    parser.add_argument(
        '-p', '--xcrdir',
        action  = 'store',
        dest    = 'str_xcrdir',
        type    = str,
        default = '',
        help    = 'Directory containing a received study'
        )
    parser.add_argument(
        '-f', '--xcrfile',
        action  = 'store',
        dest    = 'str_xcrfile',
        type    = str,
        default = '',
        help    = 'File in <xcrdir> to process'
        )
    parser.add_argument(
        '--xcrdirfile',
        action  = 'store',
        dest    = 'str_xcrdirfile',
        type    = str,
        default = '',
        help    = 'Fully qualified file to process'
        )
    parser.add_argument(
        '--parseAllFilesWithSubStr',
        action  = 'store',
        dest    = 'str_filesubstr',
        type    = str,
        default = '',
        help    = 'Parse all files in <xcrdir> that contain <substr>'
        )
    parser.add_argument(
        '--localFileList',
        action  = 'store',
        dest    = 'localFileList',
        default = [],
        help    = 'a list of local files -- not used by CLI!'
        )
    parser.add_argument(
        '--objectFileList',
        action  = 'store',
        dest    = 'objectFileList',
        default = [],
        help    = 'a list of object files -- not used by CLI!'
        )
    parser.add_argument(
        '--PACS',
        action  = 'store',
        dest    = 'str_PACS',
        type    = str,
        default = '',
        help    = 'PACS name ID within swift storage'
        )

    # CUBE settings

    parser.add_argument(
        '--CUBE',
        action  = 'store',
        dest    = 'CUBE',
        type    = str,
        default = '',
        help    = 'CUBE lookup service identifier')

    parser.add_argument(
        '--CUBEURL',
        action  = 'store',
        dest    = 'str_CUBEURL',
        type    = str,
        default = 'http://localhost:8000/api/v1/',
        help    = 'CUBE URL'
        )
    parser.add_argument(
        '--CUBEusername',
        action  = 'store',
        dest    = 'str_CUBEusername',
        type    = str,
        default = 'chris',
        help    = 'Username with which to log into CUBE'
        )
    parser.add_argument(
        '--CUBEuserpasswd',
        action  = 'store',
        dest    = 'str_CUBEuserpasswd',
        type    = str,
        default = 'chris1234',
        help    = 'CUBE user password'
        )
    parser.add_argument(
        '--swiftServicesPACS',
        action  = 'store',
        dest    = 'str_swiftServicesPACS',
        type    = str,
        default = '',
        help    = 'swift PACS location within SERVICE/PACS to push files')

    parser.add_argument(
        '--cleanup',
        action  = 'store_true',
        dest    = 'b_cleanup',
        default = False,
        help    = 'If specified, then cleanup temporary files'
        )
    parser.add_argument(
        '--debug',
        action  = 'store_true',
        dest    = 'b_debug',
        default = False,
        help    = 'If specified, then also log debug info to <logdir>'
        )
    parser.add_argument(
        "-v", "--verbosity",
        help    = "verbosity level for app",
        dest    = 'verbosity',
        type    = int,
        default = 1)
    parser.add_argument(
        "--json",
        help    = "return a JSON payload",
        dest    = 'json',
        action  = 'store_true',
        default = False
    )
    parser.add_argument(
        "-x", "--desc",
        help    = "show long synopsis",
        dest    = 'b_desc',
        action  = 'store_true',
        default = False
    )
    parser.add_argument(
        "-y", "--synopsis",
        help    = "show short synopsis",
        dest    = 'b_synopsis',
        action  = 'store_true',
        default = False
    )
    parser.add_argument(
        '--version',
        help    = 'if specified, print version number',
        dest    = 'b_version',
        action  = 'store_true',
        default = False
    )

    return parser

def parser_interpret(parser, *args):
    """
    Interpret the list space of *args, or sys.argv[1:] if
    *args is empty
    """
    if len(args):
        args    = parser.parse_args(*args)
    else:
        args    = parser.parse_args(sys.argv[1:])
    return args

def parser_JSONinterpret(parser, d_JSONargs):
    """
    Interpret a JSON dictionary in lieu of CLI.

    For each <key>:<value> in the d_JSONargs, append to
    list two strings ["--<key>", "<value>"] and then
    argparse.
    """
    l_args  = []
    for k, v in d_JSONargs.items():
        l_args.append('--%s' % k)
        if type(v) == type(True): continue
        l_args.append('%s' % v)
    return parser_interpret(parser, l_args)

class Register():
    """
    The core class of the register module -- this class essentially reads
    a DICOM file, parses its tags, and then registers tags of that file
    with a ChRIS/CUBE instance. This of course assumes that the file has been
    pushed to CUBE using some mechanism (most typically ``pfstorage``).
    """

    def serviceKey_process(self) -> dict:
        """
        If a service key (--CUBE <key>) has been specified, read from
        smdb service storage and set the CLI flags to pass on along to
        pfstorage.
        """
        d_CUBEinfo :   dict    = {}
        d_CUBEinfo['status']   = False
        if len(self.args.CUBE):
            d_CUBEinfo = self.smdb.service_keyAccess('CUBE')
            if d_CUBEinfo['status']:
                self.args.str_CUBEURL           = d_CUBEinfo['CUBE'][self.args.CUBE]['url']
                self.args.str_CUBEusername      = d_CUBEinfo['CUBE'][self.args.CUBE]['username']
                self.args.str_CUBEuserpasswd    = d_CUBEinfo['CUBE'][self.args.CUBE]['password']

        return d_CUBEinfo

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
        self.serviceKey_process()
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

    def PACSdata_checkFormatting(self, d_pacsData):
        """
        A simple method to check on some values in the d_pacsData
        dictionary. In particular, convert dates from the DICOM DA
        format of YYYYMMDD to YYYY-MM-DD, and PatientAge is recast
        as age in days.
        """
        for field in d_pacsData.keys():
            if 'date' in  field.lower():
                try:
                    d_pacsData[field]  = datetime.strptime(
                                            d_pacsData[field], 
                                            "%Y%m%d").strftime('%Y-%m-%d'
                                        )
                except:
                    pass
            if 'patientage' in field.lower():
                str_age     = d_pacsData['PatientAge']
                if not str_age[-1].isnumeric():
                    try:
                        age     = int(str_age[0:-1])
                    except:
                        age     = -1
                    AS      = str_age[-1]
                    if AS == 'Y':   age *= 365
                    if AS == 'M':   age *= 30
                    if AS == 'W':   age *= 7
                    if AS == 'D':   age *= 1
                    d_pacsData['PatientAge']    = '%s' % age
        return d_pacsData

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
                try:
                    d_pacsData[k] = d_DICOMfile_read['d_DICOM']['d_dicomSimple'][k]
                except Exception as e:
                    d_pacsData[k]   = "%s" % e
            d_pacsData['pacs_name']     = self.args.str_swiftServicesPACS
            d_pacsData                  = self.PACSdata_checkFormatting(d_pacsData)
            if len(self.args.objectFileList):
                i = self.args.localFileList.index(str_file)
                d_pacsData['path']      = self.args.objectFileList[i]
            else:
                d_path                  =  self.packer.packPath_resolve(d_DICOMfile_read)

                d_pacsData['path']      = 'SERVICES/PACS/%s/%s/%s' % \
                    (
                        self.args.str_swiftServicesPACS,
                        d_path['packDir'],
                        d_path['imageFile']
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
        recording this registration operation.
        """
        b_status        :   bool    = False
        d_register      :   dict    = {}

        if d_DICOMfile_register['status']:
            b_status    = True
            self.smdb.housingDirs_create()
            d_register  = d_DICOMfile_register['d_CUBE_register_pacs_file']
            if 'id' in d_register.keys():
                l_pop       = [d_register.pop(k) for k in ['id', 'creation_date', 'fname', 'fsize']]
            # Record in the smdb an entry for each series
            self.smdb.d_DICOM   = d_DICOMfile_register['d_DICOMfile_read']['d_DICOM']['d_dicomSimple']
            now                 = datetime.now()
            self.smdb.seriesData('register', 'info',        d_register)
            self.smdb.seriesData('register', 'timestamp',   now.strftime("%Y-%m-%d, %H:%M:%S"))
            if len(self.args.CUBE):
                self.smdb.seriesData('register', 'CUBE',
                    self.smdb.service_keyAccess('CUBE')['CUBE'][self.args.CUBE])

        return {
            'status'                : b_status,
            'd_DICOMfile_register'  : d_DICOMfile_register
        }

