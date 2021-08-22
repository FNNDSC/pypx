# Global modules
import  subprocess
import  pudb
import  json
import  pfmisc
from    pfmisc._colors      import  Colors
from    argparse            import  Namespace

# PYPX modules
from    .base               import Base
from    pypx                import smdb

class Status(Base):
    """
    The 'Status' class provides a similar/related interface signature
    as the other pypx classes, tailored in this case to return status
    information on a previous retrieve event.

    Like a move/retrieve module, this class expects as target information
    a SeriesInstanceUID and StudyInstanceUD.

    Unlike the other pypx classes, status events are fully serviced by
    the smdb module.
    """

    def __init__(self, arg):
        """
        Constructor.

        Largely simple/barebones constructor that calls the Base()
        and sets up the executable name.
        """

        super(Status, self).__init__(arg)
        self.dp     = pfmisc.debug(
                        verbosity   = self.verbosity,
                        within      = 'Find',
                        syslog      = False
        )
        self.log    = self.dp.qprint
        self.db     = smdb.SMDB(
                        Namespace(str_logDir = self.arg['dblogbasepath'])
                    )

    def status_init(self):
        """
        Intialize the status model
        """
        d_status    = {
            'state' : {
                'study':    "NoStudyFound",
                'series':   "NoSeriesFound",
                'images':   "NoImagesFound",
            },
            'study'     : {},
            'series'    : {},
            'images'    : {
                'received'      : {'count'  : -1},
                'requested'     : {'count'  : -1},
                'packed'        : {'count'  : -1},
                'pushed'        : {'count'  : -1},
                'registered'    : {'count'  : -1}
            }
        }
        return d_status

    def run(self, opt={}) -> dict:
        # pudb.set_trace()
        d_status    : dict      = self.status_init()
        d_status.update(self.db.study_seriesContainsVerify(
                                        opt['StudyInstanceUID'],
                                        opt['SeriesInstanceUID'],
                                        opt['verifySeriesInStudy']
                                ))
        d_status['state']['study'] = d_status['study']['state']
        if opt['verifySeriesInStudy']:
            if 'seriesListInStudy' in d_status['study'].keys():
                if not d_status['study']['seriesListInStudy']['status']:
                    d_status['state']['series'] = 'SeriesNotInStudy'
                    return d_status
        if d_status['status']:
            d_status['images']          = self.db.series_receivedAndRequested(
                                            opt['SeriesInstanceUID']
                                        )
            d_status['state']['series'] = d_status['series']['state']
            d_status['state']['images'] = d_status['images']['state']
        return d_status
