# Global modules
import  subprocess
import  pudb
import  json
import  pfmisc
from    pfmisc._colors      import  Colors

# PYPX modules
from .base import Base

class Move(Base):
    """
    The 'Move' class is essentially a stripped down module that
    simply performs a call to the system to run an appropriately
    constructed 'movescu' command.

    In some ways, the Move() class replicates/duplicates similar
    functionality in the Find() class. Future development might
    address this overlap more intelligently.
    """

    def __init__(self, arg):
        """
        Constructor.

        Largely simple/barebones constructor that calls the Base()
        and sets up the executable name.
        """

        super(Move, self).__init__(arg)
        self.dp     = pfmisc.debug(
                        verbosity   = self.verbosity,
                        within      = 'Find',
                        syslog      = False
        )
        self.log    = self.dp.qprint

    def movescu_command(self, opt={}):
        command = '-S --move ' + opt['aet']
        command += ' --timeout 5'
        command += ' -k QueryRetrieveLevel=SERIES'
        command += ' -k StudyInstanceUID='  + opt['study_uid']
        command += ' -k SeriesInstanceUID=' + opt['series_uid']

        str_cmd     = "%s %s %s" % (
                        self.movescu,
                        command,
                        self.commandSuffix()
        )
        return str_cmd

    def run(self, opt={}):

        # First, for dockerized run, (re)start the xinetd service
        # self.systemlevel_run(self.arg,
        #     {
        #         'executable':   'xinetd'
        #     }
        # )

        d_moveRun = self.systemlevel_run(self.arg,
                {
                    'f_commandGen':         self.movescu_command,
                    'series_uid':           opt['SeriesInstanceUID'],
                    'study_uid':            opt['StudyInstanceUID']
                }
        )

        return d_moveRun
