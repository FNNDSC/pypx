# Global modules
import  subprocess
import  pudb
import  json
import  pfmisc
from    pfmisc._colors      import  Colors

import  os
from    os                  import  listdir
from    os.path             import  isfile, join
import  sys
from    datetime            import  date, datetime

from    .pfstorage          import  swiftStorage

# PYPX modules
import  pypx.smdb
from    .base               import Base
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

    # File/dir settings
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

    # PACS settings
    parser.add_argument(
        '--aet',
        action  = 'store',
        dest    = 'aet',
        type    = str,
        default = 'CHRIS-ULTRON-AET',
        help    = 'aet')
    parser.add_argument(
        '--aec',
        action  = 'store',
        dest    = 'aec',
        type    = str,
        default = 'CHRIS-ULTRON-AEC',
        help    = 'aec')
    parser.add_argument(
        '--PACSserverIP',
        action  = 'store',
        dest    = 'str_PACSserverIP',
        type    = str,
        default = '192.168.1.110',
        help    = 'PACS server IP')
    parser.add_argument(
        '--PACSserverPort',
        action  = 'store',
        dest    = 'str_PACSserverPort',
        type    = str,
        default = '4242',
        help    = 'PACS server port')
    parser.add_argument(
        '--movescu',
        action  = 'store',
        dest    = 'movescu',
        type    = str,
        default = '/usr/bin/movescu',
        help    = '"movescu"" executable absolute location')

    # Swift settings
    parser.add_argument(
        '--swift',
        action  = 'store',
        dest    = 'swift',
        type    = str,
        default = '',
        help    = 'swift lookup service identifier')

    parser.add_argument(
        '--swiftIP',
        action  = 'store',
        dest    = 'str_swiftIP',
        type    = str,
        default = '',
        help    = 'swift IP')
    parser.add_argument(
        '--swiftPort',
        action  = 'store',
        dest    = 'str_swiftPort',
        type    = str,
        default = '',
        help    = 'swift port')
    parser.add_argument(
        '--swiftLogin',
        action  = 'store',
        dest    = 'str_swiftLogin',
        type    = str,
        default = '',
        help    = 'swift login')

    parser.add_argument(
        '--PACS',
        action  = 'store',
        dest    = 'PACS',
        type    = str,
        default = '',
        help    = 'PACS lookup service identifier')
    parser.add_argument(
        '--swiftServicesPACS',
        action  = 'store',
        dest    = 'str_swiftServicesPACS',
        type    = str,
        default = '',
        help    = 'swift PACS location within SERVICE/PACS to push files')
    parser.add_argument(
        "--swiftPackEachDICOM",
        help    = "If specified, determine the pack location of _each_ DICOM file",
        dest    = 'b_swiftPackEachDICOM',
        action  = 'store_true',
        default = False
    )
    parser.add_argument(
        '--swiftBaseLocation',
        action  = 'store',
        dest    = 'str_swiftBaseLocation',
        type    = str,
        default = '',
        help    = 'swift base location to push files')

    # CUBE settings
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


    # Data settings
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
        help    = "long synopsis",
        dest    = 'desc',
        action  = 'store_true',
        default = False
    )
    parser.add_argument(
        "-y", "--synopsis",
        help    = "short synopsis",
        dest    = 'synopsis',
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

class Push(Base):
    """
        ``px-push`` is the primary vehicle for transmitting a DICOM file
        to a remote location. The remote location can be either another
        PACS node (in which case the PACS related args are used), or
        swift storage (in which the swift related args are used). In the
        case of swift storage, and if CUBE related args are used, then
        this module will also register the files that have been pushed
        to the CUBE instance.
    """

    def serviceKey_process(self) -> dict:
        """
        If a service key (--swift <key>) has been specified, read from
        smdb service storage and set the CLI flags to pass on along to
        pfstorage.
        """
        d_swiftInfo :   dict    = {}
        d_swiftInfo['status']   = False
        if len(self.arg['swift']):
            d_swiftInfo = self.smdb.service_keyAccess('swift')
            if d_swiftInfo['status']:
                self.arg['str_swiftIP']     = d_swiftInfo['swift'][self.arg['swift']]['ip']
                self.arg['str_swiftPort']   = d_swiftInfo['swift'][self.arg['swift']]['port']
                self.arg['str_swiftLogin']  = d_swiftInfo['swift'][self.arg['swift']]['login']

        return d_swiftInfo

    def __init__(self, arg):
        """
        Constructor.

        Largely simple/barebones constructor that calls the Base()
        and sets up the executable name.
        """
        self.l_files        : list  = []

        # Check if an upstream 'reportData' exists, and if so
        # merge those the upstream process's CLI args into the
        # current namespace.
        #
        # NOTE:
        #
        # * the merge is on the *dest* of the argparse namespace, not
        #   the CLI keys -- so on 'b_json' and not '--json' for example.
        #
        # * this merge WILL OVERWRITE/CLOBBER any CLI specified
        #   for this app in favor of upstream ones *except* for
        #   the 'withFeedBack' and 'json'!
        #
        # * CLI dest keys that are not in the CLI space of this app
        #   are nonetheless still added to the arg structure -- this
        #   allows for downstream tranmission to apps with different
        #   CLI dest spaces.

        if 'reportData' in arg.keys():
            if 'args' in arg['reportData']:
                for k,v in arg['reportData']['args'].items():
                    # if k in arg and len('%s' % v):
                    if len('%s' % v):
                        if k not in ['json', 'withFeedBack']:
                            arg[k] = v

        self.smdb                           = pypx.smdb.SMDB(Namespace(**arg))
        super(Push, self).__init__(arg)
        self.serviceKey_process()
        self.dp             = pfmisc.debug(
                                verbosity   = self.verbosity,
                                within      = 'Push',
                                syslog      = False
        )
        self.log            = self.dp.qprint
        self.arg['name']    = "Push/PfStorage"

    def pushToPACS_true(self):
        """
        Return a bool condition that indicates if the image data is
        to be sent to a PACS
        """
        b_pushToPACS        : bool  = False
        return b_pushToPACS

    def pushToSwift_true(self):
        """
        Return a bool condition that indicates if the image data is
        to be sent to swift storage
        """
        b_pushToSwift       : bool  = True
        return b_pushToSwift

    def path_pushToSwift(self):
        """
        Push files in the path <xcrdir> to swift
        """
        d_do                : dict  = {
            'action'    :       'objPut',
            'args'      : {
                'localpath'         :   self.arg['str_xcrdir'],
                'DICOMsubstr'       :   self.arg['str_filesubstr'],
                'packEachDICOM'     :   self.arg['b_swiftPackEachDICOM'],
                'toLocation'        :   'SERVICES/PACS/%s/%%pack' % \
                                            self.arg['str_swiftServicesPACS'],
                'mapLocationOver'   :   self.arg['str_xcrdir']
            }
        }
        store               = swiftStorage(self.arg)
        d_storeDo           = store.run(d_do)

        # Record in the smdb an entry for each series
        for series in store.obj.keys():
            self.smdb.d_DICOM   = store.obj[series]['d_DICOM']['d_dicomSimple']
            if d_storeDo['status']:
                now     = datetime.now()
                self.smdb.seriesData('push', 'store',       d_storeDo[series])
                self.smdb.seriesData('push', 'timestamp',   now.strftime("%Y-%m-%d, %H:%M:%S"))
                if len(self.arg['swift']):
                    self.smdb.seriesData('push', 'swift',
                        self.smdb.service_keyAccess('swift')['swift'][self.arg['swift']])
        return d_storeDo

    def run(self, opt={}) -> dict:

        d_push              : dict  = {}

        if self.pushToSwift_true():
            d_push  = self.path_pushToSwift()

        return d_push
