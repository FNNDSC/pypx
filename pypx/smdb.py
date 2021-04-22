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

    <dataLogDir>/patientMap/patientMap-<%PatientID>.json
    <dataLogDir>/studyMap/studyMap-<%StudyInstanceUID>.json
    <dataLogDir>/seriesMap/<%SeriesInstanceUID>/seriesMap-%%imageFile.json

NB: This module is currently NOT THREAD SAFE as of April 2021! Collisions
occur if multiple jobs try and read/write to the map files concurrently which
happens if scheduled in an async xinetd storescp pipeline.

Typical safe calling spec for an xinetd controlled storescp is

    storescp -od /tmp/data -pm -sp \
        -xcr "/home/rudolphpienaar/src/pypx/bin/px-repack
              --xcrdir #p --xcrfile #f --verbosity 0"       \
        11113

"""

import  os
import  json
import  pudb
import  datetime

from    retry           import  retry
from    pypx            import  repack
import  pfmisc
import  inspect

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
        maps.
        """
        # Probably not scrictly speaking necessary to create
        # dirs here, but for completeness sake...
        l_vars      : list  = [
                    'str_logDir',
                    'str_dataDir',
                    'str_patientMapDir',
                    'str_studyMapDir',
                    'str_seriesMapDir'
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

        self.str_patientMap     : str   = "patientMap"
        self.str_studyMap       : str   = "studyMap"
        self.str_seriesMap      : str   = "seriesMap"

        if 'str_logDir' not in self.args:
            self.args.str_logDir        = '/tmp'
        self.str_patientMapDir  : str   = os.path.join(
                                            self.args.str_logDir,
                                            self.str_patientMap
                                        )
        self.str_studyMapDir    : str   = os.path.join(
                                            self.args.str_logDir,
                                            self.str_studyMap
                                        )
        self.str_seriesMapDir   : str   = os.path.join(
                                            self.args.str_logDir,
                                            self.str_seriesMap
                                        )


        self.d_patientMap       : dict  = {}
        self.d_patientInfo      : dict  = {
            'PatientID'                         : 'Not defined',
            'PatientName'                       : 'Not defined',
            'PatientAge'                        : 'Not defined',
            'PatientSex'                        : 'Not defined',
            'PatientBirthDate'                  : 'Not defined'        }

        self.d_studyMap         : dict  = {}
        self.d_studyInfo        : dict  = {
            'PatientID'                         : 'Not defined',
            'StudyDescription'                  : 'Not defined',
            'StudyDate'                         : 'Not defined',
            'PerformedStationAETitle'           : 'Not defined'
        }

        self.d_seriesMap        : dict  = {}
        self.d_seriesInfo       : dict  = {
            'StudyInstanceUID'                  : 'Not defined',
            'SeriesDescription'                 : 'Not defined',
            'SeriesDate'                        : 'Not defined',
            'Modality'                          : 'Not defined'
        }
        self.debugloggers_create()

    def DICOMobj_set(self, d_DICOM) -> dict:
        self.d_DICOM        = d_DICOM.copy()
        return {
            'status'    : True,
            'd_DICOM'   : d_DICOM
        }

    def patientInfo_init(self) -> dict:
        """
        Initialize a d_patientInfo dictionary with information
        pertinent to the current series, as parsed from the
        d_DICOM object.
        """
        for key in self.d_patientInfo.keys():
            if key in self.d_DICOM:
                self.d_patientInfo[key]     = self.d_DICOM[key]
        self.d_patientInfo['StudyList']     = []
        return self.d_patientInfo

    def studyInfo_init(self) -> dict:
        """
        Initialize a d_studyInfo dictionary with information
        pertinent to the current study, as parsed from the
        d_DICOM object.
        """
        for key in self.d_studyInfo.keys():
            if key in self.d_DICOM:
                self.d_studyInfo[key]       = self.d_DICOM[key]
        self.d_studyInfo['SeriesList']      = []
        return self.d_studyInfo

    def seriesInfo_init(self) -> dict:
        """
        Initialize a d_seriesInfo dictionary with information
        pertinent to the current series, as parsed from the
        d_DICOM object.
        """
        for key in self.d_seriesInfo.keys():
            if key in self.d_DICOM:
                self.d_seriesInfo[key]      = self.d_DICOM[key]
        self.d_seriesInfo['imageObj']       = {}
        return self.d_seriesInfo

    def json_read(self, fromFile, intoObject):
        try:
            intoObject.update(json.load(fromFile))
            return True
        except:
            return False

    @retry(Exception, delay = 1, backoff = 2, max_delay = 4, tries = 10)
    def json_write(self, fromObject, intoFile):
        json.dump(fromObject, intoFile, indent = 4)

    def patientMap_DBtablesGet(self):
        """
        Return the patientMap table files
        """
        str_patientMapFile      : str = '%s/%s.json' % (
                                        self.str_patientMapDir,
                                        self.d_DICOM['PatientID']
                                    )
        return {
            'status'            : True,
            'patientMapFile'    : {
                'name'      : str_patientMapFile,
                'exists'    : os.path.isfile(str_patientMapFile)
            }
        }

    def patientMap_process(self) -> dict:
        """
        Process the patient map data.
        """
        self.patientInfo_init()
        d_patientTable      = self.patientMap_DBtablesGet()
        if d_patientTable['patientMapFile']['exists']:
            with open(d_patientTable['patientMapFile']['name']) as fj:
                self.json_read(fj, self.d_patientMap)
                # self.d_patientMap   = json.load(fj)
            fj.close()
        if self.d_DICOM['PatientID'] not in self.d_patientMap.keys():
            self.d_patientMap[self.d_DICOM['PatientID']] =                  \
                self.d_patientInfo
        if self.d_DICOM['StudyInstanceUID'] not in                          \
            self.d_patientMap[self.d_DICOM['PatientID']]['StudyList']:
            self.d_patientMap[self.d_DICOM['PatientID']]['StudyList'].      \
                append(
                    self.d_DICOM['StudyInstanceUID']
                )
            with open(d_patientTable['patientMapFile']['name'], 'w') as fj:
                self.json_write(self.d_patientMap, fj)
                # json.dump(self.d_patientMap, fj, indent = 4)
        self.d_patientInfo   = self.d_patientMap[self.d_DICOM['PatientID']]

    def studyMap_DBtablesGet(self):
        """
        Return the patientMap table files
        """
        str_studyMapFile        : str = '%s/%s.json' % (
                                    self.str_studyMapDir,
                                    self.d_DICOM['StudyInstanceUID']
                                )
        return {
            'status'            : True,
            'studyMapFile'      : {
                'name'      : str_studyMapFile,
                'exists'    : os.path.isfile(str_studyMapFile)
            }
        }

    def studyMap_process(self) -> dict:
        """
        Process the study map data.
        """
        self.studyInfo_init()
        d_studyTable    = self.studyMap_DBtablesGet()
        if d_studyTable['studyMapFile']['exists']:
            with open(d_studyTable['studyMapFile']['name']) as fj:
                self.json_read(fj, self.d_studyMap)
                # self.d_studyMap    = json.load(fj)
            fj.close()
        if self.d_DICOM['StudyInstanceUID'] not in self.d_studyMap.keys():
            self.d_studyMap[self.d_DICOM['StudyInstanceUID']] =             \
                self.d_studyInfo
        l_seriesList    = [f['SeriesInstanceUID'] \
                            for f in self.d_studyMap[self.d_DICOM['StudyInstanceUID']]['SeriesList']]
        if self.d_DICOM['SeriesInstanceUID'] not in l_seriesList:
            self.d_studyMap[self.d_DICOM['StudyInstanceUID']]['SeriesList'].\
                append({
                    'SeriesInstanceUID' :   self.d_DICOM['SeriesInstanceUID'],
                    'SeriesBaseDir'     :   self.str_outputDir
                })
            self.seriesMapMeta('received', {'timestamp' : '%s' % datetime.datetime.now()})
            with open(d_studyTable['studyMapFile']['name'], 'w') as fj:
                self.json_write(self.d_studyMap, fj)
                # json.dump(self.d_studyMap, fj, indent = 4)
        self.d_studyInfo = self.d_studyMap[self.d_DICOM['StudyInstanceUID']]

    # def seriesMapMeta_packingStamp(self, *args) -> dict:
    #     """
    #     set or get the series map meta table packaging start information
    #     """
    #     b_status                        = False
    #     str_error                       = 'File does not exist at time of read'
    #     b_read                          = False
    #     d_stamp                         = {}
    #     d_seriesTable                   = self.seriesMap_DBtablesGet(
    #             SeriesInstanceUID       = self.d_DICOM['SeriesInstanceUID']
    #     )
    #     if d_seriesTable['status']:
    #         if d_seriesTable['seriesMapMetaFile']['exists']:
    #             with open(d_seriesTable['seriesMapMetaFile']['name']) as fj:
    #                 self.json_read(fj, d_stamp)
    #             fj.close()
    #             b_read                  = True
    #         if len(args):
    #             d_stamp['received']     = {
    #                 'timestamp'         : '%s' % datetime.datetime.now()
    #             }
    #             try:
    #                 with open(d_seriesTable['seriesMapMetaFile']['name'], 'w') as fj:
    #                     self.json_write(d_stamp, fj)
    #                 b_status            = True
    #                 str_error           = ''
    #             except Exception as e:
    #                 str_error           = '%s' % e
    #     return {
    #         'status'        : b_status,
    #         'error'         : str_error,
    #         'stamp'         : d_stamp
    #     }

    # def seriesMapMeta_relatedInstances(self, *args) -> dict:
    #     """
    #     Stamp the series map meta table with NumberOfSeriesRelatedInstances.
    #     """
    #     b_status                        = False
    #     str_error                       = 'File does not exist at time of read'
    #     b_read                          = False
    #     d_stamp                         = {}
    #     d_seriesTable                   = self.seriesMap_DBtablesGet(
    #             SeriesInstanceUID       = self.d_DICOM['SeriesInstanceUID']
    #     )
    #     if d_seriesTable['status']:
    #         if d_seriesTable['seriesMapMetaFile']['exists']:
    #             with open(d_seriesTable['seriesMapMetaFile']['name']) as fj:
    #                 self.json_read(fj, d_stamp)
    #             fj.close()
    #             b_read                  = True
    #         if len(args):
    #             d_stamp['NumberOfSeriesRelatedInstances']   = args[0]
    #             try:
    #                 with open(d_seriesTable['seriesMapMetaFile']['name'], 'w') as fj:
    #                     self.json_write(d_stamp, fj)
    #                 b_status            = True
    #                 str_error           = ''
    #             except Exception as e:
    #                 str_error           = '%s' % e
    #     return {
    #         'status'        : b_status,
    #         'error'         : str_error,
    #         'stamp'         : d_stamp
    #     }

    def seriesMapMeta(self, str_field, *args)   -> dict:
        """
        get/set the <str_field> in the seriesMapMeta
        """
        b_status                        = False
        str_error                       = 'File does not exist at time of read'
        b_read                          = False
        d_meta                          = {}
        d_seriesTable                   = self.seriesMap_DBtablesGet(
                SeriesInstanceUID       = self.d_DICOM['SeriesInstanceUID']
        )
        if d_seriesTable['status']:
            if d_seriesTable['seriesMapMetaFile']['exists']:
                with open(d_seriesTable['seriesMapMetaFile']['name']) as fj:
                    self.json_read(fj, d_meta)
                fj.close()
                b_read                  = True
            if len(args):
                d_meta[str_field]      = args[0]
                try:
                    with open(d_seriesTable['seriesMapMetaFile']['name'], 'w') as fj:
                        self.json_write(d_meta, fj)
                    b_status            = True
                    str_error           = ''
                except Exception as e:
                    str_error           = '%s' % e
        return {
            'status'        : b_status,
            'error'         : str_error,
            'meta'          : d_meta
        }

    def seriesStatus_get(self, str_SeriesInstanceUID) -> dict:
        """
        Return the status of the passed SeriesInstanceUID.
        """
        b_status        : bool  = False
        d_ret           : dict  = {}

    def seriesMap_DBtablesGet(self, **kwargs) -> dict:
        """
        Return the location in the DB (i.e. the file system) where
        the map information for a given SeriesInstanceUID is stored.
        """
        b_status                        = False
        str_SeriesInstanceUID           = ''
        str_outputFile                  = ''
        str_seriesBaseDir               = ''
        str_seriesMapSingleImageFile    = ''
        str_seriesMapMetaFile           = ''
        for k, v in kwargs.items():
            if k == 'SeriesInstanceUID' :   str_SeriesInstanceUID   = v
            if k == 'outputFile'        :   str_outputFile          = v
        if len(str_SeriesInstanceUID):
            b_status                    = True
            str_seriesBaseDir           = '%s/%s' % \
                    (self.str_seriesMapDir,
                     str_SeriesInstanceUID)
            str_seriesMapMetaFile           = '%s/%s-meta.json' % \
                    (self.str_seriesMapDir,
                     str_SeriesInstanceUID)
            if len(str_outputFile):
                str_seriesMapSingleImageFile    = '%s/%s.json' % (
                    str_seriesBaseDir, str_outputFile
                )
        return {
            'status'                    : b_status,
            'seriesBaseDir'             : {
                'name'      :   str_seriesBaseDir,
                'exists'    :   os.path.isdir(str_seriesBaseDir)
            },
            'seriesMapSingleImageFile'  : {
                'name'      :   str_seriesMapSingleImageFile,
                'exists'    :   os.path.isfile(str_seriesMapSingleImageFile)
            },
            'seriesMapMetaFile'         : {
                'name'      :   str_seriesMapMetaFile,
                'exists'    :   os.path.isfile(str_seriesMapMetaFile)
            }
        }

    def seriesMap_process(self, **kwargs) -> dict:
        """
        Process the series map data.
        """
        str_outputDir   = self.str_outputDir
        str_outputFile  = self.str_outputFile

        for k, v in kwargs.items():
            if k == 'outputDir'     : str_outputDir     = v
            if k == 'outputFile'    : str_outputFile    = v

        self.seriesInfo_init()
        d_seriesTable       = self.seriesMap_DBtablesGet(
                outputDir           = str_outputDir,
                outputFile          = str_outputFile,
                SeriesInstanceUID   = self.d_DICOM['SeriesInstanceUID'],
                **kwargs
        )
        if not d_seriesTable['seriesBaseDir']['exists']:
            os.makedirs(
                    d_seriesTable['seriesBaseDir']['name'],
                    exist_ok = True
            )
        if d_seriesTable['seriesMapSingleImageFile']['exists']:
            with open(d_seriesTable['seriesMapSingleImageFile']['name']) as fj:
                self.json_read(fj, self.d_seriesMap)
                # self.d_seriesMap    = json.load(fj)
            fj.close()
        if self.d_DICOM['SeriesInstanceUID'] not in self.d_seriesMap.keys():
            self.d_seriesMap[self.d_DICOM['SeriesInstanceUID']] =           \
                self.d_seriesInfo
        if str_outputFile not in                                            \
            self.d_seriesMap[self.d_DICOM['SeriesInstanceUID']]             \
                                            ['imageObj'].keys():
            ofs = os.stat('%s/%s' % (str_outputDir, str_outputFile))
            self.d_seriesMap[self.d_DICOM['SeriesInstanceUID']]['imageObj'] \
                                    [str_outputFile] =                      \
                {k.replace('st_', '') :                                     \
                    ('%s' % datetime.datetime.fromtimestamp(getattr(ofs, k))\
                    if 'time' in k and not 'ns' in k                        \
                        else getattr(ofs, k))                               \
                            for k in dir(ofs)                               \
                                if 'st' in k and not 'ns' in k and not '__'  in k}
            self.d_seriesMap[self.d_DICOM['SeriesInstanceUID']]['imageObj'] \
                                    [str_outputFile]['FSlocation'] =        \
                                        '%s/%s' % (str_outputDir, str_outputFile)
            with open(d_seriesTable['seriesMapSingleImageFile']['name'], 'w') as fj:
                self.json_write(self.d_seriesMap, fj)
                # json.dump(self.d_seriesMap, fj, indent = 4)
        else:
            self.d_seriesInfo     = self.d_seriesMap[self.d_DICOM['SeriesInstanceUID']]
        with open(d_seriesTable['seriesMapSingleImageFile']['name'], 'w') as fj:
            json.dump(self.d_seriesMap, fj, indent = 4)

    def mapsUpdateForFile(self, str_file):
        b_status        :   bool    = True

        # Store the <str_file>, i.e. the file location where the DICOM
        # has been repacked.
        self.str_outputDir  = os.path.dirname(str_file)
        self.str_outputFile = os.path.basename(str_file)

        self.patientMap_process()
        self.studyMap_process()
        self.seriesMap_process()

        return {
            'status'            : b_status,
            'd_patientInfo'     : self.d_patientInfo,
            'd_studyInfo'       : self.d_studyInfo,
            'd_seriesInfo'      : self.d_seriesInfo,
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


    def run(self):
        """
        Generic run handler -- mostly called when an "action" needs
        to be processed in relation to a specific DICOM file.

        The DICOM file to process is typically passed by a storescu
        process as #p/#f
        """
        d_run   = {
            'status'    : False
        }
        if self.args.str_action == 'mapsUpdateForFile':
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
        if self.args.str_action == 'endOfStudy':
            d_run['status'] = True
            d_run['endOfStudy'] = \
                self.endOfStudy('%s' % (
                            self.args.str_xcrdir,
                        )
                )
        if 'DBtablesGet' in self.args.str_action:
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
                        d_run['seriesMap_DBtablesGet']  = \
                            self.seriesMap_DBtablesGet(
                                SeriesInstanceUID   = self.d_DICOM['SeriesInstanceUID'],
                                outputFile          = self.args.str_xcrfile
                            )
                    if 'tudy' in self.args.str_action:
                        d_run['studyMap_DBtablesGet']   = \
                            self.studyMap_DBtablesGet()
                    if 'atient' in self.args.str_action:
                        d_run['patientMap_DBtablesGet'] = \
                            self.patientMap_DBtablesGet()
            if not d_run['status']:
                d_run['error_message']  = \
                    'Unable to process a valid DICOM %s/%s' % (
                        self.args.str_xcrdir,
                        self.args.str_xcrfile
                    )
        if not d_run['status']:
            d_run['error_on_action']  = '%s action called' % self.args.str_action
        return d_run



