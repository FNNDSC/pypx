# Global modules
import  subprocess, re, collections
import  pudb
import  json
import  sys
from    datetime            import  datetime
from    dateutil            import  relativedelta
from    terminaltables      import  SingleTable
from    argparse            import  Namespace, ArgumentParser
from    argparse            import  RawTextHelpFormatter
import  time

import  pfmisc
from    pfmisc._colors      import  Colors

from    dask                import  delayed, compute

# PYPX modules
from    .base               import Base
from    .move               import Move
import  pypx
from    pypx                import smdb
from    pypx                import report
from    pypx                import do
import  copy


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
        dest    = 'dblogbasepath',
        type    = str,
        default = '/tmp/log',
        help    = 'path to base dir of receipt database')

    # service access settings
    parser.add_argument(
        '--PACS',
        action  = 'store',
        dest    = 'PACS',
        type    = str,
        default = '',
        help    = 'PACS lookup service identifier')
    parser.add_argument(
        '--CUBE',
        action  = 'store',
        dest    = 'CUBE',
        type    = str,
        default = '',
        help    = 'CUBE lookup service identifier')
    parser.add_argument(
        '--swift',
        action  = 'store',
        dest    = 'swift',
        type    = str,
        default = '',
        help    = 'swift lookup service identifier')


    # PACS access settings
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
        '--serverIP',
        action  = 'store',
        dest    = 'serverIP',
        type    = str,
        default = '192.168.1.110',
        help    = 'PACS server IP')
    parser.add_argument(
        '--serverPort',
        action  = 'store',
        dest    = 'serverPort',
        type    = str,
        default = '4242',
        help    = 'PACS server port')
    parser.add_argument(
        '--findscu',
        action  = 'store',
        dest    = 'findscu',
        type    = str,
        default = '/usr/bin/findscu',
        help    = '"findscu" executable absolute location')
    parser.add_argument(
        '--movescu',
        action  = 'store',
        dest    = 'movescu',
        type    = str,
        default = '/usr/bin/movescu',
        help    = '"movescu" executable absolute location')

    # Query settings
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

    # Retrieve settings
    parser.add_argument(
        '--withFeedBack',
        action  = 'store_true',
        dest    = 'withFeedBack',
        default = False,
        help    = 'If specified, print the "then" events as they happen')
    parser.add_argument(
        '--then',
        action  = 'store',
        dest    = 'then',
        default = "",
        help    = 'If specified, perform another set operations "next" after the find')
    parser.add_argument(
        '--thenArgs',
        action  = 'store',
        dest    = 'thenArgs',
        default = "",
        help    = 'If specified, associate the corresponding JSON string in the list to a then operation')
    parser.add_argument(
        '--intraSeriesRetrieveDelay',
        action  = 'store',
        dest    = 'intraSeriesRetrieveDelay',
        default = "0",
        help    = 'If specified, then wait specified seconds between retrieve series loops')
    parser.add_argument(
        '--move',
        action  = 'store_true',
        dest    = 'move',
        default = False,
        help    = 'If specified with --retrieve, call initiate a PACS pull on the set of SeriesUIDs using pypx/move')

    parser.add_argument(
        '--json',
        action  = 'store_true',
        dest    = 'json',
        default = False,
        help    = 'If specified, dump the JSON structure relating to the query')

    parser.add_argument(
        "-v", "--verbosity",
        help    = "verbosity level for app",
        dest    = 'verbosity',
        type    = int,
        default = 1)
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
    parser.add_argument(
        '--waitForUserTerminate',
        help    = 'if specified, wait for user termination',
        dest    = 'b_waitForUserTerminate',
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

class Find(Base):

    """
    The Find module provides rather extensive PACS query
    functionality.

    See the 'query' method for the space of query parameters
    that the module offers. Text data pertaining to image sets
    that match the pattern of query values are returned by
    this method to a called as a JSON/dictionary payload.

    The return dictionary contains a field, 'report' that itself
    contains three report formats: 'tabular', 'rawText', and 'json'.
    The 'tabular' and 'rawText' reports are for console
    consumption/presentation, while the 'json' report is for
    software agents.

    This 'json' report also returns a hidden 'bodySeriesUID'
    section, with each entry corresponding in order to the
    seriesDescription that the report returns. These values
    are the SeriesInstanceUIDs that can actually be retrieved
    by the pypx/move operation.
    """

    def __init__(self, arg):
        """
        Constructor.

        Defines a default report structure, divided into a
        "header" and a "body". In each section,  DICOM tags
        retrieved from either the STUDY or SERIES level are
        catalogued.

        Since a given STUDY typically has several SERIES, in
        most cases only SERIES level tags are included in the
        "body".

        In some cases, some tags are only available at
        the SERIES level (such as the Modality). If such a tag
        is in the STUDY level, then the corresponding tag from
        the FIRST series in the STUDY is reported.
        """
        super(Find, self).__init__(arg)
        self.dp             = pfmisc.debug(
                                        verbosity   = self.verbosity,
                                        within      = 'Find',
                                        syslog      = False
                                        )
        self.log            = self.dp.qprint
        self.then           = do.Do(self.arg)

    def query(self, opt={}):
        parameters = {
            'AccessionNumber':                  '',
            'PatientID':                        '',
            'PatientName':                      '',
            'PatientBirthDate':                 '',
            'PatientAge':                       '',
            'PatientSex':                       '',
            'StudyDate':                        '',
            'StudyDescription':                 '',
            'StudyInstanceUID':                 '',
            'Modality':                         '',
            'ModalitiesInStudy':                '',
            'PerformedStationAETitle':          '',
            'NumberOfPatientRelatedInstances':  '',
            'NumberOfPatientRelatedStudies':    '',
            'NumberOfPatientRelatedSeries':     '',
            'NumberOfStudyRelatedInstances':    '',
            'NumberOfStudyRelatedSeries':       '',
            'NumberOfSeriesRelatedInstances':   '',
            'InstanceNumber':                   '',
            'SeriesDate':                       '',
            'SeriesDescription':                '',
            'SeriesInstanceUID':                '',
            'ProtocolName':                     '',
            'AcquisitionProtocolDescription':   '',
            'AcquisitionProtocolName':          '',
            'QueryRetrieveLevel':               'SERIES'
        }

        query = ''
        # we use a sorted dictionary so we can test generated command
        # more easily
        ordered = collections.OrderedDict(
                        sorted(
                                parameters.items(),
                                key=lambda t: t[0]
                                )
                        )
        for key, value in ordered.items():
            # update value if provided
            if key in opt:
                value = opt[key]
            # update query
            if value != '':
                query += ' -k "' + key + '=' + value + '"'
            else:
                query += ' -k ' + key

        return query

    def xinetd_command(self, opt={}):
        return "service xinetd restart"

    def findscu_command(self, opt={} ):

        command = '-xi -S'
        str_cmd     = "%s %s %s %s" % (
                        self.findscu,
                        command,
                        self.query(opt),
                        self.commandSuffix()
        )
        return str_cmd

    def run(self, opt={}):
        """
        Main entry method.

        In order to accommodate the widest range of PACS dialects,
        a query occurs in two phases/passes:

            * First, at the STUDY level to receive the set of possible
              StudyUIDs
            * Then, given each STUDY, run at the SERIES level to
              receive the set of SeriesUID information

        The query itself is based on the pattern of DICOM tag specifications
        given used to instantiate this class.

        """

        # First we execute on a STUDY level to determine all the
        # STUDIES related to this query
        formattedStudiesResponse    = \
            self.systemlevel_run(opt,
                    {
                        'f_commandGen':         self.findscu_command,
                        'QueryRetrieveLevel':   'STUDY'
                    }
            )

        if formattedStudiesResponse['status']  != 'error':
            filteredStudiesResponse             = {}
            filteredStudiesResponse['status']   = formattedStudiesResponse['status']
            filteredStudiesResponse['command']  = formattedStudiesResponse['command']
            filteredStudiesResponse['data']     = []
            filteredStudiesResponse['args']     = self.arg
            studyIndex                          = 0
            for study in formattedStudiesResponse['data']:
                l_seriesResults = []
                # For each study, we now execute a query on a SERIES
                # level to complete the picture.
                formattedSeriesResponse     = \
                    self.systemlevel_run(opt,
                            {
                                'f_commandGen':         self.findscu_command,
                                'QueryRetrieveLevel':   'SERIES',
                                'StudyInstanceUID':     study['StudyInstanceUID']['value']
                            }
                    )
                for series in formattedSeriesResponse['data']:
                    series['label']             = {}
                    series['label']['tag']      = 0
                    series['label']['value']    = "SERIES"
                    series['label']['label']    = 'RetrieveLevel'

                    series['command']           = {}
                    series['command']['tag']    = 0
                    series['command']['value']  = formattedSeriesResponse['command']
                    series['command']['label']  = 'command'

                    series['status']            = {}
                    series['status']['tag']     = 0
                    series['status']['value']   = formattedSeriesResponse['status']
                    series['status']['label']   = 'status'

                    l_seriesResults.append(series)

                if len(l_seriesResults):
                    filteredStudiesResponse['data'].append(study)
                    filteredStudiesResponse['data'][-1]['series']           \
                        = l_seriesResults

                formattedStudiesResponse['data'][studyIndex]['series']      \
                    = l_seriesResults
                studyIndex+=1
            if len(self.arg['then']):
                self.then.arg['reportData']     = copy.deepcopy(filteredStudiesResponse)
                d_then                          = self.then.run()
                filteredStudiesResponse['then'] = copy.deepcopy(d_then)
            return filteredStudiesResponse
        else:
            return formattedStudiesResponse
