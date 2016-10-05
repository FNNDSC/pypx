# Global modules
import subprocess

# PTK modules
from .base import Base

class Echo(Base):
    """docstring for Echo."""
    def __init__(self, arg):
        super(Echo, self).__init__(arg)

    def command(self):
        command = '--timeout 5' #5s timeout

        return self.executable + ' ' + command + ' ' + self.commandSuffix()

    def run(self):
        response = subprocess.run(self.command(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        result = self.handle(response)
        return result

    def handle(self, raw_response):
        std = raw_response.stdout.decode('ascii')
        response = {
            'status': 'success',
            'data': '',
            'command': raw_response.args
        }
        if std != '':
            response['status'] = 'error'
            response['data'] = std

        return response
