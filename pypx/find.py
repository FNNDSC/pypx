# Global modules
import  subprocess, re, collections
import  pudb
import  json
import  pfmisc
from    pfmisc._colors      import  Colors
from    datetime            import  datetime
from    dateutil            import  relativedelta
from    terminaltables      import  SingleTable
import  time

# PYPX modules
from .base  import Base
from .move  import Move
import  pypx

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

        b_reportSet = False
        if 'reportTags' in arg.keys():
            if len(arg['reportTags']):
                self.d_reportTags   = json.loads(arg['reportTags'])
                b_reportSet         = True
        if not b_reportSet:
            self.d_reportTags = \
            {
                "header": 
                {
                    "study" : [
                            "PatientName",
                            "PatientBirthDate",
                            "StudyDate",
                            "PatientAge",
                            "PatientSex",
                            "AccessionNumber",
                            "PatientID",
                            "PerformedStationAETitle",
                            "StudyDescription"
                            ],
                    "series": [
                            "Modality"
                    ]
                },
                "body": 
                {
                    "series" : [ 
                            "SeriesDescription"
                            ]
                }
            }

        super(Find, self).__init__(arg)
        self.dp             = pfmisc.debug(
                                        verbosity   = self.verbosity,
                                        within      = 'Find',
                                        syslog      = False
                                        )

    def report_generate(self, d_queryResult):
        """
        Generate a nicely formatted report string, 
        suitable for tty/consoles.
        """

        def patientAge_calculate(study):
            """
            Explicitly calculate the age from the 
                    PatientBirthDate
                    StudyDate
            """
            str_birthDate   = study['PatientBirthDate']['value']
            str_studyDate   = study['StudyDate']['value']
            try:
                dt_birthDate    = datetime.strptime(str_birthDate, '%Y%m%d') 
                dt_studyDate    = datetime.strptime(str_studyDate, '%Y%m%d')
                dt_patientAge   = relativedelta.relativedelta(dt_studyDate, dt_birthDate)
                str_patientAge  = '%02dY-%02dM-%02dD' % \
                    (
                        dt_patientAge.years,
                        dt_patientAge.months,
                        dt_patientAge.days
                    )
            except:
                str_patientAge  = "NaN"
            return str_patientAge

        def DICOMtag_lookup(d_DICOMfields, str_DICOMtag):
            """
            Process a study field lookup
            """
            str_value   = ""
            try:
                str_value   = d_DICOMfields[str_DICOMtag]['value']
            except:
                if str_DICOMtag == 'PatientAge':
                    """
                    Sometimes the PatientAge is not returned
                    in the call to PACS. In this case, calculate
                    the age from the PatientBirthDate and StudyDate.
                    Note this my be unreliable!
                    """
                    str_value   = patientAge_calculate(d_DICOMfields)
            return str_value

        def block_build(
                l_DICOMtag, 
                l_blockFields, 
                l_blockTable, 
                str_reportBlock,
                d_block
            ):
            """
            Essentially create a text/table of rows each of 2 columns.
            """

            def tableRow_add2Col(str_left, 
                                str_right, 
                                leftColWidth   = 30, 
                                rightColWidth  = 50):
                """
                Add 2 columns to a table 
                """
                nonlocal CheaderField, CheaderValue
                return [
                            CheaderField        +
                            f"{str_left:<30}"   +
                            Colors.NO_COLOUR, 
                            CheaderValue        +
                            f"{str_right:<50}"  +
                            Colors.NO_COLOUR
                        ]

            def row_add2Col(str_left, 
                            str_right, 
                            leftColWidth    = 30, 
                            rightColWidth   = 50):
                """
                Add 2 columns to a string text
                """
                nonlocal CheaderField, CheaderValue
                return "%s%30s%s%50s%s\n" % \
                        (   
                            CheaderField,
                            str_left, 
                            CheaderValue,
                            str_right,
                            Colors.NO_COLOUR
                        )

            for str_tag  in l_blockFields:
                l_blockTable.append(
                    tableRow_add2Col(
                        str_tag, 
                        DICOMtag_lookup(l_DICOMtag, str_tag))
                )
                str_reportBlock += \
                    row_add2Col(
                        str_tag,
                        DICOMtag_lookup(l_DICOMtag, str_tag)
                        )
                d_block[str_tag] = DICOMtag_lookup(l_DICOMtag, str_tag)

            return l_blockTable, str_reportBlock, d_block

        def colorize_set():
            CheaderField        = ''
            CheaderValue        = ''
            str_colorize        = self.colorize
            b_colorize          = bool(len(str_colorize))
            if b_colorize:
                if str_colorize == 'dark':
                    CheaderField    = Colors.LIGHT_BLUE
                    CheaderValue    = Colors.LIGHT_GREEN
                if str_colorize == 'light':
                    CheaderField    = Colors.BLUE
                    CheaderValue    = Colors.GREEN
            return CheaderField, CheaderValue

        def header_generate(study):
            """
            For a given 'study' structure, generate a header block
            in various formats.
            """
            # Generate the "header" for the given study
            d_headerContents    = {}
            str_reportHeader    = ""
            l_headerTable       = []
            analyze             = None
            for k in self.d_reportTags['header']:
                if k == 'study': 
                    analyze = study
                if k == 'series':
                    if len(study['series']):
                        analyze = study['series'][0]
                l_tags  = self.d_reportTags['header'][k]
                l_headerTable, str_reportHeader, d_headerContents = \
                    block_build(analyze, l_tags, l_headerTable, str_reportHeader, d_headerContents)

            tb_headerInstance   = SingleTable(l_headerTable)
            tb_headerInstance.inner_heading_row_border  = False
            return tb_headerInstance.table, str_reportHeader, d_headerContents

        def body_generate(study):
            """
            For a given 'study' structure, generate a body block
            in various formats. Typically, the body contains tags
            from the SERIES level. Note currently STUDY tags in the
            body are not supported.
            """
            str_reportSUID      = ""
            str_reportBody      = ""
            d_bodyFields        = self.d_reportTags['body']
            for k in d_bodyFields.keys():
                l_bodyTable     = []
                l_suidTable     = []
                d_bodyContents  = {}
                d_seriesUID     = {}
                dl_bodyContents = []
                dl_seriesUID    = []
                l_seriesUIDtag  = ['SeriesInstanceUID']
                if k == 'series':
                    l_series    = study['series']
                    l_tags      = self.d_reportTags['body']['series']
                    for series in l_series:
                        # pudb.set_trace()
                        l_bodyTable, str_reportBody, d_bodyContents     = \
                            block_build(
                                    series, 
                                    l_tags, 
                                    l_bodyTable, 
                                    str_reportBody, 
                                    d_bodyContents
                            )
                        dl_bodyContents.append(d_bodyContents.copy())
                        # capture a hidden SeriesInstanceUID for the JSON return
                        l_suidTable, str_reportSUID, d_seriesUID    = \
                            block_build(
                                    series, 
                                    l_seriesUIDtag, 
                                    l_suidTable, 
                                    str_reportSUID, 
                                    d_seriesUID
                            )
                        dl_seriesUID.append(d_seriesUID.copy())

                    tb_bodyInstance = SingleTable(l_bodyTable)
                    tb_bodyInstance.inner_heading_row_border    = False

            return tb_bodyInstance.table, str_reportBody, dl_bodyContents, dl_seriesUID

        CheaderField, CheaderValue = colorize_set()

        l_tabularHits       = []
        l_rawTextHits       = []
        l_jsonHits          = []
        for study in d_queryResult['data']:
            d_tabular       = {}
            d_rawText       = {}
            d_json          = {}

            # Generate the header
            d_tabular['header'],        \
            d_rawText['header'],        \
            d_json['header']   =        \
                header_generate(study)

            # Generate the body
            d_tabular['body'],          \
            d_rawText['body'],          \
            d_json['body'],             \
            d_json['bodySeriesUID'] =   \
                body_generate(study)
     
            l_tabularHits.append(d_tabular)
            l_rawTextHits.append(d_rawText)
            l_jsonHits.append(d_json)

        return {
                "tabular":  l_tabularHits, 
                "rawText":  l_rawTextHits,
                "json":     l_jsonHits
        }

    def query(self, opt={}):
        parameters = {
            'AccessionNumber': '',
            'PatientID': '',                     # PATIENT INFORMATION
            'PatientName': '',
            'PatientBirthDate': '',
            'PatientAge': '',
            'PatientSex': '',
            'StudyDate': '',                     # STUDY INFORMATION
            'StudyDescription': '',
            'StudyInstanceUID': '',
            'Modality': '',
            'ModalitiesInStudy': '',
            'PerformedStationAETitle': '',
            'NumberOfSeriesRelatedInstances': '', # SERIES INFORMATION
            'InstanceNumber': '',
            'SeriesDate': '',
            'SeriesDescription': '',
            'SeriesInstanceUID': '',
            'QueryRetrieveLevel': 'SERIES'
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

    def retrieve_request(self, d_filteredHits):
        """
        Perform a request to "move" the image data at SERIES level.

        This essentially loops over all the SeriesInstanceUID in the
        query space structure.

        For the special case of a dockerized run, this method will attempt
        to also restart the 'xinet.d' service within the container.

        NOTE: Some PACS servers require the StudyInstanceUID in addition
        to the SeriesInstanceUID.

        """
        self.systemlevel_run(self.arg, 
            {
                'f_commandGen': self.xinetd_command
            }
        )
        studyIndex  = 0
        l_run       = []
        for study in d_filteredHits['report']['json']:
            seriesIndex = 0
            str_header  = d_filteredHits['report']['rawText'][studyIndex]['header']
            self.dp.qprint('\n%s' % str_header)
            for series, seriesUID in zip( study['body'], study['bodySeriesUID']):
                str_seriesDescription   = series['SeriesDescription']
                str_seriesUID           = seriesUID['SeriesInstanceUID']
                str_studyUID            = d_filteredHits['data'][studyIndex]['StudyInstanceUID']['value']
                self.dp.qprint(
                    Colors.LIGHT_CYAN + 
                    'Requesting SeriesDescription... ' +
                    Colors.YELLOW + 
                    str_seriesDescription
                )
                if self.move:
                    self.arg['SeriesInstanceUID']   = str_seriesUID
                    self.arg['StudyInstanceUID']    = str_studyUID
                    d_moveRun = pypx.move({
                            **self.arg,
                            })                   
                else:
                    d_moveRun = self.systemlevel_run(self.arg, 
                            {
                                'f_commandGen':         self.movescu_command,
                                'series_uid':           str_seriesUID,
                                'study_uid':            str_studyUID
                            }
                )
                l_run.append(d_moveRun)
                if 'SeriesDescription' in study['body'][seriesIndex]:
                    study['body'][seriesIndex]['PACS_Retrieve'] = " [ OK ] "
                seriesIndex += 1
                time.sleep(1)
            studyIndex += 1
            # pudb.set_trace()
        return l_run

    def xinetd_command(self, opt={}):
        return "service xinetd restart"

    def movescu_command(self, opt={}):
        command = '-S --move ' + opt['aet']
        command += ' --timeout 5'
        command += ' -k QueryRetrieveLevel=SERIES'
        command += ' -k SeriesInstanceUID=' + opt['series_uid']
        command += ' -k StudyInstanceUID='  + opt['study_uid']

        str_cmd     = "%s %s %s" % (
                        self.movescu,
                        command,
                        self.commandSuffix()
        )
        return str_cmd

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

        For some PACS, a query needs to be run in two phases:

            * First, at the STUDY level to receive the StudyUID
            * Then, given each STUDY, run at the SERIES level to
              receive the SeriesUID

        This method performs the query based on the pattern of 
        tag specifications given on the CLI.

        """
        # pudb.set_trace()

        formattedStudiesResponse    = \
            self.systemlevel_run(opt, 
                    {
                        'f_commandGen':         self.findscu_command,
                        'QueryRetrieveLevel':   'STUDY'
                    }
            )

        filteredStudiesResponse             = {}
        filteredStudiesResponse['status']   = formattedStudiesResponse['status']
        filteredStudiesResponse['command']  = formattedStudiesResponse['command']
        filteredStudiesResponse['data']     = []
        studyIndex                          = 0
        for study in formattedStudiesResponse['data']:
            l_seriesResults = []
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
                filteredStudiesResponse['data'][-1]['series']       = l_seriesResults

            formattedStudiesResponse['data'][studyIndex]['series']  = l_seriesResults
            studyIndex+=1

        # pudb.set_trace()
        d_report  = self.report_generate(filteredStudiesResponse)
        filteredStudiesResponse['report'] = d_report
        if self.retrieve: self.retrieve_request(filteredStudiesResponse)
        if len(self.printReport):
            if self.printReport in filteredStudiesResponse['report'].keys():
                self.report_print(filteredStudiesResponse['report'])
        return filteredStudiesResponse

    def report_print(self, d_hits):
        """
        Print a report based on one of the <str_field> arguments.
        """
        str_field   = self.printReport
        if str_field != 'json':
            for d_hit in d_hits[str_field]:
                print("%s\n%s\n" % (d_hit['header'], d_hit['body']))
        else:
            print(
                json.dumps(
                    d_hits['json'],
                    indent = 4
                )
            )
