from unittest import TestCase

import pypx

class TestEcho(TestCase):
    def test_echo_command(self):
        options = {
            'executable': '/bin/echoscu',
            'aec': 'MY-AEC',
            'aet': 'MY-AET',
            'server_ip': '192.168.1.110',
            'server_port': '4242'
            }
        output = pypx.echo(options)
        command = '/bin/echoscu --timeout 5  -aec MY-AEC -aet MY-AET 192.168.1.110 4242'
        self.assertEqual(output['command'], command)