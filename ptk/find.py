# Global modules
import subprocess, re

# PTK modules
from .base import Base

class Find(Base):
    """docstring for Find."""
    def __init__(self, arg):
        super(Find, self).__init__(arg)
        # to be moved out
        self.postfilter_parameters = {
            'PatientSex': '',
            'PerformedStationAETitle': '',
            'StudyDescription': '',
            'SeriesDescription': ''
        }

    def command(self, opt={}):
        command = '-xi -S'

        return self.executable + ' ' + command + ' ' + self.query(opt) + ' ' + self.commandSuffix()

    def query(self, opt={}):
        parameters = {
            'PatientID': '',                     # PATIENT INFORMATION
            'PatientName': '',
            'PatientBirthDate': '',
            'PatientSex': '',
            'StudyDate': '',                     # STUDY INFORMATION
            'StudyDescription': '',
            'StudyInstanceUID': '',
            'ModalitiesInStudy': '',
            'PerformedStationAETitle': '',
            'NumberOfSeriesRelatedInstances': '', # SERIES INFORMATION
            'InstanceNumber': '',
            'SeriesDate': '',
            'SeriesDescription': '',
            'SeriesInstanceUID': '',
            'QueryRetrieveLevel': 'SERIES'
        }

        query = ''
        for key, value in parameters.items():
            # update value if provided
            if key in opt:
                value = opt[key]
            # update query
            if value != '':
                query += ' -k "' + key + '=' + value + '"'
            else:
                query += ' -k ' + key

        return query

    def preparePostFilter(self):
        print('prepare post filter')
        # $post_filter['PatientSex'] = $patientsex;
        # $post_filter['PerformedStationAETitle'] = $station;
        # $post_filter['StudyDescription'] = $studydescription;
        # $post_filter['SeriesDescription'] = $seriesdescription;

    def run(self, opt={}):
        #
        #
        # find data
        response = subprocess.run(self.command(opt), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        # format response
        return self.formatResponse(response)

    def checkResponse(self, response):
        stdSplit = response.split('\n')
        infoCount = 0
        errorCount = 0
        for line in stdSplit:
            if line.startswith('I: '):
                infoCount += 1
            elif line.startswith('E: '):
                errorCount += 1

        status = 'error'
        if errorCount == 0:
            status = 'success'

        return status

    def parseResponse(self, response):
        data = []

        uid = 0
        stdSplit = response.split('\n')

        for line in stdSplit:
            if line.startswith('I: ---------------------------'):
                data.append({})
                data[-1]['uid'] = {}
                data[-1]['uid']['tag'] = 0
                data[-1]['uid']['value'] = uid
                data[-1]['uid']['label'] = 'uid'
                uid +=1

            elif line.startswith('I: '):
                lineSplit = line.split()
                if len(lineSplit) >= 8 and re.search('\((.*?)\)', lineSplit[1]) != None:
                    # extract DICOM tag
                    tag = re.search('\((.*?)\)', lineSplit[1]).group(0)[1:-1].strip().replace('\x00', '')

                    # extract value
                    value = re.search('\[(.*?)\]', line)
                    if value != None:
                        value = value.group(0)[1:-1].strip().replace('\x00', '')
                    else:
                        value = 'no value provided'

                    # extract label
                    label = lineSplit[-1].strip()

                    data[-1][label] = {}
                    data[-1][label]['tag'] = tag
                    data[-1][label]['value'] = value
                    data[-1][label]['label'] = label

        return data

    def formatResponse(self, raw_response):
        std = raw_response.stdout.decode('ascii')
        response = {
            'status': 'success',
            'data': '',
            'command': raw_response.args
        }

        status = self.checkResponse(std)
        if status == 'error':
            response['status'] = 'error'
            response['data'] = std
        else:
            response['status'] = 'success'
            response['data'] = self.parseResponse(std)

        return response
