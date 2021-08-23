"""
                                         _  _
                                        | || |
                     ___  _ __ ___    __| || |__
                    / __|| '_ ` _ \  / _` || '_ \.
                    \__ \| | | | | || (_| || |_) |
                    |___/|_| |_| |_| \__,_||_.__/


        A simple map database of JSON "table" objects/files.

This module provides support for a simple file-system database of JSON
file tables that define/track the state, description, location, and other
meta data associated with received DICOM files.

Three core map file/tables exist:

    <dataLogDir>/patientData/patientData-<%PatientID>.json
    <dataLogDir>/studyData/studyData-<%StudyInstanceUID>.json
    <dataLogDir>/seriesData/<%SeriesInstanceUID>/seriesData-%%imageFile.json

NB: This module is currently NOT THREAD SAFE as of April 2021! Collisions
occur if multiple jobs try and read/write to the map files concurrently which
happens if scheduled in an async xinetd storescp pipeline.

Typical safe calling spec for an xinetd controlled storescp is

    storescp -od /tmp/data -pm -sp \
        -xcr "/home/rudolphpienaar/src/pypx/bin/px-repack
              --xcrdir #p --xcrfile #f --verbosity 0"       \
        11113

"""

import  sys, os, os.path
import  json
import  pudb
import  datetime
import  copy
import  re

from    retry           import  retry
from    pypx            import  repack
import  pfmisc
import  inspect

from    argparse        import  Namespace, ArgumentParser
from    argparse        import  RawTextHelpFormatter

import  fcntl
import  time
import  pudb

def parser_setup(str_desc):
    parser = ArgumentParser(
                description         = str_desc,
                formatter_class     = RawTextHelpFormatter
            )

    parser.add_argument(
        '--JSONargs',
        action  = 'store',
        dest    = 'JSONargString',
        type    = str,
        default = '',
        help    = 'JSON equivalent of CLI key/values')

    parser.add_argument(
        '-p', '--xcrdir',
        action  = 'store',
        dest    = 'str_xcrdir',
        type    = str,
        default = '/tmp',
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
        '--action',
        action  = 'store',
        dest    = 'str_action',
        type    = str,
        default = '',
        help    = 'DB action to perform'
        )
    parser.add_argument(
        '--actionArgs',
        action  = 'store',
        dest    = 'str_actionArgs',
        type    = str,
        default = '',
        help    = 'DB action args'
        )
    parser.add_argument(
        '-l', '--logdir',
        action  = 'store',
        dest    = 'str_logDir',
        type    = str,
        default = '/tmp/log',
        help    = 'Directory to store log files'
        )

    parser.add_argument(
        '--AccessionNumber',
        action  = 'store',
        dest    = 'AccessionNumber',
        type    = str,
        default = '',
        help    = 'Accession Number')
    parser.add_argument(
        '--PatientID',
        action  = 'store',
        dest    = 'PatientID',
        type    = str,
        default = '',
        help    = 'Patient ID')
    parser.add_argument(
        '--PatientName',
        action  = 'store',
        dest    = 'PatientName',
        type    = str,
        default = '',
        help    = 'Patient name')
    parser.add_argument(
        '--PatientSex',
        action  = 'store',
        dest    = 'PatientSex',
        type    = str,
        default = '',
        help    ='Patient sex')
    parser.add_argument(
        '--StudyDate',
        action  = 'store',
        dest    = 'StudyDate',
        type    = str,
        default = '',
        help    = 'Study date (YYYY/MM/DD)')
    parser.add_argument(
        '--ModalitiesInStudy',
        action  = 'store',
        dest    = 'ModalitiesInStudy',
        type    = str,
        default = '',
        help    = 'Modalities in study')
    parser.add_argument(
        '--Modality',
        action  = 'store',
        dest    = 'Modality',
        type    = str,
        default = '',
        help    = 'Study Modality')
    parser.add_argument(
        '--PerformedStationAETitle',
        action  = 'store',
        dest    = 'PerformedStationAETitle',
        type    = str,
        default = '',
        help    = 'Performed station aet')
    parser.add_argument(
        '--StudyDescription',
        action  = 'store',
        dest    = 'StudyDescription',
        type    = str,
        default = '',
        help    = 'Study description')
    parser.add_argument(
        '--SeriesDescription',
        action  = 'store',
        dest    = 'SeriesDescription',
        type    = str,
        default = '',
        help    = 'Series Description')
    parser.add_argument(
        '--SeriesInstanceUID',
        action  = 'store',
        dest    = 'SeriesInstanceUID',
        type    = str,
        default = '',
        help    = 'Series Instance UID')
    parser.add_argument(
        '--StudyInstanceUID',
        action  = 'store',
        dest    = 'StudyInstanceUID',
        type    = str,
        default = '',
        help    = 'Study Instance UID')
    parser.add_argument(
        '--ProtocolName',
        action  = 'store',
        dest    = 'ProtocolName',
        type    = str,
        default = '',
        help    = 'Protocol Name')
    parser.add_argument(
        '--AcquisitionProtocolName',
        action  = 'store',
        dest    = 'AcquisitionProtocolName',
        type    = str,
        default = '',
        help    = 'Acquisition Protocol Description Name')

    parser.add_argument(
        '--AcquisitionProtocolDescription',
        action  = 'store',
        dest    = 'AcquisitionProtocolDescription',
        type    = str,
        default = '',
        help    = 'Acquisition Protocol Description')

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
        if type(v) == type(True):
            if v: l_args.append('--%s' % k)
            continue
        l_args.append('--%s' % k)
        l_args.append('%s' % v)
    return parser_interpret(parser, l_args)

class SMDB_models():
    """
    The core data models used by the SMDB database
    """

    def __init__(self):
        self.__name__           : str   = 'smdb_models'

        self.d_patientModel     : dict  = {
            'PatientID'                         : 'Not defined',
            'PatientName'                       : 'Not defined',
            'PatientAge'                        : 'Not defined',
            'PatientSex'                        : 'Not defined',
            'PatientBirthDate'                  : 'Not defined'
        }

        self.d_studyModel       : dict  = {
            'PatientID'                         : 'Not defined',
            'StudyDescription'                  : 'Not defined',
            'StudyDate'                         : 'Not defined',
            'StudyInstanceUID'                  : 'Not defined',
            'PerformedStationAETitle'           : 'Not defined'
        }

        self.d_seriesModel       : dict  = {
            'PatientID'                         : 'Not defined',
            'StudyInstanceUID'                  : 'Not defined',
            'SeriesInstanceUID'                 : 'Not defined',
            'SeriesDescription'                 : 'Not defined',
            'SeriesNumber'                      : 'Not defined',
            'SeriesDate'                        : 'Not defined',
            'Modality'                          : 'Not defined'
        }

    def patientModel_get(self)                   -> dict:
        return copy.deepcopy(self.d_patientModel)

    def patientModel_reset(self, d_legacy)       -> dict:
        d_legacy.clear()
        return self.patientModel_get()

    def studyModel_get(self)                     -> dict:
        return copy.deepcopy(self.d_studyModel)

    def studyModel_reset(self, d_legacy)         -> dict:
        d_legacy.clear()
        return self.studyModel_get()

    def seriesModel_get(self)                    -> dict:
        return copy.deepcopy(self.d_seriesModel)

    def seriesModel_reset(self, d_legacy)        -> dict:
        d_legacy.clear()
        return self.seriesModel_get()

