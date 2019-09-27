# Global modules
import  subprocess
import  pudb
import  json
import  pfmisc
from    pfmisc._colors      import  Colors

# PYPX modules
from .base import Base

class Echo(Base):
    """
    The 'Echo' class is essentially a stripped down module that 
    simply runs an 'echoscp' on the system shell.
    """

    def __init__(self, arg):
        """
        Constructor.

        Largely simple/barebones constructor that calls the Base()
        and sets up the executable name.
        """

        super(Echo, self).__init__(arg)
        self.dp = pfmisc.debug(
                    verbosity   = self.verbosity,
                    within      = 'Echo',
                    syslog      = False
        )

    def echoscu_command(self, opt={}):
        command = ' --timeout 5 -v '

        str_cmd     = "%s %s %s" % (
                        self.echoscu,
                        command,
                        self.commandSuffix()
        )
        return str_cmd

    def run(self, opt={}):

        d_echoRun = self.systemlevel_run(self.arg, 
                {
                    'f_commandGen':         self.echoscu_command
                }
        )

        return d_echoRun
