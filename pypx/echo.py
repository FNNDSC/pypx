# Global modules
import subprocess

# PYPX modules
from .base import Base

class Echo(Base):
    """docstring for Echo."""
    def __init__(self, arg):
        super(Echo, self).__init__(arg)

    def command(self):
        command = '--timeout 5' #5s timeout

        return self.executable + ' ' + command + ' ' + self.commandSuffix()

    def run(self):
        response = subprocess.run(
            self.command(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        return self.handle(response)
