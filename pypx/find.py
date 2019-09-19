# Global modules
import  subprocess, re, collections
import  pudb
import  json
from    pfmisc._colors      import  Colors
from    datetime            import  datetime
from    dateutil            import  relativedelta
from    terminaltables      import  SingleTable

# PYPX modules
from .base import Base

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

        if len(arg['reportTags']):
            self.d_reportTags   = json.loads(arg['reportTags'])
        else:
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
                            "StudyDescription",
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
            dt_birthDate    = datetime.strptime(str_birthDate, '%Y%m%d') 
            dt_studyDate    = datetime.strptime(str_studyDate, '%Y%m%d')
            dt_patientAge   = relativedelta.relativedelta(dt_studyDate, dt_birthDate)
            str_patientAge  = '%02dY-%02dM-%02dD' % \
                (
                    dt_patientAge.years,
                    dt_patientAge.months,
                    dt_patientAge.days
                )
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

        str_colorize        = self.arg['colorize']
        b_colorize          = bool(len(str_colorize))
        str_reportHeader    = ""
        str_reportBody      = ""
        str_reportSUID      = ""
        str_reportText      = ""
        str_reportTable     = ""

        CheaderField        = ''
        CheaderValue        = ''
        if b_colorize:
            if str_colorize == 'dark':
                CheaderField    = Colors.LIGHT_BLUE
                CheaderValue    = Colors.LIGHT_GREEN

        analyze             = None
        l_studyHits         = []
        for study in d_queryResult['data']:
            # Generate the "header"
            d_study             = {}
            d_headerContents    = {}
            str_reportHeader    = "\n\n"
            l_headerTable       = []
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
            d_study['header']   = d_headerContents.copy()

            # Generate the body
            d_bodyFields        = self.d_reportTags['body']
            for k in d_bodyFields.keys():
                l_bodyTable     = []
                l_suidTable     = []
                d_bodyContents  = {}
                d_seriesUID     = {}
                dl_bodyContents = []
                dl_seriesUID    = []
                str_reportBody  += "\n"
                str_reportSUID  += "\n"
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
                    d_study['body']             = dl_bodyContents
                    d_study['bodySeriesUID']    = dl_seriesUID
     
            l_studyHits.append(d_study)
            str_reportText      += str_reportHeader + str_reportBody
            str_reportTable     += "\n%s\n%s\n\n\n" % (tb_headerInstance.table, tb_bodyInstance.table)
            str_reportHeader    = ''
            str_reportBody      = ''

        return {
                "tabular":  str_reportTable, 
                "rawText":  str_reportText,
                "json":     l_studyHits
        }

    def command(self, opt={}):
        command = '-xi -S'
        str_cmd     = "%s %s %s %s" % (
                        self.executable,
                        command,
                        self.query(opt),
                        self.commandSuffix()
        )
        return str_cmd

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
        # we use a sorted dictionnary so we can test generated command 
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

    def systemlevel_run(self, opt, d_params):
        """
        Run the system command, based on the passed paramter dictionary
        """
        for k,v in d_params.items():
            opt[k]  = v
        raw_response= subprocess.run(
                        self.command(opt), 
                        stdout  = subprocess.PIPE, 
                        stderr  = subprocess.STDOUT, 
                        shell   = True
            )
        return self.formatResponse(raw_response)

    def run(self, opt={}):
        """
        Main entry method. 

        For some PACS, a query needs to be run in two phases:

            * First, at the STUDY level to receive the StudyUID
            * Then, given each STUDY, run at the SERIES level to
              receive the SeriesUID

        """
        # pudb.set_trace()

        formattedStudiesResponse    = \
            self.systemlevel_run(opt, {'QueryRetrieveLevel': 'STUDY'})

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
            
            # pudb.set_trace()
            if len(l_seriesResults):
                filteredStudiesResponse['data'].append(study)
                filteredStudiesResponse['data'][-1]['series']       = l_seriesResults

            formattedStudiesResponse['data'][studyIndex]['series']  = l_seriesResults
            studyIndex+=1

        # pudb.set_trace()
        d_report  = self.report_generate(filteredStudiesResponse)
        filteredStudiesResponse['report'] = d_report
        return filteredStudiesResponse

    def checkResponse(self, response):
        std_split = response.split('\n')
        info_count = 0
        error_count = 0
        for line in std_split:
            if line.startswith('I: '):
                info_count += 1
            elif line.startswith('E: '):
                error_count += 1

        status = 'error'
        if error_count == 0:
            status = 'success'

        return status

    def parseResponse(self, response):
        data = []

        uid = 0
        std_split = response.split('\n')

        for line in std_split:
            if line.startswith('I: ---------------------------'):
                data.append({})
                data[-1]['uid'] = {}
                data[-1]['uid']['tag'] = 0
                data[-1]['uid']['value'] = uid
                data[-1]['uid']['label'] = 'uid'
                uid += 1

            elif line.startswith('I: '):
                lineSplit = line.split()
                if len(lineSplit) >= 8 and re.search('\((.*?)\)', lineSplit[1]) != None:
                    # extract DICOM tag
                    tag = re.search('\((.*?)\)', lineSplit[1]).group(0)[1:-1].strip().replace('\x00', '')

                    # extract value
                    value = re.search('\[(.*?)\]', line)
                    if value != None:
                        value = value.group(0)[1:-1].strip().replace('\x00', '')
                    else:
                        value = 'no value provided'

                    # extract label
                    label = lineSplit[-1].strip()

                    data[-1][label] = {}
                    data[-1][label]['tag'] = tag
                    data[-1][label]['value'] = value
                    data[-1][label]['label'] = label

        return data

    def formatResponse(self, raw_response):
        std = raw_response.stdout.decode('ascii')
        response = {
            'status':   'success',
            'data':     '',
            'command':  raw_response.args
        }

        status = self.checkResponse(std)
        if status == 'error':
            response['status']  = 'error'
            response['data']    = std
        else:
            response['status']  = 'success'
            response['data']    = self.parseResponse(std)

        return response
