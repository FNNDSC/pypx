# Turn off all logging for modules in this libary!!
# Any log noise from pydicom will BREAK receiving
# DICOM data from the remote PACS since the log messages
# will pollute and destroy the DICOM storescp protocol.
import logging
logging.disable(logging.CRITICAL)

from    argparse            import  Namespace

# Global modules
import  os
import  sys
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
import  hashlib
import  re

# PyDicom module
import  pydicom             as      dicom

# PYPX modules
import  pypx.utils
import  pypx.smdb

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
        '--parseAllFilesWithSubStr',
        action  = 'store',
        dest    = 'str_filesubstr',
        type    = str,
        default = '',
        help    = 'Parse all files in <xcrdir> that contain <substr>'
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
        '-d', '--datadir',
        action  = 'store',
        dest    = 'str_dataDir',
        type    = str,
        default = '/tmp/data',
        help    = 'Directory in which to pack final DICOM files'
        )

    parser.add_argument(
        '--rootDirTemplate',
        action  = 'store',
        dest    = 'str_rootDirTemplate',
        type    = str,
        default = '%PatientID-%PatientName-%PatientBirthDate',
        help    = 'Template pattern for root unpack directory'
        )
    parser.add_argument(
        '--studyDirTemplate',
        action  = 'store',
        dest    = 'str_studyDirTemplate',
        type    = str,
        default = '%StudyDescription-%AccessionNumber-%StudyDate',
        help    = 'Template pattern for study unpack directory'
        )
    parser.add_argument(
        '--seriesDirTemplate',
        action  = 'store',
        dest    = 'str_seriesDirTemplate',
        type    = str,
        default = '%_pad|5,0_SeriesNumber-%SeriesDescription',
        help    = 'Template pattern for series unpack directory'
        )
    parser.add_argument(
        '--imageTemplate',
        action  = 'store',
        dest    = 'str_imageTemplate',
        type    = str,
        default = '%_pad|4,0_InstanceNumber-%SOPInstanceUID.dcm',
        help    = 'Template pattern for image file'
        )

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
        args, unknown    = parser.parse_known_args(*args)
    else:
        args, unknown    = parser.parse_known_args(sys.argv[1:])
    return args, unknown

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


def args_impedanceMatch(ns_arg):
    """
    This method is an "impedance matcher" that examines the
    incoming namespace, ns_arg, and returns a new namespace that
    contains any missing elements necessary for full instantiation
    of the class object.

    Typically this method is used when the class is called as a module
    without the assumption of the native driving script creating the
    the fully qualified namespace.
    """
    l_key   : list  = []

    # Get the parser structure for this module
    parser          = parser_setup("impedanceMatching")
    args, unknown   = parser_interpret(parser)

    str_rootDirTemplate     = args.str_rootDirTemplate

    l_key = [k for (k,v) in vars(ns_arg).items()]
    if 'str_xcrdir'     not in l_key:   setattr(ns_arg, 'str_xcrdir', '/tmp')
    if 'str_xcrfile'    not in l_key:   setattr(ns_arg, 'str_xcrfile', '')
    if 'str_xcrdir'     not in l_key:   setattr(ns_arg, 'str_xcrdir', '')
    if 'str_xcrdirfile' not in l_key:   setattr(ns_arg, 'str_xcrdirfile', '')
    if 'str_filesubstr' not in l_key:   setattr(ns_arg, 'str_filesubstr', '')

    if 'str_rootDirTemplate'    not in l_key:
        setattr(ns_arg, 'str_rootDirTemplate',      args.str_rootDirTemplate)
    if 'str_studyDirTemplate'   not in l_key:
        setattr(ns_arg, 'str_studyDirTemplate',     args.str_studyDirTemplate)
    if 'str_seriesDirTemplate'  not in l_key:
        setattr(ns_arg, 'str_seriesDirTemplate',    args.str_seriesDirTemplate)
    if 'str_imageTemplate'      not in l_key:
        setattr(ns_arg, 'str_imageTemplate',        args.str_imageTemplate)
    return ns_arg

