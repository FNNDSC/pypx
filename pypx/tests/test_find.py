from unittest import TestCase

import pypx

class TestFind(TestCase):
    def test_find_command(self):
        options = {
            'executable': '/bin/findscu',
            'aec': 'MY-AEC',
            'aet': 'MY-AET',
            'server_ip': '192.168.1.110',
            'server_port': '4242'
            }
        output = pypx.find(options)
        command = '\
/bin/findscu -xi -S  \
-k InstanceNumber \
-k ModalitiesInStudy \
-k NumberOfSeriesRelatedInstances \
-k PatientBirthDate \
-k PatientID \
-k PatientName \
-k PatientSex \
-k PerformedStationAETitle \
-k "QueryRetrieveLevel=SERIES" \
-k SeriesDate \
-k SeriesDescription \
-k SeriesInstanceUID \
-k StudyDate \
-k StudyDescription \
-k StudyInstanceUID  \
-aec MY-AEC -aet MY-AET 192.168.1.110 4242'

        self.maxDiff = None
        self.assertEqual(output['command'], command)