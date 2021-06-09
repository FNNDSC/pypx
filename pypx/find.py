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
from    pypx                import do
import  copy

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
