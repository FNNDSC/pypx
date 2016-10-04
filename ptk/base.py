class Base():
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
            self.server_port = '4241'

        self.query = ''
        self.command_suffix = ''
        self.commandSuffix()

        self.response = {
            'status': 'error',
            'data': {}
        }

    def commandSuffix(self):
        # required parameters
        self.command_suffix = ' -aec ' + self.aec
        self.command_suffix += ' -aet ' + self.aet
        self.command_suffix += ' ' + self.server_ip
        self.command_suffix += ' ' + self.server_port