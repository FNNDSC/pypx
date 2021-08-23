# Global modules
import  subprocess, re, collections
import  pudb
import  json
import  sys

from    datetime            import  datetime
from    dateutil            import  relativedelta
from    terminaltables      import  SingleTable
from    argparse            import  Namespace
import  time

import  pfmisc
from    pfmisc._colors      import  Colors

# PYPX modules
from    .base               import Base
from    .move               import Move
import  pypx
from    pypx                import smdb

class Report(Base):

    """
    The Report module interprets JSON CLI output from other
    px scripts and generates/prints reports.
    """

    def reportTempate_construct(self, arg):
        """
        Construct the report based on either the internal
        default template, or a parsing of user specified
        CLI.
        """
        l_studyTags     : list  = []
        l_seriesTags    : list  = []

        b_reportSet     : bool  = False

        if 'reportTags' in arg.keys():
            if len(arg['reportTags']):
                self.d_reportTags   = json.loads(arg['reportTags'])
                b_reportSet         = True
        if not b_reportSet:
            self.d_reportTags       = \
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
                            "NumberOfStudyRelatedSeries",
                            "NumberOfStudyRelatedInstances"
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
            for t in [
                {'reportHeaderStudyTags' : ['header', 'study']},
                {'reportHeaderSeriesTags': ['header', 'series']},
                {'reportBodySeriesTags'  : ['body', 'series']}
            ]:
                for k, v in t.items():
                    if k in self.arg.keys():
                        if len(self.arg[k]):
                            self.d_reportTags[v[0]][v[1]] = \
                                self.arg[k].split(',')

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

        # This is the main JSON object that contains
        # reports
        self.d_report       : dict  = {}

        super(Report, self).__init__(arg)
        self.reportTempate_construct(arg)
        self.dp             = pfmisc.debug(
                                        verbosity   = self.verbosity,
                                        within      = 'Find',
                                        syslog      = False
                                        )
        self.log            = self.dp.qprint

    def report_generate(self):
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
            nonlocal seriesCount, studyCount
            try:
                str_value   = d_DICOMfields[str_DICOMtag]['value']
            except:
                # pudb.set_trace()
                if str_DICOMtag == 'PatientAge':
                    """
                    Sometimes the PatientAge is not returned
                    in the call to PACS. In this case, calculate
                    the age from the PatientBirthDate and StudyDate.
                    Note this my be unreliable!
                    """
                    str_value   = patientAge_calculate(d_DICOMfields)
                if str_DICOMtag == 'seriesStatus':
                    # pudb.set_trace()
                    if 'then' in self.arg['reportData']:
                        d_then      = self.arg['reportData']['then']
                        d_status    = [v for k, v in d_then.items() if 'status' in k][0]
                        d_study     = d_status['study'][studyCount]
                        l_series    = d_study[next(iter(d_study))]
                        d_series    = l_series[seriesCount]
                        str_value   = self.seriesStatus_print(
                            studyIndex          = studyCount,
                            seriesIndex         = seriesCount,
                            status              = d_series,
                            SeriesDescription   = d_DICOMfields['SeriesDescription']['value']
                                        )
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
                return "%s%30s%s  %-50s%s\n" % \
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
                    CheaderField    = Colors.LIGHT_PURPLE
                    CheaderValue    = Colors.LIGHT_GREEN
                if str_colorize == 'light':
                    CheaderField    = Colors.PURPLE
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

        def status_addToSeries():
            """
            Inject "status" related info into the body series line.
            """

        def body_generate(study, studyCount):
            """
            For a given 'study' structure, generate a body block
            in various formats. Typically, the body contains tags
            from the SERIES level. Note currently STUDY tags in the
            body are not supported.
            """
            str_reportSUID      = ""
            str_reportBody      = ""
            d_bodyFields        = self.d_reportTags['body']
            nonlocal            seriesCount
            for k in d_bodyFields.keys():
                l_bodyTable     = []
                l_suidTable     = []
                d_bodyContents  = {}
                d_seriesUID     = {}
                dl_bodyContents = []
                dl_seriesUID    = []
                l_seriesUIDtag  = [
                                    'SeriesInstanceUID',
                                    'SeriesNumber',
                                    'NumberOfSeriesRelatedInstances'
                                ]
                if k == 'series':
                    l_series    = study['series']
                    # if len(self.arg['reportBodySeriesTags']):
                    #     l_tags  = self.arg['reportBodySeriesTags'].split()
                    # else:
                    #     l_tags  = self.d_reportTags['body']['series']
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
                        
                        # Here, add some "hidden" elements in the JSON return
                        # suitable for additional processing and defined
                        # in the l_seriesUID list.
                        #
                        # First, check if a CLI '--seriesSpecial' has been passed,
                        # and if so, append to the "hidden" element list.
                        if 'seriesSpecial' in self.arg:
                            if len(self.arg['seriesSpecial']):
                                l_seriesUIDtag.append(self.arg['seriesSpecial'])
                        l_suidTable, str_reportSUID, d_seriesUID        = \
                            block_build(
                                    series,
                                    l_seriesUIDtag,
                                    l_suidTable,
                                    str_reportSUID,
                                    d_seriesUID
                            )
                        dl_seriesUID.append(d_seriesUID.copy())
                        seriesCount += 1

                    tb_bodyInstance = SingleTable(l_bodyTable)
                    tb_bodyInstance.inner_heading_row_border    = False

            return tb_bodyInstance.table, str_reportBody, dl_bodyContents, dl_seriesUID

        CheaderField, CheaderValue = colorize_set()

        l_tabularHits       = []
        l_rawTextHits       = []
        l_jsonHits          = []
        studyCount          = 0
        seriesCount         = 0
        for study in self.arg['reportData']['data']:
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
                body_generate(study, studyCount)

            l_tabularHits.append(d_tabular)
            l_rawTextHits.append(d_rawText)
            l_jsonHits.append(d_json)
            studyCount += 1

        return {
                "tabular":  l_tabularHits,
                "rawText":  l_rawTextHits,
                "json":     l_jsonHits
        }

    def toCSV(self, **kwargs):
        """
        Generate a csv version of the report, suitable for consumption
        by spreadsheets in raw form. Output can be prettified and
        summarized if chosen.
        """

        def cols_keystring(l_kv) -> str:
            """
            Return a <str_sep> string of the list in <l_kv>
            """
            l_headers   = [f + self.arg['csvSeparator'] for f in list(l_kv)[:-1]]
            l_headers.append(list(l_kv)[-1])
            return ''.join(l_headers)

        def maxWidthinList(l_lv) -> int:
            """
            Return the max length string that exists in the passed list
            """
            maxEl   = max(l_lv, key = len)
            return len(maxEl)

        def sumColElements(l_lv) -> int:
            """
            Return a summation of all the elements in a column.
            This assumes that column elements can be type cast
            to int values.
            """
            return sum([int(i) for i in l_lv])

        def padListToMax(l_lv) -> tuple:
            """
            Pad the string elements in a list to a fixed width
            """
            width       : int   = maxWidthinList(l_lv)+2
            l_padded    : list  = [ f.center(width) for f in l_lv ]
            return l_padded, width

        def padListToLeft(l_lv) -> tuple:
            """
            Pad the string elements in a list to a fixed width
            """
            width       : int   = maxWidthinList(l_lv)+2
            l_padded    : list  = [ f.ljust(width) for f in l_lv ]
            return l_padded, width

        def checkAndPrettify() -> bool:
            """
            If self.arg['csvPrettity'] is true, then edit some dictionaries
            keys and values in place -- mostly this means pre-checking for
            column width and replacing the separation character, and also
            creating table top, middle, and bottom ASCII box elements.
            """
            nonlocal ld_seriesDesc, d_header, ld_seriesUID
            l_padded    :   list    = []
            l_paddedK   :   list    = []
            l_paddedV   :   list    = []
            b_status                = False

            if self.arg['csvPrettify']:
                b_status            = True
                self.arg['csvSeparator']    = '│'
                if len(self.arg['reportBodySeriesTags']):
                    l_tag = self.arg['reportBodySeriesTags'].split(',')
                    for tag in l_tag:
                        l_padded, width     = padListToLeft([k[tag]  \
                                                    for k in ld_seriesDesc])
                        for i in range(0, len(ld_seriesDesc)):
                            ld_seriesDesc[i][tag]   = l_padded[i]
                else:
                    # Pad the SeriesDescription/UID
                    l_padded, width     = padListToMax([k['SeriesDescription']  \
                                                for k in ld_seriesDesc])
                    for i in range(0, len(ld_seriesDesc)):
                        ld_seriesDesc[i]['SeriesDescription']   = l_padded[i]

                    # Pad the NumberOfSeriesRelatedInstances
                    # The following is a cesspoll of ugliness, marginally saved
                    # by the check at least for the existence of this long column
                    str_colToJustify    = 'NumberOfSeriesRelatedInstances'
                    if str_colToJustify in ld_seriesUID[0]:
                        # Fix all numbers to 3 width and leading zeros
                        try:
                            l_w = ['%05d' % int(f[str_colToJustify]) for f in ld_seriesUID]
                        except:
                            l_w = [ld_seriesUID[0][str_colToJustify]]
                        # Now set the width of the first element
                        l_w[0] = l_w[0].center(len(str_colToJustify)+2)
                        # and pad the whole list to that width
                        l_padded, width     = padListToMax(l_w)
                        for i in range(0, len(ld_seriesUID)):
                            ld_seriesUID[i][str_colToJustify] = l_padded[i]

                # Pad Study key and values pairs to optional column header
                # as part of the prettification
                for k,v in d_header.items():
                    ml = max(len(k), len(v))+2
                    l_paddedK.append(k.center(ml))
                    l_paddedV.append(v.center(ml))
                d_header = dict(zip(l_paddedK, l_paddedV))
            return b_status

        def checkAndSummarize() -> bool:
            """
            If self.arg['csvSummarize'] is true, summarize the series related
            lists.
            """
            nonlocal ld_seriesDesc, ld_seriesUID
            b_status        = False
            str_colToSum    = 'NumberOfSeriesRelatedInstances'
            if self.arg['csvSummarize']:
                b_status    = True
                l_descriptionSummary    = [
                    'Study contains %d series' % len(ld_seriesDesc)
                ]
                l_instanceSummary       = [
                    'All series contain %d images' %                        \
                         sumColElements([ld_seriesUID[i][str_colToSum]      \
                             for i in range(0, len(ld_seriesUID))])
                ]
                ld_seriesDesc   = []
                ld_seriesDesc.append( {'%s' % 'SeriesDescription' : '%s' % l_descriptionSummary[0] })
                l_keys          = list(ld_seriesUID[0].keys())
                ld_seriesUID    = [{}]
                for k in l_keys:
                    ld_seriesUID[0][k]  = l_instanceSummary[0]
            return b_status

        def colHeaders_generate() -> str:
            """
            Generate the column headers
            """
            str_bodyLabels      : str   = ""
            str_headerLabels    : str   = cols_keystring(d_header.keys())
            if len(self.arg['reportBodySeriesTags']):
                l_tags  = self.arg['reportBodySeriesTags'].split(',')
                for tag in l_tags:
                    str_bodyLabels  += '%s%s' % (
                        tag.center(len(ld_seriesDesc[0][tag])),
                        self.arg['csvSeparator']
                    )
                str_bodyLabels  = str_bodyLabels[:-1]
            else:
                str_bodyLabels   = '%s%s%s' % (
                    'SeriesDescription'.center(len(ld_seriesDesc[0]['SeriesDescription'])),
                    self.arg['csvSeparator'],
                    'NumberOfSeriesRelatedInstances'.center(len(ld_seriesUID[0]['NumberOfSeriesRelatedInstances']))
                )
            return  str_headerLabels                        +\
                    self.arg['csvSeparator']                +\
                    str_bodyLabels                          +'\n'

        def tableCellBorders_generate(str_template):
            """
            Based on the passed template, generate the [Top|Middle|Bottom]
            table horizontal border lines.
            """
            nonlocal str_tableTop, str_tableMiddle, str_tableBottom
            l_str           = list(str_template)
            l_lined         = ['─'  if f != '│' else '│' for f in l_str  ]
            l_top           = [f    if f != '│' else '┬' for f in l_lined]
            l_middle        = [f    if f != '│' else '┼' for f in l_lined]
            l_bottom        = [f    if f != '│' else '┴' for f in l_lined]
            str_tableTop    = "".join(l_top)        + '\n'
            str_tableMiddle = "".join(l_middle)     + '\n'
            str_tableBottom = "".join(l_bottom)     + '\n'

        str_csvReport   :   str     = ''
        l_prettyPadded  :   list    = []
        b_summarizeDo   :   bool    = False
        b_prettifyDo    :   bool    = False
        str_tableTop    :   str     = ''
        str_tableMiddle :   str     = ''
        str_tableBottom :   str     = ''

        for d_study in self.d_report['json']:
            d_header            = d_study['header']
            ld_seriesDesc       = d_study['body']
            ld_seriesUID        = d_study['bodySeriesUID']
            b_summarizeDo       = checkAndSummarize()
            b_prettifyDo        = checkAndPrettify()
            str_columnHeaders   = colHeaders_generate()
            tableCellBorders_generate(str_columnHeaders)
            if self.arg['csvPrintHeaders']:
                if b_prettifyDo:    str_csvReport += str_tableTop
                str_csvReport   +=  str_columnHeaders
                if b_prettifyDo:    str_csvReport += str_tableMiddle
            else:
                if b_prettifyDo:    str_csvReport += str_tableTop
            str_headerVals      = cols_keystring(d_header.values())
            for ds,dn in zip(ld_seriesDesc, ld_seriesUID):
                if len(self.arg['reportBodySeriesTags']):
                    l_tags  = self.arg['reportBodySeriesTags'].split(',')
                    str_seriesVals  = ''
                    for tag in l_tags:
                        str_seriesVals  += '%s%s' % (
                            ds[tag],
                            self.arg['csvSeparator']
                        )
                    str_seriesVals  = str_seriesVals[:-1]
                else:
                    str_seriesVals  = '%s%s%s' % (
                            ds['SeriesDescription'],
                            self.arg['csvSeparator'],
                            dn['NumberOfSeriesRelatedInstances']
                    )
                str_csvReport   +=  str_headerVals                          +\
                                    self.arg['csvSeparator']                +\
                                    str_seriesVals                          +'\n'
            str_csvReport       =  str_csvReport[:-1]
            if b_prettifyDo: str_csvReport += '\n' + str_tableBottom
        return str_csvReport

    def studyHeader_print(self, **kwargs):
        """
        Print a study header based on the kwargs
        """
        studyIndex      : int   = -1
        str_reportType  : str   = 'rawText'
        for k,v in kwargs.items():
            if k == 'studyIndex'    : studyIndex        = int(v)
            if k == 'reportType'    : str_reportType    = v
        if studyIndex >= 0:
            if str_reportType in ['rawText', 'tabular']:
                self.log(self.d_report[str_reportType][studyIndex]['header'])
            else:
                self.log('Invalid reportType specified', comms = 'error')
        else:
            self.log('Invalid studyIndex referenced', comms = 'error')

    def report_getBodyField(self, studyIndex, seriesIndex, str_field) -> str:
        d_fieldBody = self.d_report['json'][studyIndex]['body'][seriesIndex]
        d_fieldMeta = self.d_report['json'][studyIndex]['bodySeriesUID'][seriesIndex]
        ret         = ""
        if str_field in d_fieldBody.keys():
            ret =  d_fieldBody[str_field]
        elif str_field in d_fieldMeta.keys():
            ret = d_fieldMeta[str_field]
        return ret

    def seriesRetrieve_print(self, **kwargs) -> str:
        """
        Return an inline study/series retrieve string based on the kwargs
        """
        studyIndex              : int   = -1
        seriesIndex             : int   = -1
        str_seriesInstances     : str   = ''
        str_seriesDescription   : str   = ''
        for k,v in kwargs.items():
            if k == 'studyIndex'    : studyIndex    = int(v)
            if k == 'seriesIndex'   : seriesIndex   = int(v)
        if studyIndex >= 0:
            if seriesIndex >= 0:
                str_seriesInstances = '%03d' %      \
                    int(self.report_getBodyField(studyIndex, seriesIndex,
                                            'NumberOfSeriesRelatedInstances'))
                str_seriesDescription   =           \
                    self.report_getBodyField(studyIndex, seriesIndex,
                                            'SeriesDescription')
                str_seriesNumber        =           \
                    self.report_getBodyField(studyIndex, seriesIndex,
                                            'SeriesNumber')
                if len(str_seriesNumber):
                    str_seriesNumber    = ' [ %04d ] ' % int(str_seriesNumber)
                str_line                =                                \
                                            'Requesting '               +\
                                            str_seriesInstances         +\
                                            ' images for '
                str_line = '%31s' % str_line + str_seriesNumber  + str_seriesDescription
            else:
                str_line    = 'Invalid seriesIndex specified'
        else:
            str_line    = 'Invalid studyIndex specified'
        return str_line

    def seriesStatus_print(self, **kwargs) -> str:
        """
        Return an inline study/series status string based on the kwargs
        """
        studyIndex              : int   = -1
        seriesIndex             : int   = -1
        str_seriesInstances     : str   = ''
        str_seriesDescription   : str   = ''
        str_seriesInstanceUID   : str   = ''
        str_line                : str   = ''
        d_status                : dict  = {}
        for k,v in kwargs.items():
            if k == 'studyIndex'        : studyIndex            = int(v)
            if k == 'seriesIndex'       : seriesIndex           = int(v)
            if k == 'status'            : d_status              = v
            if k == 'SeriesDescription' : str_seriesDescription = v
            if k == 'SeriesInstanceUID' : str_seriesInstanceUID = v
        if studyIndex >= 0:
            if seriesIndex >= 0:
                str_receivedCount       = '%03d' % d_status['images']['received']['count']
                str_requestedCount      = '%03d' % d_status['images']['requested']['count']
                str_packedCount         = '%03d' % d_status['images']['packed']['count']
                str_pushedCount         = '%03d' % d_status['images']['pushed']['count']
                str_registeredCount     = '%03d' % d_status['images']['registered']['count']
                str_status              = '%25s : %20s : %20s ' % \
                    (
                        d_status['state']['study'],
                        d_status['state']['series'],
                        d_status['state']['images']
                     )
                if not len(str_seriesDescription):
                    try:
                        str_seriesDescription   =           \
                            self.report_getBodyField(studyIndex, seriesIndex,
                                                    'SeriesDescription')
                    except:
                        str_seriesDescription   = ''
                if not len(str_seriesInstanceUID):
                    try:
                        str_seriesInstanceUID   =           \
                            self.report_getBodyField(studyIndex, seriesIndex,
                                                    'SeriesInstanceUID')
                    except:
                        str_seriesInstanceUID   = ''
                if d_status['status']:
                    str_line                =  \
                        ' [ PACS:%s/JSON:%s/DCM:%s/PUSH:%s/REG:%s ] │ ' %                             \
                            (
                                str_receivedCount, str_requestedCount, str_packedCount,
                                str_pushedCount, str_registeredCount
                            )
                else:
                    str_line                =  str_status

                str_line += ' ' + str_seriesDescription
                str_line = '%-100s' % str_line
                if len(str_seriesInstanceUID):
                    str_line += ' │ ' + str_seriesInstanceUID
            else:
                str_line    = 'Invalid seriesIndex specified'
        else:
            str_line    = 'Invalid studyIndex specified'
        return str_line

    def seriesPush_print(self, **kwargs) -> str:
        """
        Return an inline study/series push string based on the kwargs
        """
        studyIndex              : int   = -1
        seriesIndex             : int   = -1
        str_seriesInstances     : str   = ''
        str_seriesDescription   : str   = ''
        str_line                : str   = ''
        d_count                 : dict  = {}
        for k,v in kwargs.items():
            if k == 'studyIndex'        : studyIndex    = int(v)
            if k == 'seriesIndex'       : seriesIndex   = int(v)
            if k == 'fileCounts'        : d_count       = v
        if studyIndex >= 0:
            if seriesIndex >= 0:
                str_receivedCount       = '%03d' % d_count['received']['count']
                str_requestedCount      = '%03d' % d_count['requested']['count']
                str_seriesDescription   =           \
                    self.report_getBodyField(studyIndex, seriesIndex,
                                            'SeriesDescription')
                str_seriesInstanceUID   =           \
                    self.report_getBodyField(studyIndex, seriesIndex,
                                            'SeriesInstanceUID')

                str_line += str_seriesDescription
                str_line = '%-50s' % str_line
                str_line = "Pushing [ %s ]: "    \
                            % (str_receivedCount)       \
                            + str_line + str_seriesInstanceUID
            else:
                str_line    = 'Invalid seriesIndex specified'
        else:
            str_line    = 'Invalid studyIndex specified'
        return str_line

    def seriesRegister_print(self, **kwargs) -> str:
        """
        Return an inline study/series register string based on the kwargs
        """
        studyIndex              : int   = -1
        seriesIndex             : int   = -1
        str_seriesInstances     : str   = ''
        str_seriesDescription   : str   = ''
        str_line                : str   = ''
        d_count                 : dict  = {}
        for k,v in kwargs.items():
            if k == 'studyIndex'        : studyIndex    = int(v)
            if k == 'seriesIndex'       : seriesIndex   = int(v)
            if k == 'fileCounts'        : d_count       = v
        if studyIndex >= 0:
            if seriesIndex >= 0:
                str_receivedCount       = '%03d' % d_count['received']['count']
                str_requestedCount      = '%03d' % d_count['requested']['count']
                str_seriesDescription   =           \
                    self.report_getBodyField(studyIndex, seriesIndex,
                                            'SeriesDescription')
                str_seriesInstanceUID   =           \
                    self.report_getBodyField(studyIndex, seriesIndex,
                                            'SeriesInstanceUID')

                str_line += str_seriesDescription
                str_line = '%-50s' % str_line
                str_line = "Registering [ %s ]: "    \
                            % (str_receivedCount)       \
                            + str_line + str_seriesInstanceUID
            else:
                str_line    = 'Invalid seriesIndex specified'
        else:
            str_line    = 'Invalid studyIndex specified'
        return str_line

    def seriesReport_print(self, **kwargs) -> str:
        """
        Return an inline study/series register string based on the kwargs
        """
        studyIndex              : int   = -1
        seriesIndex             : int   = -1
        instanceNumber          : str   = ''
        str_seriesInstances     : str   = ''
        str_seriesDescription   : str   = ''
        str_line                : str   = ''
        for k,v in kwargs.items():
            if k == 'studyIndex'        : studyIndex        = int(v)
            if k == 'seriesIndex'       : seriesIndex       = int(v)
            if k == 'instanceNumber'    : instanceNumber    = v
        if studyIndex >= 0:
            if seriesIndex >= 0:
                str_seriesDescription   =           \
                    self.report_getBodyField(studyIndex, seriesIndex,
                                            'SeriesDescription')
                str_seriesInstanceUID   =           \
                    self.report_getBodyField(studyIndex, seriesIndex,
                                            'SeriesInstanceUID')
                str_seriesNumber        =           \
                    self.report_getBodyField(studyIndex, seriesIndex,
                                            'SeriesNumber')
                # Uncomment to show the InstanceNumber. This is NOT the same
                # as the SeriesNumber, which isn't available at a QUERY level.
                # The InstanceNumber in practice seemed less useful, so for now
                # it is commented out.
                # try:
                #     str_line = '[ %03d ] ' % int(instanceNumber)
                # except:
                #     str_line = '[ --- ] '
                str_line += str_seriesDescription
                str_line = '%-55s' % str_line
                str_line += str_seriesInstanceUID
            else:
                str_line    = 'Invalid seriesIndex specified'
        else:
            str_line    = 'Invalid studyIndex specified'
        return str_line

    def report_print(self):
        """
        Print a report based on one of the <str_field> arguments.
        """
        str_field   = self.printReport
        if str_field == 'tabular' or str_field == 'rawText':
            for d_hit in self.d_report[str_field]:
                print("%s\n%s\n" % (d_hit['header'], d_hit['body']))
        elif str_field == 'csv':
            print(self.toCSV()
            )
        else:
            print(
                json.dumps(
                    self.d_report['json'],
                    indent = 4
                )
            )

    def run(self, opt={}):
        """
        Main entry method.

        Interpret the JSON payload and generate a CLI report.

        This method mainly concerns itself with logic around
        interpreting if input JSON data is valid.

        """

        b_status        : bool      = True

        if 'reportDataFile' in self.arg:
            if len(self.arg['reportDataFile']):
                try:
                    with open(self.arg['reportDataFile']) as f:
                        self.arg['reportData'] = json.load(f)
                except Exception as e:
                    print("While attempting to read %s,\n%s" % \
                        (
                            self.arg['reportDataFile'],
                            '%s' % e
                        )
                    )
                    b_status    = False

        if 'status' in self.arg['reportData']:
            if not self.arg['reportData']['status'] or \
                   'error' in self.arg['reportData']['status']:
                self.log(   'An error has been flagged in the report payload.',
                            comms = 'error')
                self.log(   '\n%s\n' % json.dumps(self.arg['reportData'], indent = 4),
                            comms = 'status')
                b_status    = False

        if b_status:
            self.d_report   = self.report_generate()
            if len(self.printReport):
                if self.printReport in self.d_report.keys() or              \
                    self.printReport == 'csv':
                    self.report_print()

        if 'b_json' in self.arg:
            if self.arg['b_json']:
                return json.dumps(self.arg['reportData'])
