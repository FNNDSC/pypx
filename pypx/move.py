# Global modules
import subprocess

# PYPX modules
from .base import Base

class Move(Base):
    """docstring for Move."""
    def __init__(self, arg):
        super(Move, self).__init__(arg)

    def command(self, opt={}):
        command = '--move ' + opt['aet_listener']
        command += ' --timeout 5'
        command += ' -k QueryRetrieveLevel=SERIES'
        command += ' -k SeriesInstanceUID=' + opt['series_uid']

        return self.executable + ' ' + command + ' ' + self.commandSuffix()

    def run(self, opt={}):
        response = subprocess.run(
            self.command(opt), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        return self.handle(response)
