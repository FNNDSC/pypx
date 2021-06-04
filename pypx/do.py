# Global modules
import  subprocess, re, collections
from pfmisc.other import list_removeDuplicates
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

class Do(Base):

    """
    The Do module provides a convient and centralised location
    from which to dispatch processing to a variety of additional
    operations.

    All these operations work on a study/series tuple, and this
    module iterates over structures that define this space.

    In many cases, the operations append to the JSON stream that
    "flows" through this module, adding some operation-specific
    information, which in turn can be consumed by a downstream
    process.

    """

    def __init__(self, arg):
        """
        Constructor. Nothing too fancy. Just a parent init
        and a class logging function.

        Most of the "complexity" here is "merging" upstream
        arg values with this specific app's arg values.

        """
        # Check if an upstream 'reportData' exists, and if so
        # merge those args with the current namespace:
        if 'reportData' in arg.keys():
            d_argCopy           = arg.copy()
            # "merge" these 'arg's with upstream.
            arg.update(arg['reportData']['args'])
            # Since this might overwrite some args specific to this
            # app, we update again to the copy.
            arg.update(d_argCopy)

        super(Do, self).__init__(arg)
        self.dp             = pfmisc.debug(
                                        verbosity   = self.verbosity,
                                        within      = 'Do',
                                        syslog      = False
                                        )
        self.log            = self.dp.qprint

    def run(self, opt={}) -> dict:
        """
        If a '--next' request has been specified in the class / module,
        perform additional actions on the space of find hits.

        These actions are typically either:

            * retrieve images
            * status query on retrieved images
            * find query on the internal smdb "database"
            * push images to a swift/CUBE

        and are performed with additional processing on the STUDY/SERIES
        level. This essentially loops over all the SeriesInstanceUID in the
        query space structure.

        For the special case of a dockerized run, this method will attempt
        to also restart the 'xinet.d' service within the container.

        NOTE: The architecture/infrastructure could be overwhelmed if
        too many concurrent requests are presented. Note that a separate
        `storescp` is spawned for EACH incoming DICOM file. Thus requesting
        multiple series (each with multiple DICOM files) in multiple studies
        all at once could result in thousands of `storescp` being spawned
        to try and handle the flood.
        """

        def countDownTimer_do(f_time):
            t               : int   = int(f_time)
            while t:
                mins, secs = divmod(t, 60)
                timer = '{:02d}:{:02d}'.format(mins, secs)
                if self.arg['withFeedBack']:
                    print("     ", end = '')
                    print(  Colors.BLUE_BCKGRND + Colors.WHITE +          \
                            "[ Parsing incoming images %s ]" % timer + Colors.NO_COLOUR
                    )
                time.sleep(1)
                if self.arg['withFeedBack']: print("\033[2A")
                t -= 1

        def seriesRetrieveDelay_do(str_line):
            """
            Simply delay processing a retrieve to prevent client
            overwhelm.

            Delay can be a simple fixed interval in (float) seconds,
            or if the delay is the string "dynamic" then delay by
            a function of the number of images retrieved.
            """
            factor  = 1
            f_sleep = 0.0
            if 'intraSeriesRetrieveDelay' in self.arg.keys():
                if 'dynamic' not in self.arg['intraSeriesRetrieveDelay']:
                    f_sleep = float(self.arg['intraSeriesRetrieveDelay'])
                else:
                    l_dynamic   = self.arg['intraSeriesRetrieveDelay'].split(':')
                    if len(l_dynamic) ==2:
                        factor  = int(l_dynamic[1])
                    l_words     = str_line.split()
                    images  = int(l_words[1])
                    f_sleep = float(images) / factor
                countDownTimer_do(f_sleep)

        def retrieve_do() -> dict:
            """
            Nested retrieve handler
            """
            nonlocal series, studyIndex, seriesIndex
            seriesInstances : int   = series['NumberOfSeriesRelatedInstances']['value']
            d_then          : dict  = {}
            d_db            : dict  = db.seriesMapMeta(
                                        'NumberOfSeriesRelatedInstances',
                                        seriesInstances
                                    )
            str_line        = presenter.seriesRetrieve_print(
                studyIndex  = studyIndex, seriesIndex = seriesIndex
            )
            if self.arg['withFeedBack']: self.log(str_line + "               ")
            series['SeriesMetaDescription']  = {
                                    'tag'   : "0,0",
                                    'value' : str_line,
                                    'label' : 'inlineRetrieveText'
                                }
            if self.move:
                d_then      = pypx.move({
                                **self.arg,
                            })
            else:
                d_then = self.systemlevel_run(self.arg,
                        {
                            'f_commandGen'      : self.movescu_command,
                            'series_uid'        : str_seriesUID,
                            'study_uid'         : str_studyUID
                        }
                )
            if 'intraSeriesRetrieveDelay' in self.arg.keys():
                if self.arg['intraSeriesRetrieveDelay']:
                    seriesRetrieveDelay_do(str_line)
            series['PACS_retrieve'] = {
                'requested' :   '%s' % datetime.now()
            }
            d_db    = db.seriesMapMeta('retrieve', d_then)
            return d_then

        def status_do() -> dict:
            """
            Nested status handler
            """
            nonlocal    series
            d_then      : dict  = {}

            # pudb.set_trace()
            self.arg['verifySeriesInStudy']   = True
            d_then      = pypx.status({
                            **self.arg,
                        })

            str_line    = presenter.seriesStatus_print(
                studyIndex  = studyIndex,
                seriesIndex = seriesIndex,
                status      = d_then
            )
            series['SeriesMetaDescription']    = {
                                    'tag'   : "0,0",
                                    'value' : str_line,
                                    'label' : 'inlineStatusText'
                                }
            if self.arg['withFeedBack']: self.log(str_line)

            return d_then


        # self.systemlevel_run(self.arg,
        #     {
        #         'f_commandGen': self.xinetd_command
        #     }
        # )

        db              = smdb.SMDB(
                            Namespace(str_logDir = self.arg['dblogbasepath'])
                        )
        db.housingDirs_create()
        d_filteredHits  = self.arg['reportData']

        # In the case of in-line updates on the progress of the
        # postprocess, we need to create a presentation/report object
        # which we can use for the reporting.
        # pudb.set_trace()
        presenter   = report.Report({
                                        'colorize' :    'dark',
                                        'reportData':   d_filteredHits
                                    })
        presenter.run()
        l_run           = []
        d_ret           = {
            'do'        : False
        }
        l_then          = self.arg['then'].split(',')
        b_headerPrinted = False
        for then in l_then:
            studyIndex  = 0
            d_ret['status'] = False
            for study in d_filteredHits['data']:
                l_run       = []
                seriesIndex = 0
                if self.arg['withFeedBack']:
                    print("")
                    print(  Colors.BLUE_BCKGRND + Colors.WHITE + "[ STUDY %s ]"\
                            % then + Colors.NO_COLOUR)
                    presenter.studyHeader_print(
                        studyIndex  = studyIndex, reportType = 'rawText'
                    )
                    print(  Colors.BLUE_BCKGRND + Colors.WHITE + "[ SERIES %s ]"\
                            % then + Colors.NO_COLOUR)
                for series in study['series']:
                    str_seriesDescription   = series['SeriesDescription']['value']
                    str_seriesUID           = series['SeriesInstanceUID']['value']
                    str_studyUID            = study['StudyInstanceUID']['value']
                    db.d_DICOM['SeriesInstanceUID'] = str_seriesUID
                    self.arg['SeriesInstanceUID']   = str_seriesUID
                    self.arg['StudyInstanceUID']    = str_studyUID
                    if then == "retrieve":  d_then  = retrieve_do()
                    if then == "status"  :  d_then  = status_do()
                    l_run.append(d_then)
                    seriesIndex += 1
                d_ret[then]             = { 'study' : []}
                d_ret[then]['study'].append({ study['StudyInstanceUID']['value'] : l_run})
                studyIndex += 1
                d_ret['do'] = True
        return d_ret

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