class SMDB():

    def fileSpec_process(self):
        """
        Parse a file spec -- used if the module is called from the CLI
        on a specific DICOM file to update.
        """

        if len(self.args.str_xcrdirfile):
            self.args.str_xcrdir        = os.path.dirname(
                                                self.args.str_xcrdirfile
                                        )
            self.args.str_xcrfile       = os.path.basename(
                                                self.args.str_xcrdirfile
                                        )
        try:
            self.args.str_xcrdir        = os.path.expanduser(
                                                self.args.str_xcrdir
                                        )
        except:
            pass
        return len(self.args.str_xcrdir) and len(self.args.str_xcrfile)

    def housingDirs_create(self):
        """
        Create various directories to contain logging, data, and
        services.
        """
        # Probably not scrictly speaking necessary to create
        # dirs here, but for completeness sake...
        l_vars      : list  = [
                    'str_logDir',
                    'str_dataDir',
                    'str_patientDataDir',
                    'str_studyDataDir',
                    'str_seriesDataDir',
                    'str_servicesDir'
                ]
        for ns in [self, self.args]:
            for k,v in vars(ns).items():
                if k in l_vars: os.makedirs(v, exist_ok = True)

    def debugloggers_create(self):
        """
        Create the loggers.
        """
        if 'verbosity'      not in self.args:
            self.args.verbosity     = 0
        if 'b_debug'        not in self.args:
            self.args.b_debug       = False
        if 'str_debugFile'  not in self.args:
            self.args.str_debugFile = '/dev/null'
        self.str_debugFile      = '%s/smdb.log' % self.args.str_logDir
        self.dp                 = pfmisc.debug(
                                    verbosity   = int(self.args.verbosity),
                                    level       = 2,
                                    within      = self.__name__,
                                    debugToFile = self.args.b_debug,
                                    debugFile   = self.str_debugFile
                                )
        self.log                = self.dp.qprint

    def __init__(self, args):
        """
        Constructor for database. Core map element structures are defined.
        Call separate methods for actually creating file system paths.
        """

        self.__name__           : str   = 'smdb'
        self.args                       = args
        self.d_DICOM            : dict  = {}

        self.str_patientData    : str   = "patientData"
        self.str_studyData      : str   = "studyData"
        self.str_seriesData     : str   = "seriesData"

        if not hasattr(self.args, 'str_logDir'):
            self.args.str_logDir        = '/tmp/log'

        self.str_servicesBaseDir: str   = os.path.join(
                                            self.args.str_logDir,
                                            '../'
                                        )
        self.str_services       : str   = "services"
        self.str_swiftService   : str   = "swift.json"
        self.str_CUBEservice    : str   = "cube.json"
        self.str_PACSservice    : str   = "pacs.json"
        self.str_dataBaseDir    : str   = os.path.join(
                                            self.args.str_logDir,
                                            '../'
                                        )
        self.str_data           : str   = "data"

        if 'str_logDir' not in self.args:
            self.args.str_logDir        = '/tmp'
        self.str_patientDataDir : str   = os.path.join(
                                            self.args.str_logDir,
                                            self.str_patientData
                                        )
        self.str_studyDataDir   : str   = os.path.join(
                                            self.args.str_logDir,
                                            self.str_studyData
                                        )
        self.str_seriesDataDir  : str   = os.path.join(
                                            self.args.str_logDir,
                                            self.str_seriesData
                                        )
        self.str_servicesDir    : str   = os.path.join(
                                            self.str_servicesBaseDir,
                                            self.str_services
                                        )
        self.str_dataDir        : str   = os.path.join(
                                            self.str_dataBaseDir,
                                            self.str_data
                                        )

        self.models                     = SMDB_models()

        # The Info structures are the defaults/intialization parameters
        # that are used in each Meta structure.

        self.d_patientModel     : dict  = self.models.patientModel_get()
        self.d_patientMeta      : dict  = {}

        # Default study meta model
        self.d_studyModel       : dict  = self.models.studyModel_get()

        # Information relevant to all series of a study is stored in
        # the d_studyMeta
        self.d_studyMeta        : dict  = {}

        # Information relevant to a single series in the study is
        # stored in the d_studySeries
        self.d_studySeries      : dict  = {}

        # Default series meta info model
        self.d_seriesModel      : dict  = self.models.seriesModel_get()
        self.d_seriesMeta       : dict  = {}
        self.d_seriesImage      : dict  = {}

        # pudb.set_trace()
        self.housingDirs_create()
        self.debugloggers_create()

    def DICOMobj_set(self, d_DICOM) -> dict:
        self.d_DICOM        = d_DICOM.copy()
        return {
            'status'    : True,
            'd_DICOM'   : d_DICOM
        }

    def patientModel_init(self) -> dict:
        """
        Initialize a d_patientModel dictionary with information
        pertinent to the current series, as parsed from the
        d_DICOM object.
        """
        self.d_patientModel = self.models.patientModel_reset(self.d_patientModel)
        for key in self.d_patientModel.keys():
            if key in self.d_DICOM:
                self.d_patientModel[key]     = self.d_DICOM[key]
        self.d_patientModel['StudyList']     = []
        return self.d_patientModel

    def studyModel_init(self) -> dict:
        """
        Initialize a d_studyModel dictionary with information
        pertinent to the current study, as parsed from the
        d_DICOM object.
        """
        self.d_studyModel = self.models.studyModel_reset(self.d_studyModel)
        for key in self.d_studyModel.keys():
            if key in self.d_DICOM:
                self.d_studyModel[key]       = self.d_DICOM[key]
        # The meta/model was supposed to contain an explicit list
        # of SeriesInstanceUIDs -- however writing this information
        # to one file from multiple processes concurrently was not
        # safe.
        # self.d_studyModel['SeriesList']      = []
        return self.d_studyModel

    def seriesModel_init(self) -> dict:
        """
        Initialize a d_seriesModel dictionary with information
        pertinent to the current series, as parsed from the
        d_DICOM object.
        """
        self.d_seriesModel = self.models.seriesModel_reset(self.d_seriesModel)
        for key in self.d_seriesModel.keys():
            if key in self.d_DICOM:
                self.d_seriesModel[key]      = self.d_DICOM[key]
        return self.d_seriesModel

    def json_read(self, fromFile, intoObject):
        try:
            intoObject.update(json.load(fromFile))
            return True
        except:
            return False

    @retry(Exception, delay = 1, backoff = 2, max_delay = 4, tries = 10)
    def json_write(self, fromObject, intoFile):
        json.dump(fromObject, intoFile, indent = 4)

    def patientData_DBtablesGet(self):
        """
        Return the patientData table files
        """
        str_patientDataFile      : str = '%s/%s.json' % (
                                        self.str_patientDataDir,
                                        self.d_DICOM['PatientID']
                                    )
        return {
            'status'            : True,
            'patientDataFile'    : {
                'name'      : str_patientDataFile,
                'exists'    : os.path.isfile(str_patientDataFile)
            }
        }

    def patientData_process(self) -> dict:
        """
        Process the patient map data.
        """
        self.patientModel_init()
        d_patientTable      = self.patientData_DBtablesGet()
        if d_patientTable['patientDataFile']['exists']:
            with open(d_patientTable['patientDataFile']['name']) as fj:
                self.json_read(fj, self.d_patientMeta)
                # self.d_patientMeta   = json.load(fj)
            fj.close()
        if self.d_DICOM['PatientID'] not in self.d_patientMeta.keys():
            self.d_patientMeta[self.d_DICOM['PatientID']] =                  \
                self.d_patientModel
        if self.d_DICOM['StudyInstanceUID'] not in                          \
            self.d_patientMeta[self.d_DICOM['PatientID']]['StudyList']:
            self.d_patientMeta[self.d_DICOM['PatientID']]['StudyList'].      \
                append(
                    self.d_DICOM['StudyInstanceUID']
                )
            with open(d_patientTable['patientDataFile']['name'], 'w') as fj:
                self.json_write(self.d_patientMeta, fj)
            fj.close()
                # json.dump(self.d_patientMeta, fj, indent = 4)
        self.d_patientModel   = self.d_patientMeta[self.d_DICOM['PatientID']]
        return self.d_patientModel

    def studyData_DBtablesGet(self) -> dict:
        """
        Return the patientData table files
        """
        str_studySeries         : str = ''
        str_studyMetaFile       : str = '%s/%s-meta.json' % (
                                    self.str_studyDataDir,
                                    self.d_DICOM['StudyInstanceUID']
                                )
        str_seriesDir           : str = '%s/%s-series' % (
                                    self.str_studyDataDir,
                                    self.d_DICOM['StudyInstanceUID']
                                )
        if 'SeriesInstanceUID' in self.d_DICOM.keys():
            str_studySeries     = '%s/%s-meta.json' % (
                                    str_seriesDir,
                                    self.d_DICOM['SeriesInstanceUID']
                                )
            if not os.path.isdir(str_seriesDir): os.makedirs(str_seriesDir)
        else:
            str_studySeries     = "-not applicable-"
        return {
            'status'            : True,
            'studyDataDir'       : self.str_studyDataDir,
            'studySeriesDir'    : str_seriesDir,
            'studyMetaFile'     : {
                'name'              : str_studyMetaFile,
                'exists'            : os.path.isfile(str_studyMetaFile)
                                },
            'studySeriesFile'   : {
                'name'              : str_studySeries,
                'exists'            : os.path.isfile(str_studySeries)
                                }
        }

    def dictexpand(self, d) -> dict:
        """
        Expand a dictionary of key,value pairs:

            d[key] = value

        to

            d[key]  = {
                'value':    value
                'label':    key
            }

        and return result. This is mainly to reconstruct the structure to which
        some pypx utils expect a DICOM dictionary conformance.
        """
        d_ret       : dict  = {}
        d_ret       = {k:{'value': v, 'label': k} for (k,v) in d.items()}
        return d_ret

    def studyData_process(self) -> dict:
        """
        Process the study map data.

        This merely checks if study map and series-related map json
        files exist, and if not simply creates them.

        Since multiple processes might attempt this, this method attempts
        to be conceptually thread safe. If collisions occur, then no data
        should be lost since effectively only the same information is ever
        stamped/saved by each thread that might clobber this.
        """
        self.studyModel_init()
        d_studyTable    = self.studyData_DBtablesGet()
        if not d_studyTable['studyMetaFile']['exists']:
            self.d_studyMeta[self.d_DICOM['StudyInstanceUID']] =             \
                self.d_studyModel
            with open(d_studyTable['studyMetaFile']['name'], 'w') as fj:
                self.json_write(self.d_studyMeta, fj)
        else:
            with open(d_studyTable['studyMetaFile']['name']) as fj:
                self.json_read(fj, self.d_studyMeta)
        fj.close()
        if not d_studyTable['studySeriesFile']['exists']:
            with open(d_studyTable['studySeriesFile']['name'], 'w') as fj:
                self.json_write({
                    self.d_DICOM['StudyInstanceUID'] : {
                        'SeriesInstanceUID' :   self.d_DICOM['SeriesInstanceUID'],
                        'SeriesBaseDir'     :   self.str_outputDir,
                        'DICOM'             :   self.dictexpand(self.d_DICOM)
                    }
                }, fj)
        else:
            with open(d_studyTable['studySeriesFile']['name']) as fj:
                self.json_read(fj, self.d_studySeries)
        fj.close()
        return {
            'status'        : True,
            'd_studyMeta'   : self.d_studyMeta,
            'd_studySeries' : self.d_studySeries
        }

    def seriesData(self, str_table, *args)   -> dict:
        """
        This is the main entry point to performing set/get operations on the
        seriesData "tables".

        If called without any parameters other than the table name,

                d_data = seriesData('meta')

        the method will return the whole meta file contents within the 'meta'
        field return, i.e. d_data['meta']

        If called with a field name,

                d_data = seriesData('retrieve', 'NumberOfSeriesRelatedInstances')

        will return a status bool on whether or not that field exists in the
        table, and the contents of that specific field in a similarly named key,

                d_data['NumberOfSeriesRelatedIntances']

        If called with a field name and value for a table, set that specific
        field in the table file to the passed value, and return a named key
        with that value

                d_data = seriesData('retrieve', 'NumberOfSeriesRelatedInstances', 10)

                d_data['NumberOfSeriesRelatedIntances'] == 10

        NOTE:

            * A "write" to a seriesMetaFile is always followed by a read check!
              The post-write read check is to be a failsafe to catch any edge
              cases where a write *might* have gotten lost due to access
              collisions.

            * THIS METHOD IS A POTENTIAL BREAKPOINT IN HIGHLY ASYNCHRONOUS AND
              CONCURRENT CALLING ENVIRONMENTS!

              This method might attempt to write to the exact same *-meta.json file
              in a flood of storescp which might break.

        """

        # @retry(Exception, delay = 1, backoff = 2, max_delay = 4, tries = 10)
        def seriesData_write(str_filename, d_obj):
            """
            Multiprocess safe write
            """
            d_ret       : dict  = {
                'status'    : True,
                'error'     : ""
            }
            try:
                with open(str_filename, 'w') as fj:
                    # Lock it!
                    fcntl.flock(fj, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # Edit it!
                    self.json_write(d_obj, fj)
                    # Unlock it!
                    fcntl.flock(fj, fcntl.LOCK_UN)
            except Exception as e:
                d_ret['status']     = False
                d_ret['error']      = "Concurrent write failure!"
            return d_ret

        b_status        : bool          = False
        b_fileRead      : bool          = False
        b_canWrite      : bool          = True
        str_error       : str           = 'File does not exist at time of read'
        str_field       : str           = ""
        d_meta          : dict          = {}
        d_check         : dict          = {}
        d_ret           : dict          = {}
        d_seriesTable   : dict          = self.seriesData_DBtablesGet(
                SeriesInstanceUID       = self.d_DICOM['SeriesInstanceUID']
        )
        if len(args): str_field         = args[0]
        if d_seriesTable['status']:

            # The "read" from file...
            str_tableName   = 'series-%s' % str_table
            if d_seriesTable[str_tableName]['exists']:
                with open(d_seriesTable[str_tableName]['name']) as fj:
                    self.json_read(fj, d_meta)
                fj.close()
                b_fileRead                  = True
                if len(str_field):
                    if str_field in d_meta.keys():
                        b_status            = True
                        str_error           = ''
                        d_ret               = d_meta[str_field]
                    else:
                        b_status            = False
                        str_error           = "No field '%s' found" % str_field
                        d_ret               = {}
                else:
                    b_status                = True
                    str_field               = 'meta'
                    d_ret                   = d_meta

            # Optional "write" info to file... if file does not exist yet
            # this code will create it. It is possible that multiple processes
            # might collide here. We use fcntl to lock access, write, and then
            # release. If a file is locked, we wait a bit and try again.
            #
            # Only write to the file if there is a file content change
            #
            if len(args) == 2:
                value                   = args[1]
                if b_fileRead:
                    if str_field in d_meta.keys():
                        if d_meta[str_field] == value:
                            b_canWrite  = False
                if b_canWrite:
                    d_meta[str_field]       = value
                    str_fileName            = d_seriesTable[str_tableName]['name']
                    d_write                 = seriesData_write(str_fileName, d_meta)
                    b_status                = d_write['status']
                    if d_write['status']:
                        d_ret               = value
                    else:
                        str_error               = d_write['error'] + "\nConcurrency write error!"
                        d_check                 = self.seriesData(str_table, str_field)
                        while d_check[str_field] != value:
                            d_check             = self.seriesData(str_table, str_field)
                            time.sleep(0.5)

        return {
            'status'        : b_status,
            'error'         : str_error,
            str_field       : d_ret
        }

    def study_statusGet(self, str_StudyInstanceUID) -> dict:
        """
        Return the status of the passed StudyInstanceUID as well as
        an embedded list in the returned object of the contents of
        all the related study-series files.
        """
        b_status        : bool  = False

        d_DICOM         = self.d_DICOM.copy()
        self.d_DICOM['StudyInstanceUID'] = str_StudyInstanceUID
        d_studyTable    : dict  = self.studyData_DBtablesGet()
        self.d_DICOM    = d_DICOM.copy()

        b_status        = d_studyTable['studyMetaFile']['exists']
        return {
            'status'        : b_status,
            'studyTable'    : d_studyTable
        }

    def study_seriesListGet(self, str_StudyInstanceUID) -> dict:
        """
        Return a list of the series associated with given
        str_StudyInstanceUID
        """
        b_status            : bool  = False
        d_studyTable        : dict  = self.study_statusGet(str_StudyInstanceUID)
        d_series            : dict  = {}
        l_series            : list  = []
        str_studySeriesDir  : str = ''
        str_studySeriesFile : str = ''
        lstr_error          : list  = []
        if d_studyTable['status']:
            str_studySeriesDir  = d_studyTable['studyTable']['studySeriesDir']
            l_studySeries       = os.listdir(str_studySeriesDir)
            if len(l_studySeries):
                b_status        = True
            for f in l_studySeries:
                str_studySeriesFile = '%s/%s' % (str_studySeriesDir, f)
                with open(str_studySeriesFile, 'r') as fp:
                    try:
                        # d_series    = json.load(fp)
                        self.json_read(fp, d_series)
                    except:
                        b_status    = False
                        lstr_error.append(str_studySeriesFile)
                        # pudb.set_trace()
                        # pass
                fp.close()
                l_series.append(d_series[str_StudyInstanceUID]['SeriesInstanceUID'])
        return {
            'status'            : b_status,
            'seriesList'        : l_series,
            'JSONparseError'    : lstr_error
        }

    def study_seriesContainsVerify(self,
                    str_StudyInstanceUID,
                    str_SeriesInstanceUID,
                    b_verifySeriesInStudy) -> dict:
        """
        Check if the passed str_StudyInstanceUID contains
        the passed str_SeriesInstanceUID -- at least as far
        as the smdb is concerned.
        """
        d_status                    : dict      = {}
        d_status['status']                      = False
        d_status['error']                       = 'Study not found'
        d_status['study']                       = self.study_statusGet(
                                                    str_StudyInstanceUID
                                                )
        d_status['study']['state']              = 'StudyNotFound'
        d_status['series']                      = {}

        if d_status['study']['status'] or not b_verifySeriesInStudy:
            if d_status['study']['status']:
                d_status['study']['state']  = 'StudyOK'
            d_status['error']               = 'Series not found'
            d_status['study']['seriesListInStudy']   = \
                                            self.study_seriesListGet(
                                                str_StudyInstanceUID
                                            )
            d_status['series']              = self.series_statusGet(
                                                str_SeriesInstanceUID
                                            )
            d_status['series']['state']     = 'SeriesNotFound'
            if d_status['series']['status']:
                d_status['error']           = ''
                d_status['series']['state'] = 'SeriesMapMetaOK'
                d_status['status']          = True
            if str_SeriesInstanceUID in d_status['study']\
                                        ['seriesListInStudy']\
                                        ['seriesList']:
                d_status['study']['state'] = 'StudyContainsSeriesOK'
            else:
                d_status['study']['state'] = 'StudyDoesNotContainSeries'
                d_status['study']['status']= False
        return d_status

    def series_receivedAndRequested(self, str_SeriesInstanceUID) -> dict:
        """
        Return a dictionary with requested / received / packed file count.
        """
        d_count                 : dict  = {}
        d_count['received']     = self.series_receivedFilesCount(
                                        str_SeriesInstanceUID
                                )
        d_count['requested']    = self.series_requestedFilesCount(
                                        str_SeriesInstanceUID
                                )
        d_count['packed']       = self.series_packedFilesCount(
                                        str_SeriesInstanceUID
                                )
        d_count['pushed']       = self.series_dbFilesCount(
                                        str_SeriesInstanceUID, 'push'
                                )
        d_count['registered']    = self.series_dbFilesCount(
                                        str_SeriesInstanceUID, 'register'
                                )
        if d_count['received']['count'] >= d_count['requested']['count']:
            d_count['state']    = 'ImagesAllReceivedOK'
            d_count['status']   = True
        elif not d_count['received']['count']:
            d_count['state']    = 'NoImagesReceived'
            d_count['status']   = False
        else:
            d_count['state']    = 'ImagesInFlight'
            d_count['status']   = False
        if d_count['requested']['count'] == -1:
            d_count['state']    = 'ImagesReceiveCountOK'
            d_count['status']   = True
        if d_count['pushed']['count'] >= 1:
            d_count['state']    = 'ImagesPushedOK'
            d_count['status']   = True
        if d_count['registered']['count'] >= 1:
            d_count['state']    = 'ImagesRegisteredOK'
            d_count['status']   = True
        return d_count

    def series_statusGet(self, str_SeriesInstanceUID) -> dict:
        """
        Return the status of the passed SeriesInstanceUID.
        """
        b_status        : bool  = False
        d_seriesTable   : dict  = self.seriesData_DBtablesGet(
                            SeriesInstanceUID = str_SeriesInstanceUID
        )
        b_status        = d_seriesTable['series-meta']['exists']
        return {
            'status'        : b_status,
            'seriesTable'   : d_seriesTable
        }

    def series_requestedFilesCount(self, str_SeriesInstanceUID) -> dict:
        """
        Return the requested files count for a given series.

        This assumes that the series was received as the result of a
        DICOM movescu which allows the requestor to ask the PACS for
        the NumberOfSeriesRelatedInstances. If a DICOM series was simply
        pushed directly to the listener, this information is not
        available.
        """
        b_status        : bool  = False
        d_DICOM         = self.d_DICOM.copy()
        count           = -1
        self.d_DICOM['SeriesInstanceUID'] = str_SeriesInstanceUID
        d_get           : dict  = \
            self.seriesData('retrieve', 'NumberOfSeriesRelatedInstances')
        self.d_DICOM    = d_DICOM.copy()
        b_status        = d_get['status']
        if b_status:
            count       = int(d_get['NumberOfSeriesRelatedInstances'])
        return {
            'status'    :   b_status,
            'count'     :   count
        }

    def series_receivedFilesCount(self, str_SeriesInstanceUID) -> dict:
        """
        Return the number of actual received files by "counting" the
        object json files for a given series.

        Note this returns the count in the seriesDataDir for a given
        series, which assumes that a file has been processed and
        recorded -- this does not return the count of files in the
        packed location.
        """
        b_status            : bool  = False
        l_files             : list  = []
        str_processedDir    : str   = os.path.join( self.args.str_logDir,
                                                    self.str_seriesData,
                                                    str_SeriesInstanceUID) + '-img'
        if os.path.isdir(str_processedDir):
            b_status        = True
            l_files         : list  = [
                f for f in os.listdir(str_processedDir)
                        if os.path.isfile(os.path.join(str_processedDir, f))
            ]
        return {
            'status'    : b_status,
            'count'     : len(l_files)
        }

    def series_dbFilesCount(self, str_SeriesInstanceUID, str_type) -> dict:
        """
        Return the number of actual str_type files by "counting" the
        object json files for a given series.

        Note this returns the count in the seriesDataDir for a given
        series, which assumes that a file has been processed and
        recorded -- this does not return the count of files in the
        packed location.
        """
        b_status            : bool  = False
        count               : int   = 0
        l_files             : list  = []
        str_seriesDir       : str   = os.path.join( self.args.str_logDir,
                                                    self.str_seriesData)
        if os.path.isdir(str_seriesDir):
            l_files         : list  = [
                f for f in os.listdir(str_seriesDir)
                        if re.match(r'%s-%s.json' %(str_SeriesInstanceUID, str_type), f)
            ]
            b_status        = bool(len(l_files))
            if b_status:
                """
                A true status simply indicates the entire series has been processed.
                In order to remain consistent with the other count measures, we set
                the 'count' to number of packed files.
                """
                d_packed    = self.series_packedFilesCount(str_SeriesInstanceUID)
                if d_packed['status']:
                    count       = d_packed['count']
                else:
                    b_status    = False
                    count       = -1
        return {
            'status'    : b_status,
            'count'     : count
        }


    def series_packedFilesCount(self, str_SeriesInstanceUID) -> dict:
        """
        Return the number of actual packed files by "counting" the
        image DICOMS files for a given series.

        """
        b_status            : bool  = False
        l_files             : list  = []
        d_imageDir          : dict  = self.imageDirs_getOnSeriesInstanceUID(str_SeriesInstanceUID)
        if d_imageDir['status']:
            str_processedDir    : str   = d_imageDir[str_SeriesInstanceUID]
            if os.path.isdir(str_processedDir):
                b_status        = True
                l_files         : list  = [
                    f for f in os.listdir(str_processedDir)
                            if os.path.isfile(os.path.join(str_processedDir, f))
                ]
        return {
            'status'    : b_status,
            'count'     : len(l_files)
        }

    def seriesData_DBtablesGet(self, **kwargs) -> dict:
        """
        Return the location in the DB (i.e. the file system) where
        the map information for a given SeriesInstanceUID is stored.
        """
        b_status                    : bool  = False
        str_SeriesInstanceUID       : str   = ''
        str_outputFile              : str   = ''
        str_seriesBaseDir           : str   = ''
        str_seriesMetaFile          : str   = ''
        str_seriesRetrieveFile      : str   = ''
        str_seriesImageFile         : str   = ''
        str_seriesPushFile          : str   = ''
        str_seriesPackFile          : str   = ''
        str_seriesRegisterFile      : str   = ''
        for k, v in kwargs.items():
            if k == 'SeriesInstanceUID' :   str_SeriesInstanceUID   = v
            if k == 'outputFile'        :   str_outputFile          = v
        if len(str_SeriesInstanceUID):
            b_status                    = True
            str_seriesBaseDir           = '%s/%s-img'               % \
                    (self.str_seriesDataDir,
                     str_SeriesInstanceUID)
            str_seriesMetaFile          = '%s/%s-meta.json'         % \
                    (self.str_seriesDataDir,
                     str_SeriesInstanceUID)
            str_seriesRetrieveFile      = '%s/%s-retrieve.json'     % \
                    (self.str_seriesDataDir,
                     str_SeriesInstanceUID)
            str_seriesPushFile          = '%s/%s-push.json'         % \
                    (self.str_seriesDataDir,
                     str_SeriesInstanceUID)
            str_seriesPackFile          = '%s/%s-pack.json'         % \
                    (self.str_seriesDataDir,
                     str_SeriesInstanceUID)
            str_seriesRegisterFile      = '%s/%s-register.json'     % \
                    (self.str_seriesDataDir,
                     str_SeriesInstanceUID)
            if len(str_outputFile):
                str_seriesImageFile    = '%s/%s.json'               % (
                    str_seriesBaseDir, str_outputFile
                )
        return {
            'status'                : b_status,
            'seriesBaseDir'         : {
                'name'      :   str_seriesBaseDir,
                'exists'    :   os.path.isdir(str_seriesBaseDir)
            },
            'series-meta'           : {
                'name'      :   str_seriesMetaFile,
                'exists'    :   os.path.isfile(str_seriesMetaFile)
            },
            'series-retrieve'       : {
                'name'      :   str_seriesRetrieveFile,
                'exists'    :   os.path.isfile(str_seriesRetrieveFile)
            },
            'series-push'           : {
                'name'      :   str_seriesPushFile,
                'exists'    :   os.path.isfile(str_seriesPushFile)
            },
            'series-pack'           : {
                'name'      :   str_seriesPackFile,
                'exists'    :   os.path.isfile(str_seriesPackFile)
            },
            'series-register'       : {
                'name'      :   str_seriesRegisterFile,
                'exists'    :   os.path.isfile(str_seriesRegisterFile)
            }
        }

    def seriesData_process(self, **kwargs) -> dict:
        """
        Process the series map data.
        """

        def seriesTables_get(str_outputFile) -> dict:
            """
            (compare this method to the first part of the studyData_process())

            * Check on the housing directory for the JSON image representations and
              create if necessary;

            * Return the series tables (data)

            * On return, the self.d_seriesMeta is existant.
            """
            nonlocal d_seriesTables
            d_seriesTables = self.seriesData_DBtablesGet(
                    outputDir           = str_outputDir,
                    outputFile          = str_outputFile,
                    SeriesInstanceUID   = self.d_DICOM['SeriesInstanceUID'],
                    **kwargs
            )
            if not d_seriesTables['seriesBaseDir']['exists']:
                try:
                    os.makedirs(
                            d_seriesTables['seriesBaseDir']['name'],
                            exist_ok = True
                    )
                    d_seriesTables['seriesBaseDir']['exists'] = os.path.isdir(
                        d_seriesTables['seriesBaseDir']['name']
                    )
                except Exception as e:
                    d_seriesTables['error']     = 'Some error occured in output dir creation.'
                    d_seriesTables['status']    = False
            if d_seriesTables['series-meta']['exists']:
                with open(d_seriesTables['series-meta']['name']) as fj:
                    self.json_read(fj, self.d_seriesMeta)
                fj.close()
            else:
                d_seriesTables['status']    = False
            d_seriesTables['outputFile']    = str_outputFile
            return d_seriesTables

        def seriesData_singleImageFile_init(d_seriesTables)  -> dict:
            """
            Initialize some data within a single JSON image file.
            """
            str_seriesInstanceUID : str     = self.d_DICOM['SeriesInstanceUID']

            self.d_seriesImage.clear()

            if d_seriesTables['series-image']['exists']:
                with open(d_seriesTables['series-image']['name']) as fj:
                    self.json_read(fj, self.d_seriesImage)
                fj.close()

            if str_seriesInstanceUID not in self.d_seriesImage.keys():
                try:
                    self.d_seriesImage[str_seriesInstanceUID] =             \
                        self.d_seriesMeta[str_seriesInstanceUID].copy()
                except Exception as e:
                    print("An error occurred with the seriesMeta data")
                    print("self.d_seriesMeta = %s" % self.d_seriesMeta)
            self.d_seriesImage[str_seriesInstanceUID]['outputFile'] =       \
                    d_seriesTables['outputFile']
            if 'imageObj' not in self.d_seriesImage[str_seriesInstanceUID]:
                self.d_seriesImage[str_seriesInstanceUID]['imageObj'] = {}

            return d_seriesTables

        def seriesData_singleImageFile_update(d_seriesTables) -> dict:
            """
            Update data specific to *this* image file, only if this output
            file is not already present in the JSON dictionary.

            Return False if no updates made, else True
            """
            b_updatesMade   : bool  = False
            try:
                if self.d_seriesImage[self.d_DICOM['SeriesInstanceUID']]['outputFile'] not in                                      \
                    self.d_seriesImage[self.d_DICOM['SeriesInstanceUID']]           \
                                                    ['imageObj'].keys():
                    ofs = os.stat('%s/%s' % (str_outputDir, str_outputFile))
                    self.d_seriesImage[self.d_DICOM['SeriesInstanceUID']]['imageObj'] \
                                            [str_outputFile] =                      \
                        {k.replace('st_', '') :                                     \
                            ('%s' % datetime.datetime.fromtimestamp(getattr(ofs, k))\
                            if 'time' in k and not 'ns' in k                        \
                                else getattr(ofs, k))                               \
                                    for k in dir(ofs)                               \
                                        if 'st' in k and not 'ns' in k and not '__'  in k}
                    self.d_seriesImage[self.d_DICOM['SeriesInstanceUID']]['imageObj'] \
                                            [str_outputFile]['FSlocation'] =        \
                                                '%s/%s' % (str_outputDir, str_outputFile)
                    b_updatesMade   = True
                else:
                    self.d_seriesModel     = self.d_seriesImage[self.d_DICOM['SeriesInstanceUID']]
            except:
                # pudb.set_trace()
                b_updatesMade   = False
            return {
                'status'    : b_updatesMade,
                'image'     : self.d_seriesImage
            }

        def seriesData_singleImageFile_save(d_update)  -> dict:
            """
            Save the updated dictionary.
            """
            nonlocal d_seriesTables
            if d_update['status']:
                with open(d_seriesTables['series-image']['name'], 'w') as fj:
                    self.json_write(d_update['image'], fj)
                fj.close()
            return {
                'status'    : d_update['status'],
                'update'    : d_update
            }

        str_outputDir   : str       = self.str_outputDir
        str_outputFile  : str       = self.str_outputFile
        d_seriesMeta    : dict      = {}
        d_seriesTables  : dict      = {}
        d_seriesInfo    : dict      = {}
        d_ret           : dict      = {}

        for k, v in kwargs.items():
            if k == 'outputDir'     : str_outputDir     = v
            if k == 'outputFile'    : str_outputFile    = v

        # Initialize the seriesModel (as modeled by the constructor)
        self.seriesModel_init()

        # Write the seriesModel data to the series meta file --
        # This is a potential bottleneck/collision as mulitple
        # processes might attempt to write to the same file, so
        # we place in a while/backoff/timeout
        d_seriesInfo['status'] = False
        while not d_seriesInfo['status']:
            d_seriesInfo    = self.seriesData(
                                        'meta',
                                        self.d_DICOM['SeriesInstanceUID'],
                                        self.d_seriesModel
                            )


        # Now create, for each image file, a series map entry
        d_ret = seriesData_singleImageFile_save(
            seriesData_singleImageFile_update(
                seriesData_singleImageFile_init(
                    seriesTables_get(str_outputFile)
                )
            )
        )

        return d_ret

    def mapsUpdateForFile(self, str_file):
        """
        NOTE:
            *   This is typically called once per DICOM file, most often by a
                repack.py process as it handles DICOM files received from a
                storescp and repacks them. The mapsUpdate is performed relative
                to the repacked location.

            *   When called via storescp, particular care must be taken to
                avoid collisions writing to the same file! This is somewhat
                mitigated by the _process() routines only writing to a file
                if it does not already exist. Nonetheless, collisions might
                still occur, and an extra layer in the JSON file writing is
                used with a @retry decorator and backoff on the write.

            *   Due also to the highly parallel nature of storescp handling,
                maps _might_ not be complete -- particularly on less powerful
                machines. In that case a mapsCheck() can be called.

        PRECONDITIONS:
            *   self.d_DICOM exists and has been set.
        """
        b_status                :   bool    = False
        d_patientData_process   :   dict    = {}
        d_studyData_process     :   dict    = {}
        d_seriesData_process    :   dict    = {}

        # Store the <str_file>, i.e. the file location where the DICOM
        # has been repacked.
        self.str_outputDir      = os.path.dirname(str_file)
        self.str_outputFile     = os.path.basename(str_file)

        # Only process files that actually exist!
        if os.path.isfile(str_file):
            # pudb.set_trace()
            d_patientData_process    = self.patientData_process()
            d_studyData_process      = self.studyData_process()
            d_seriesData_process     = self.seriesData_process()

        return {
            'status'                : b_status,
            'd_patientData_process' : d_patientData_process,
            'd_studyData_process'   : d_studyData_process,
            'd_seriesData_process'  : d_seriesData_process
        }

    def endOfStudy(self, str_xcrdir):
        """
        Perform an end-of-study event
        """
        str_eosfile = '/tmp/eos.txt'
        str_message = 'EOS for dir %s on %s' % (
                            str_xcrdir,
                            datetime.datetime.now()
                        )
        with open(str_eosfile, 'a') as f:
            f.write(str_message)
        return {
            'method'            : inspect.stack()[0][3],
            'status'            : True,
            'message'           : str_message
        }

    def seriesDirLocation_get(self, **kwargs) -> dict:
        """
        Return a list of dictionaries with the results of hits on series'
        directory locations that correspond to the search parameters of
        **kwargs.
        """
        pudb.set_trace()
        d_ret                   : dict  = {}
        str_seriesInstanceUID   : str   = ""
        if len(self.args.SeriesInstanceUID):
            str_seriesInstanceUID       = self.args.SeriesInstanceUID
        d_seriesStatus                  = self.series_statusGet(str_seriesInstanceUID)
        d_seriesReceivedAndRequested    = self.series_receivedAndRequested(str_seriesInstanceUID)

    def imageDirs_getOnPatientID(self, astr_PatientID) -> dict:
        """
        Return a structure that contains a list of all directories containing
        DICOM files for a given PatientID.
        """
        d_ret               : dict  = {}
        b_status            : bool  = False
        l_studies           : list  = []
        d_series            : dict  = {}
        d_imageDirs         : dict  = {}
        d_imageInfo         : dict  = {}
        d_patientData       : dict  = {}
        str_patientDataFile : str   = '%s/%s.json' % (self.str_patientDataDir, astr_PatientID)
        str_imageFile       : str   = ""
        str_imageObj        : str   = ""
        str_imageLocation   : str   = ""
        str_imageDataDir    : str   = ""
        str_imageDir        : str   = ""

        if os.path.isfile(str_patientDataFile):
            with open(str_patientDataFile) as fp:
                self.json_read(fp, d_patientData)
            fp.close()
            l_studies       = d_patientData[astr_PatientID]['StudyList']
            for study in l_studies:
                d_series[study] = [os.path.splitext(f)[0] for f in os.listdir(
                                                '%s/%s-series' % (self.str_studyDataDir, study)
                                                        )]
                d_imageDirs[study]  = []
                for series in d_series[study]:
                    str_imageDataDir    = '%s/%s-img' % (self.str_seriesDataDir, series)
                    str_imageFile       = os.listdir(str_imageDataDir)[0]
                    if os.path.isfile('%s/%s' % (str_imageDataDir, str_imageFile)):
                        with open('%s/%s' % (str_imageDataDir, str_imageFile)) as fp:
                            self.json_read(fp, d_imageInfo)
                        fp.close()
                        str_imageObj        = os.path.splitext(str_imageFile)[0]
                        str_imageLocation   = d_imageInfo[series]['imageObj'][str_imageObj]['FSlocation']
                        str_imageDir        = os.path.dirname(str_imageLocation)
                        d_imageDirs[study].append(str_imageDir)
                b_status    = True

        d_ret = {
            'status'        : b_status,
            'PatientID'     : astr_PatientID,
            'd_series'      : d_series,
            'd_imageDirs'   : d_imageDirs
        }
        return d_ret

    def imageDirs_getOnSeriesInstanceUID(self, astr_SeriesInstanceUID) -> dict:
        """
        Return a structure that contains a list of all directories containing
        DICOM files for a given SeriesInstanceUID
        """
        d_ret               : dict  = {}
        b_status            : bool  = False
        d_imageInfo         : dict  = {}
        str_imageFile       : str   = ""
        str_imageObj        : str   = ""
        str_imageLocation   : str   = ""
        str_imageDataDir    : str   = ""
        str_imageDir        : str   = "Non-existant meta directory: "
        str_error           : str   = ""

        str_imageDataDir    = '%s/%s-img' % (
                                    self.str_seriesDataDir,
                                    astr_SeriesInstanceUID
                            )
        str_imageDir        += str_imageDataDir
        if os.path.isdir(str_imageDataDir):
            str_imageFile       = os.listdir(str_imageDataDir)[0]
            try:
                if os.path.isfile('%s/%s' % (str_imageDataDir, str_imageFile)):
                    with open('%s/%s' % (str_imageDataDir, str_imageFile)) as fp:
                        self.json_read(fp, d_imageInfo)
                    fp.close()
                    str_imageObj        = os.path.splitext(str_imageFile)[0]
                    str_imageLocation   = d_imageInfo[astr_SeriesInstanceUID][
                                                    'imageObj'][str_imageObj]['FSlocation']
                    str_imageDir        = os.path.dirname(str_imageLocation)
                    b_status            = True
            except Exception as e:
                str_error               = '%s' % e

        d_ret = {
            'status'                    : b_status,
            'error'                     : str_error,
            astr_SeriesInstanceUID      : str_imageDir
        }
        return d_ret

    def mapsUpdateForPatient_do(self, astr_PatientID) -> dict:
        """
        Update all the DB data for a given PatientID.

        This method is used most often to "correct" or "pick up"
        any DB entries that might have been lost "in the wash"
        during a high load of asynchronous storescp originating
        pack operations.

        Anecdotally it has been observed that while all image files
        are correctly repacked in their image directories, the logging
        of these files in the smdb catalogue can sometimes miss a few
        individual image cataloging here and there.

        This method redoes the cataloguing for a Patient to refresh
        all the internal tracking.
        """
        b_status        : bool  = False
        d_ret           : dict  = {}
        d_imageInfo     : dict  = {}
        l_studies       : list  = []
        l_seriesFiles   : list  = []
        str_seriesDir   : str   = ""

        d_imageInfo             = self.imageDirs_getOnPatientID(astr_PatientID)
        d_ret['d_imageInfo']    = d_imageInfo
        b_status                = d_imageInfo['status']
        d_ret['status']         = b_status
        if b_status:
            l_studies           = list(d_imageInfo['d_imageDirs'].keys())
            for study in l_studies:
                for str_seriesDir in d_imageInfo['d_imageDirs'][study]:
                    l_images    = ['%s/%s' % (str_seriesDir, f) for f in os.listdir(str_seriesDir)]
                    for self.args.str_xcrdirfile in l_images:
                        d_ret[self.args.str_xcrdirfile]     = self.mapsUpdateForFile_do()
        return d_ret

    def service_keyAccess(self, astr_service) -> dict:
        """
        This method saves the details of accessing a given service
        instance as a named key. Three services are supported:

            * 'PACS'
            * 'swift'
            * 'CUBE'

        The point/idea of these services is to store a short hand for
        parameters useful to some upstream services, for example:

            * px-find ...
            * px-push ...
            * px-register ...

        For 'PACS':

            {
                "<keyname>":  {
                        "aet":      "<AETitle>",
                        "aec":      "<CalledAETitle>",
                        "ip":       "<PACSip>",
                        "port":     "<PACSport>",
                    }
            }

        For 'swift':

            {
                "<keyname>":  {
                        "ip":       "<IPofSwiftServer>",
                        "port":     "<PortOfSwiftServer>",
                        "login":    "<username>:<passwd>"
                    }
            }

        For 'CUBE':

            {
                "<keyname>":  {
                        "url":      "<URLofCUBEAPI>",
                        "username": "<CUBEusername>",
                        "password": "<CUBEuserpasswd>"
                    }
            }

        NOTE:

            * Currently no models or error checking on the passed CLI
                <self.args.str_actionArgs>!!!

        """
        d_ret           : dict  = {}
        d_service       : dict  = {}
        d_update        : dict  = {}
        d_ret['status']         = False

        if astr_service.lower().strip() == 'swift':
            str_service : str   = os.path.join(
                                    self.str_servicesDir,
                                    self.str_swiftService
                                )
        if astr_service.lower().strip() == 'cube':
            str_service : str   = os.path.join(
                                    self.str_servicesDir,
                                    self.str_CUBEservice
                                )
        if astr_service.lower().strip() == 'pacs':
            str_service: str   = os.path.join(
                                    self.str_servicesDir,
                                    self.str_PACSservice
                                )
        if os.path.isfile(str_service):
            with open(str_service) as fj:
                self.json_read(fj, d_service)
            fj.close()
            d_ret['status']     = True
            d_ret[astr_service] = d_service

        if hasattr(self.args, 'str_actionArgs'):
            if len(self.args.str_actionArgs):
                try:
                    d_update   = json.loads(self.args.str_actionArgs)
                    d_service.update(d_update)
                    with open(str_service, 'w') as fj:
                        self.json_write(d_service, fj)
                    fj.close()
                    d_ret[astr_service]     = d_service
                    d_ret['status']         = True
                except:
                    d_ret['status']         = False

        return d_ret

    def mapsUpdateForFile_do(self) -> dict:
        d_run   : dict  = {}
        # pudb.set_trace()
        if self.fileSpec_process():
            d_DICOMread     = repack.Process.DICOMfile_read(
                                file = '%s/%s' % (
                                    self.args.str_xcrdir,
                                    self.args.str_xcrfile
                                )
                            )
            if d_DICOMread['status']:
                self.DICOMobj_set(d_DICOMread['d_DICOM']['d_dicomSimple'])
                d_run['status'] = True
                d_run['mapsUpdateForFile'] = \
                    self.mapsUpdateForFile('%s/%s' % (
                                self.args.str_xcrdir,
                                self.args.str_xcrfile
                            )
                    )
            d_DICOM                 = d_DICOMread['d_DICOM']
            d_DICOM['dcm']          = "Not JSON serializable"
            d_DICOM['d_dcm']        = "Not JSON serializable"
            d_DICOM['d_dicom']      = "Not JSON serializable"
            # d_run['d_DICOMread']    = d_DICOMread
        return d_run

    def run(self) -> dict:
        """
        Generic run handler -- mostly called when an "action" needs
        to be processed in relation to a specific DICOM file.

        The DICOM file to process is typically passed by a storescu
        process as #p/#f
        """

        def seriesDirLocation_doget() -> dict:
            nonlocal d_run
            d_run['seriesDirLocation'] = self.seriesDirLocation_get()
            return d_run

        def DBtablesGet_do() -> dict:
            nonlocal d_run
            if self.fileSpec_process():
                d_DICOMread     = repack.Process.DICOMfile_read(
                                    file = '%s/%s' % (
                                        self.args.str_xcrdir,
                                        self.args.str_xcrfile
                                    )
                                )
                if d_DICOMread['status']:
                    self.DICOMobj_set(d_DICOMread['d_DICOM']['d_dicomSimple'])
                    d_run['status'] = True
                    if 'eries' in self.args.str_action:
                        d_run['seriesData_DBtablesGet']  = \
                            self.seriesData_DBtablesGet(
                                SeriesInstanceUID   = self.d_DICOM['SeriesInstanceUID'],
                                outputFile          = self.args.str_xcrfile
                            )
                    if 'tudy' in self.args.str_action:
                        d_run['studyData_DBtablesGet']   = \
                            self.studyData_DBtablesGet()
                    if 'atient' in self.args.str_action:
                        d_run['patientData_DBtablesGet'] = \
                            self.patientData_DBtablesGet()
            if not d_run['status']:
                d_run['error_message']  = \
                    'Unable to process a valid DICOM %s/%s' % (
                        self.args.str_xcrdir,
                        self.args.str_xcrfile
                    )
            return d_run

        d_run   = {
            'status'    : False
        }

        # pudb.set_trace()
        if 'mapsUpdateForFile'          in self.args.str_action:
            d_run = self.mapsUpdateForFile_do()
        if 'imageDirsPatientID'         in self.args.str_action:
            d_run = self.imageDirs_getOnPatientID(self.args.str_actionArgs)
        if 'imageDirsSeriesInstanceUID' in self.args.str_action:
            d_run = self.imageDirs_getOnSeriesInstanceUID(self.args.str_actionArgs)
        if 'mapsUpdateForPatient'       in self.args.str_action:
            d_run = self.mapsUpdateForPatient_do(self.args.str_actionArgs)
        if 'seriesDirLocation'          in self.args.str_action:
            d_run = seriesDirLocation_doget()
        if 'DBtablesGet'                in self.args.str_action:
            d_run = DBtablesGet_do()
        if 'swift'                      in self.args.str_action:
            d_run = self.service_keyAccess('swift')
        if 'CUBE'                       in self.args.str_action:
            d_run = self.service_keyAccess('CUBE')
        if 'PACS'                       in self.args.str_action:
            d_run = self.service_keyAccess('PACS')

        if not d_run['status']:
            d_run['error']  = "An error occurred while executing '%s'" %    \
                self.args.str_action
        return d_run



