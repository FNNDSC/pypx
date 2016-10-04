import subprocess

from .base import Base

class Echo(Base):
    """docstring for Echo."""
    def __init__(self, arg):
        super(Echo, self).__init__(arg)
        self.executable = 'echoscu'

    def command(self):
        command = ' --timeout 5' #5s timeout

        return self.executable + ' ' + command + ' ' + self.command_suffix

    def run(self):
        response = subprocess.run(self.command(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        result = self.handle(response)
        return result

    def handle(self, echo_response):
        std = echo_response.stdout.decode('ascii')
        response = {
            'status': 'success',
            'data': '',
            'command': echo_response.args
        }
        if std != '':
            response['status'] = 'error'
            response['data'] = std

        return response
