class Base():
    """docstring for Echo."""
    def __init__(self,arg):
        self.arg = arg

        if 'aet' in arg:
            self.aet = arg['aet']
        else:
            self.aet = 'CHRIS-ULTRON-AET'

        if 'aec' in arg:
            self.aec = arg['aec']
        else:
            self.aec = 'CHRIS-ULTRON-AEC'

        if 'server_ip' in arg:
            self.server_ip = arg['server_ip']
        else:
            self.server_ip = '192.168.1.110'

        if 'server_port' in arg:
            self.server_port = arg['server_port']
        else:
            self.server_port = '4242'

        if 'executable' in arg:
            self.executable = arg['executable']
        else:
            self.executable = '/usr/local/bin/echoscu'

        self.response = {
            'status': 'error',
            'data': {}
        }

    def commandSuffix(self):
        # required parameters
        command_suffix = ' -aec ' + self.aec
        command_suffix += ' -aet ' + self.aet
        command_suffix += ' ' + self.server_ip
        command_suffix += ' ' + self.server_port

        return command_suffix

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
