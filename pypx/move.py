# Global modules
import subprocess

# PYPX modules
from .base import Base

class Move(Base):
    """docstring for Move."""
    def __init__(self, arg):
        super(Move, self).__init__(arg)

    def command(self, opt={}):
        command = '-aem ' + opt['aet_listener']
        command += ' -k QueryRetrieveLevel=SERIES'
        command += ' -k SeriesInstanceUID=' + opt['series_uid']

        print( self.executable + ' ' + command + ' ' + self.commandSuffix() )

        return self.executable + ' ' + command + ' ' + self.commandSuffix()
    
    def run(self, opt={}):
        print('run Move')

        print( opt )

        series_uids = opt['series_uids'].split(',')

        for series_uid in series_uids:
            opt['series_uid'] = series_uid
            response = subprocess.run(self.command(opt), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            print( response )

        return 'Yay!'