class Process():
    """
    The core class of the repack module -- this class essentially reads
    a DICOM file, parses its tags, and then repacks (or re-copies) that
    file to a more descriptive location on the filesystem.
    """

    def loggers_create(self):
        """
        >>>>>>>>>>>>>>   Debugging control  <<<<<<<<<<<<<<<<
        Essentially we create some pfmisc.debug objects that
        write to files and also give them some shortcut names
        """
        str_thisMRsession       = pathlib.PurePath(self.args.str_xcrdir).name
        self.str_pulseFile      = '%s/%s-pulse.log'     % (
                                                            self.args.str_logDir,
                                                            str_thisMRsession
                                                        )
        self.str_debugFile      = '%s/repack.log'       % self.args.str_logDir
        self.pulseObj           = pfmisc.debug(
                                            verbosity   = int(self.args.verbosity),
                                            level       = 2,
                                            within      = self.__name__,
                                            debugToFile = self.args.b_debug,
                                            debugFile   = self.str_pulseFile
                                            )
        self.dp                 = pfmisc.debug(
                                            verbosity   = int(self.args.verbosity),
                                            level       = 2,
                                            within      = self.__name__,
                                            debugToFile = self.args.b_debug,
                                            debugFile   = self.str_debugFile
                                            )
        self.logPulse           = self.pulseObj.qprint
        self.log                = self.dp.qprint

    def filesToRepack_determine(self):
        """
        Based on the pattern of CLI calling flags, determine which
        files to repack.
        """
        if self.args.str_filesubstr:
            try:
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
            except:
                pass
        else:
            self.l_files.append(self.args.str_xcrfile)

    def __init__(self, args):

        self.__name__           : str   = 'repack'
        self.args                       = args
        self.l_files            : list  = []

        if len(self.args.str_xcrdirfile):
            self.args.str_xcrdir        = os.path.dirname(
                                                self.args.str_xcrdirfile
                                        )
            self.args.str_xcrfile       = os.path.basename(
                                                self.args.str_xcrdirfile
                                        )

        self.smdb                       = pypx.smdb.SMDB(args)

        # set_trace(
        #             host            = "0.0.0.0",
        #             port            = 5555,
        #             term_size       = (252, 63)
        #         )

        self.filesToRepack_determine()
        self.loggers_create()
        self.logPulse('Pulsing on dir %s...' %  self.args.str_xcrdir,
                      level = 2)
        self.log(
            'Incoming DICOM dir: %s' % (self.args.str_xcrdir),
            level = 2
        )
        for str_file in self.l_files:
            self.log(
                'Incoming DICOM file: %s' % (str_file),
                level = 2
            )

    def cleanup(self, str_file):
        """
        Clean up -- this is called once per process sweep, with the
        received <str_file> as argument. Quite simply this method just
        deletes that file, should it exist, in the <xcrdir>.
        """
        b_status        :   bool    = False
        str_filepath    :   str     = os.path.join(
                                        self.args.str_xcrdir,
                                        str_file
                                    )
        str_error       :   str     = ''
        str_message     :   str     = ''
        if os.path.isfile(str_filepath):
            try:
                os.remove(str_filepath)
                b_status    = True
                str_message = '%s successfully deleted' % str_filepath
            except Exception as e:
                str_error   = '%s' % e

        return {
            'status'    : b_status,
            'error'     : str_error,
            'message'   : str_message
        }

    def run(self) -> dict:
        """
        Main entry point for receiver. This will, for each DICOM file to
        process, read the DICOM, perform some preprocessing on the DICOM
        tag  space,  and then  save  the  file  in the appropriate target
        directory tree.
        """
        dl_run      : list  = []
        d_run       : dict  = {'status' : False}
        for str_file in self.l_files:
            d_run           = self.DICOMfile_mapsUpdate(
                                self.DICOMfile_save(
                                    Process.DICOMfile_read(
                                        file = '%s/%s' % (
                                                self.args.str_xcrdir,
                                                str_file
                                            )
                                    )
                                )
                            )
            self.log(
                'DICOM repacked to: %s/%s' % \
                    ( d_run['d_DICOMfile_save']['outputDir'],
                      d_run['d_DICOMfile_save']['outputFile']),
                level = 2
            )
            # Before returning, we need to "sanitize" some of the
            # DICOMfile_read fields that are not JSON serializable
            # allowing us to present the caller with a nice return
            # JSON payload
            d_DICOM             = d_run['d_DICOMfile_save']\
                                            ['d_DICOMfile_read']\
                                                ['d_DICOM']
            d_DICOM['dcm']      = "Not JSON serializable"
            d_DICOM['d_dcm']    = "Not JSON serializable"
            d_DICOM['d_dicom']  = "Not JSON serializable"
            if self.args.b_cleanup: d_run['cleanup']= self.cleanup(str_file)
            dl_run.append(d_run)

        return {
            'status'    : d_run['status'],
            'run'       : dl_run
        }

    def packPath_resolve(self, d_DICOMfile_read) -> dict:
        """
        Return the pack path and image name template. Note this
        needs a d_DICOMread dictionary as returned from a call
        to DICOMfile_read.
        """

        def DICOMlookup_santitizeFromTemplate(str_template):
            """
            Process DICOM lookup tags in a template string and
            return a sanitized result.
            """
            return re.sub('[^A-Za-z0-9\.\-]+', '_',
                                self.tagsInString_process(
                                    d_DICOMfile_read['d_DICOM'],
                                    str_template
                                )['str_result']
                            )

        str_rootDir     :   str     = ''
        str_studyDir    :   str     = ''
        str_seriesDir   :   str     = ''
        str_packDir     :   str     = ''
        str_imageFile   :   str     = ''

        str_rootDir     = DICOMlookup_santitizeFromTemplate(
                            self.args.str_rootDirTemplate
                        )
        str_studyDir    = DICOMlookup_santitizeFromTemplate(
                            self.args.str_studyDirTemplate
                        )
        str_seriesDir   = DICOMlookup_santitizeFromTemplate(
                            self.args.str_seriesDirTemplate
                        )
        str_imageFile   = DICOMlookup_santitizeFromTemplate(
                            self.args.str_imageTemplate
                        )
        str_packDir     = '%s/%s/%s' % (
                            str_rootDir,
                            str_studyDir,
                            str_seriesDir
                        )

        return {
            'status'    : True,
            'packDir'   : str_packDir,
            'imageFile' : str_imageFile
        }


    def DICOMfile_save(self, d_DICOMfile_read) -> dict:
        """
        Save/pack the initial DICOM file in a new location based on the
        various <template> patterns:

        <dataDir>
            |
            └─<rootTemplate>
                    |
                    └─<studyTemplate>
                             |
                             └─<seriesTemplate>
                                      |
                                      └─<imageTemplate>.dcm

        Also update the various map files that are used to track the
        status of receipts.
        """

        b_status        :   bool    = False
        str_imageFile   :   str     = ''
        str_outputDir   :   str     = ''
        str_errorDir    :   str     = ''
        str_errorCopy   :   str     = ''
        str_path        :   str     = ''
        d_path          :   dict    = {}

        # pudb.set_trace()
        if d_DICOMfile_read['status']:
            d_path          = self.packPath_resolve(d_DICOMfile_read)
            str_outputDir   = '%s/%s' % (
                                    self.args.str_dataDir,
                                    d_path['packDir']
                            )
            str_imageFile   = d_path['imageFile']

            try:
                os.makedirs(str_outputDir)
            except Exception as e:
                str_errorDir    = '%s' %e
            try:
                str_path    = shutil.copy(
                                '%s/%s' % (
                                    d_DICOMfile_read['inputPath'],
                                    d_DICOMfile_read['inputFileName']
                                ),
                                '%s/%s' % (
                                    str_outputDir,
                                    str_imageFile
                                )
                            )
                b_status    = True
            except Exception as e:
                str_errorCopy   = '%s' % e
        return {
            'method'            : inspect.stack()[0][3],
            'outputDir'         : str_outputDir,
            'outputFile'        : str_imageFile,
            'shutilpath'        : str_path,
            'status'            : b_status,
            'errorDir'          : str_errorDir,
            'errorCopy'         : str_errorCopy,
            'd_DICOMfile_read'  : d_DICOMfile_read
        }

    def DICOMfile_mapsUpdate(self, d_DICOMfile_save)    -> dict:
        """
        Interact with the SMDB object to update JSON mapping information
        relative to this save operation.
        """
        b_status        :   bool    = False
        d_mapsUpdate    :   dict    = {}

        if d_DICOMfile_save['status']:
            b_status        = True
            self.smdb.housingDirs_create()
            self.smdb.DICOMobj_set(d_DICOMfile_save ['d_DICOMfile_read']\
                                                    ['d_DICOM']\
                                                    ['d_dicomSimple'])
            d_mapsUpdate    = self.smdb.mapsUpdateForFile(
                    '%s/%s' % ( d_DICOMfile_save['outputDir'],
                                d_DICOMfile_save['outputFile'])
            )
            self.smdb.seriesData('pack', 'seriesPack', True)

        return {
            'status'            : b_status,
            'd_mapsUpdate'      : d_mapsUpdate,
            'd_DICOMfile_save'  : d_DICOMfile_save
        }

    @staticmethod
    def DICOMfile_read(*args, **kwargs) -> dict:
        """
        Read a DICOM file and perform some initial  parsing of tags,
        returning  a  dictionary  object of multiple representations
        of the dicom data.

        Nested functions are used here, mainly for encapsulation
        and readability.
        """

        # Core structure template returned by this method
        d_DICOM : dict = {
                'str_dicomFile'     : '',
                'dcm'               : None,
                'd_dcm'             : {},
                'str_raw'           : '',
                'l_tagRaw'          : [],
                'str_json'          : {},
                'd_dicom'           : {},
                'd_dicomSimple'     : {},
                'l_tagsUsed'        : []
        }

        def dcm_readFromFile(str_file, d_DICOM) -> bool:
            """
            Load the <str_file> and populate some field records in <d_DCIOM>.
            """
            b_status    : bool          = False
            d_err       : dict          = {
                                            'file'      : '',
                                            'cwd'       : '',
                                            'message'   : ''
                                        }
            d_DICOM['str_dicomFile']    = str_file
            try:
                d_DICOM['dcm']          = dicom.read_file(str_file)
                b_status                = True
            except Exception as e:
                d_err['file']           = str_file
                d_err['cwd']            = os.getcwd()
                d_err['message']        = '%s' % e
                b_status                = False
            return {
                'method'        : inspect.stack()[0][3],
                'status'        : b_status,
                'error'         : d_err
            }

        def dcm_doExplicitToStr(d_dcm, str_file) -> dict:
            """
            This a nested error mitigation method, called when a
            implicit "to-string"  conversion fails.  This method
            attempts to perform  an  explicit conversion instead
            by performing an element  by element conversion over
            the dictionary of d_dcm FileDataset components.
            """
            b_status    : bool  = False
            l_k         : list  = list(d_dcm.keys())
            str_raw     : str   = ''
            str_err     : str   = ''

            for k in l_k:
                try:
                    str_raw     += str(d_dcm[k])
                    str_raw     += '\n'
                    b_status    = True
                except:
                    str_err     = 'Failed to string convert key "%s"' % k
                    str_raw     += str_err + "\n"
                    b_status    = False
            return {
                'method'        : inspect.stack()[0][3],
                'failingFile'   : str_file,
                'status'        : b_status,
                'conversion'    : str_raw,
                'error'         : str_err
            }

        def dcm_populate(d_DICOM, d_prior)   -> dict:
            """
            Populate some additional records of the d_DICOM structure
            by attempting simple conversions on the pydicom object
            """
            b_status    : bool          = False
            d_explicit  : dict          = {}
            d_raw       : dict          = {}
            if d_prior['status']:
                b_status                = True
                d_DICOM['l_tagRaw']     = d_DICOM['dcm'].dir()
                d_DICOM['d_dcm']        = dict(d_DICOM['dcm'])
                try:
                    d_DICOM['str_raw']  = str(d_DICOM['dcm'])
                except:
                    d_raw               = dcm_doExplicitToStr(
                                            d_DICOM['d_dcm'],
                                            d_prior)
                    d_DICOM['str_raw']  = d_raw['conversion']
            return {
                'method'        : inspect.stack()[0][3],
                'status'        : b_status,
                'rawConversion' : d_raw,
                'prior'         : d_prior
            }

        def dcm_dicomDictsProcess(d_DICOM, l_tags, d_prior) -> dict:
            """
            Populate the d_dicom dictionaries in the housing structure.
            """
            b_status    : bool              = False
            str_error   : str               = ''
            if d_prior['status']:
                if len(l_tags):
                    d_DICOM['l_tagsUsed']   = l_tags
                else:
                    d_DICOM['l_tagsUsed']   = d_DICOM['l_tagRaw'].copy()

                if 'PixelData' in d_DICOM['l_tagsUsed']:
                    d_DICOM['l_tagsUsed'].remove('PixelData')

                for key in d_DICOM['l_tagsUsed']:
                    d_DICOM['d_dicom'][key] = d_DICOM['dcm'].data_element(key)
                    try:
                        d_DICOM['d_dicomSimple'][key] = getattr(d_DICOM['dcm'], key)
                    except:
                        d_DICOM['d_dicomSimple'][key] = "no attribute"
                    if  not isinstance(d_DICOM['d_dicomSimple'][key], str)      or \
                        not isinstance(d_DICOM['d_dicomSimple'][key], list)     or \
                        not isinstance(d_DICOM['d_dicomSimple'][key], float)    or \
                        not isinstance(d_DICOM['d_dicomSimple'][key], bool)     or \
                        not isinstance(d_DICOM['d_dicomSimple'][key], int):
                            d_DICOM['d_dicomSimple'][key] = '%s' %  \
                                d_DICOM['d_dicomSimple'][key]
                try:
                    d_DICOM['str_json']     = json.dumps(d_DICOM['d_dicomSimple'])
                    b_status                = True
                except Exception as e:
                    str_error   = '%s' % e

            return {
                'method'        : inspect.stack()[0][3],
                'status'        : b_status,
                'error'         : str_error,
                'prior'         : d_prior
            }

        b_status        : bool  = False
        l_tags          : list  = []
        l_tagsToUse     : list  = []
        d_tagsInString  : dict  = {}
        str_file        : str   = ""
        str_outputFile  : str   = ""

        for k, v in kwargs.items():
            if k == 'file':             str_file    = v
            if k == 'l_tagsToUse':      l_tags      = v

        if len(args):
            l_file      : list  = args[0]
            str_file    : str   = l_file[0]

        d_DICOMprocess  = dcm_dicomDictsProcess(d_DICOM, l_tags,
            dcm_populate(d_DICOM,
                dcm_readFromFile(str_file, d_DICOM)
            )
        )

        return {
            'method'            : inspect.stack()[0][3],
            'status'            : d_DICOMprocess['status'],
            'inputPath'         : os.path.dirname(str_file),
            'inputFileName'     : os.path.basename(str_file),
            'd_DICOM'           : d_DICOM,
            'd_DICOMprocess'    : d_DICOMprocess
        }


    def tagsInString_process(self, d_DICOM, astr, *args, **kwargs):
        """
        This method substitutes DICOM tags that are '%'-tagged
        in a string template with the actual tag lookup.

        For example, an output filename that is specified as the
        following string:

            %PatientAge-%PatientID-output.txt

        will be parsed to

            006Y-4412364-ouptut.txt

        It is also possible to apply certain permutations/functions
        to a tag. For example, a function is identified by an underscore
        prefixed and suffixed string as part of the DICOM tag. If
        found, this function is applied to the tag value. For example,

            %PatientAge-%_md5|4_PatientID-output.txt

        will apply an md5 hash to the PatientID and use the first 4
        characters:

            006Y-7f38-output.txt

        """

        def pad_process(func, str_replace):
            """
            Pad a string in a given width.

            Arg specifier:

                    "<width>,<leadingChar>"

            i.e.

                %_pad|3,0_

            will pad the value in a width 3 with leading '0's.

            """
            nonlocal    astr
            l_funcTag   = []        # a function/tag list
            l_funcTag   = func.split('_')[1:]
            func        = l_funcTag[0]
            char        = '0'
            str_pad     = ''
            l_args      = func.split('|')
            if len(l_args) > 1:
                str_pad     = l_args[1]
            if len(str_pad):
                l_arg   = str_pad.split(',')
                width   = l_arg[0]
                if len(l_arg) > 1:
                    char    = l_arg[1]
                str_replace     = str_replace.rjust(int(width), char)
            astr        = astr.replace('_%s_' % func, '')
            return astr, str_replace

        def md5_process(func, str_replace):
            """
            md5 mangle the <str_replace>.
            """
            nonlocal    astr
            l_funcTag   = []        # a function/tag list
            l_args      = []        # the 'args' of the function
            chars       = ''        # the number of resultant chars from func
                                    # result to use
            str_replace = hashlib.md5(str_replace.encode('utf-8')).hexdigest()
            l_funcTag   = func.split('_')[1:]
            func        = l_funcTag[0]
            l_args      = func.split('|')
            if len(l_args) > 1:
                chars   = l_args[1]
                str_replace     = str_replace[0:int(chars)]
            astr        = astr.replace('_%s_' % func, '')
            return astr, str_replace

        def strmsk_process(func, str_replace):
            """
            string mask
            """
            nonlocal    astr
            l_funcTag   = []        # a function/tag list
            l_funcTag   = func.split('_')[1:]
            func        = l_funcTag[0]
            str_msk     = func.split('|')[1]
            l_n = []
            for i, j in zip(list(str_replace), list(str_msk)):
                if j == '*':    l_n.append(i)
                else:           l_n.append(j)
            str_replace = ''.join(l_n)
            astr        = astr.replace('_%s_' % func, '')
            return astr, str_replace

        def nospc_process(func, str_replace):
            """
            replace spaces in string
            """
            nonlocal    astr
            l_funcTag   = []        # a function/tag list
            l_args      = []        # the 'args' of the function
            l_funcTag   = func.split('_')[1:]
            func        = l_funcTag[0]
            l_args      = func.split('|')
            str_char    = ''
            if len(l_args) > 1:
                str_char = l_args[1]
            # strip out all non-alphnumeric chars and
            # replace with space
            str_replace = re.sub(r'\W+', ' ', str_replace)
            # replace all spaces with str_char
            str_replace = str_char.join(str_replace.split())
            astr        = astr.replace('_%s_' % func, '')
            return astr, str_replace

        def convertToNumber (s):
            return int.from_bytes(s.encode(), 'little')

        def convertFromNumber (n):
            return n.to_bytes(math.ceil(n.bit_length() / 8), 'little').decode()

        def name_process(func, str_replace):
            """
            replace str_replace with a name

            Note this sub-function can take as an argument a DICOM tag, which
            is then used to seed the name caller. This assures that all
            DICOM files belonging to the same series (or that have the same
            DICOM tag value passed as argument) all get the same 'name'.

            NB: If a DICOM tag is passed as an argument, the first character
            of the tag must be lower case to protect parsing of any non-arg
            DICOM tags.
            """
            nonlocal        astr, d_DICOM
            l_funcTag       = []        # a function/tag list
            l_args          = []        # the 'args' of the function
            l_funcTag       = func.split('_')[1:]
            func            = l_funcTag[0]
            l_args          = func.split('|')
            if len(l_args) > 1:
                str_argTag  = l_args[1]
                str_argTag  = re.sub('([a-zA-Z])', lambda x: x.groups()[0].upper(), str_argTag, 1)
                if str_argTag in d_DICOM['d_dicomSimple']:
                    str_seed    = d_DICOM['d_dicomSimple'][str_argTag]
                    randSeed    = convertToNumber(str_seed)
                    Faker.seed(randSeed)
            str_firstLast   = pfdicom.fake.name()
            l_firstLast     = str_firstLast.split()
            str_first       = l_firstLast[0]
            str_last        = l_firstLast[1]
            str_replace     = '%s^%s^ANON' % (str_last.upper(), str_first.upper())
            astr            = astr.replace('_%s_' % func, '')
            return astr, str_replace

        b_tagsFound         = False
        str_replace         = ''        # The lookup/processed tag value
        l_tags              = []        # The input string split by '%'
        l_tagsToSub         = []        # Remove any noise etc from each tag
        func                = ''        # the function to apply
        tag                 = ''        # the tag in the funcTag combo

        if '%' in astr:
            l_tags          = astr.split('%')[1:]
            # Find which tags (mangled) in string match actual tags
            l_tagsToSub     = [i for i in d_DICOM['l_tagRaw'] if any(i in b for b in l_tags)]
            # Need to arrange l_tagsToSub in same order as l_tags
            l_tagsToSubSort =  sorted(
                l_tagsToSub,
                key = lambda x: [i for i, s in enumerate(l_tags) if x in s][0]
            )
            for tag, func in zip(l_tagsToSubSort, l_tags):
                b_tagsFound     = True
                str_replace     = str(d_DICOM['d_dicomSimple'][tag])
                if 'md5'    in func: astr, str_replace   = md5_process(func, str_replace)
                if 'strmsk' in func: astr, str_replace   = strmsk_process(func, str_replace)
                if 'nospc'  in func: astr, str_replace   = nospc_process(func, str_replace)
                if 'name'   in func: astr, str_replace   = name_process(func, str_replace)
                if 'pad'    in func: astr, str_replace   = pad_process(func, str_replace)
                astr  = astr.replace('%' + tag, str_replace)

        return {
            'status':       True,
            'b_tagsFound':  b_tagsFound,
            'str_result':   astr
        }

