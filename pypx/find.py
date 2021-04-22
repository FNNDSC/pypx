# Global modules
import  subprocess, re, collections
import  pudb
import  json

from    datetime            import  datetime
from    dateutil            import  relativedelta
from    terminaltables      import  SingleTable
from    argparse            import  Namespace
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

    def retrieve_request(self, d_filteredHits):
        """
        Perform a request to "move" the image data at SERIES level.

        This essentially loops over all the SeriesInstanceUID in the
        query space structure.

        For the special case of a dockerized run, this method will attempt
        to also restart the 'xinet.d' service within the container.

        NOTE: Some PACS servers require the StudyInstanceUID in addition
        to the SeriesInstanceUID, hence this method provides both in
        the movescu request.

        NOTE: The architecture/infrastructure could be overwhelmed if
        too many concurrent requests are presented. Note that a separate
        `storescp` is spawned for EACH incoming DICOM file. Thus requesting
        multiple series (each with multiple DICOM files) in multiple studies
        all at once could result in thousands of `storescp` being spawned
        to try and handle the flood.
        """

        self.systemlevel_run(self.arg,
            {
                'f_commandGen': self.xinetd_command
            }
        )

        db          = smdb.SMDB(
                        Namespace(str_logDir = self.arg['dblogbasepath'])
                    )
        db.housingDirs_create()
        studyIndex  = 0
        l_run       = []

        # In the case of in-line updates on the progress of the
        # retrieve, we need to create a presentation/report object
        # which we can use for the reporting.
        presenter   = report.Report({
                                        'colorize' :    'dark',
                                        'reportData':   d_filteredHits
                                    })
        presenter.run()
        for study in d_filteredHits['data']:
            seriesIndex = 0
            if self.arg['retrieveFeedBack']:
                presenter.studyHeader_print(
                    studyIndex  = studyIndex, reportType = 'rawText'
                )
            for series in study['series']:
                str_seriesDescription   = series['SeriesDescription']['value']
                str_seriesUID           = series['SeriesInstanceUID']['value']
                seriesInstances         = series['NumberOfSeriesRelatedInstances']['value']
                str_studyUID            = study['StudyInstanceUID']['value']
                db.d_DICOM['SeriesInstanceUID'] = str_seriesUID
                d_db                    = db.seriesMapMeta(
                                                'NumberOfSeriesRelatedInstances',
                                                seriesInstances
                                        )
                if self.arg['retrieveFeedBack']:
                    presenter.seriesRetrieve_print(
                        studyIndex  = studyIndex, seriesIndex = seriesIndex
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
                                'f_commandGen'      : self.movescu_command,
                                'series_uid'        : str_seriesUID,
                                'study_uid'         : str_studyUID
                            }
                    )
                d_db    = db.seriesMapMeta(
                    'retrieve', d_moveRun
                )
                l_run.append(d_moveRun)
                series['PACS_retrieve'] = {
                    'requested' :   '%s' % datetime.now()
                }
                seriesIndex += 1
            studyIndex += 1
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
                    filteredStudiesResponse['data'][-1]['series']           \
                        = l_seriesResults

                formattedStudiesResponse['data'][studyIndex]['series']      \
                    = l_seriesResults
                studyIndex+=1

            if self.retrieve: self.retrieve_request(filteredStudiesResponse)
            return filteredStudiesResponse
        else:
            return formattedStudiesResponse
