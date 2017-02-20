from unittest import TestCase

import pypx

class TestMove(TestCase):
    def test_move_command(self):
        options = {
            'executable': '/bin/movescu',
            'aec': 'MY-AEC',
            'aet': 'MY-AET',
            'aet_listener': 'LISTENER-AET',
            'series_uid': '123.354345.4545',
            'server_ip': '192.168.1.110',
            'server_port': '4242'
            }
        output = pypx.move(options)
        command = '/bin/movescu --move LISTENER-AET --timeout 5 \
-k QueryRetrieveLevel=SERIES \
-k SeriesInstanceUID=123.354345.4545  \
-aec MY-AEC -aet MY-AET 192.168.1.110 4242'
        self.assertEqual(output['command'], command)
