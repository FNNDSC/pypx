import subprocess
import ptk.utils

class Echo():
    """docstring for Echo."""
    def __init__(self, arg):
        ptk.utils.init(self, arg)
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
