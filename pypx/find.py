# Global modules
import subprocess, re, collections

# PYPX modules
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
            'PatientAge': '',
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
        # we use a sorted dictionnary so we can test generated command more easily
        ordered = collections.OrderedDict(sorted(parameters.items(), key=lambda t: t[0]))
        for key, value in ordered.items():
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

        #
        #
        # Run query at Study level first
        # BCH and MGH does not directly allow MRN query at Series level
        opt['QueryRetrieveLevel'] = 'STUDY';

        response = subprocess.run(
            self.command(opt), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        # format response
        formattedStudies = self.formatResponse(response)

        print(formattedStudies)

        results = []

        for study in formattedStudies['data']:
            studyInstanceUID = study['StudyInstanceUID']['value']
            opt['QueryRetrieveLevel'] = 'SERIES';
            opt['StudyInstanceUID'] = studyInstanceUID;
            studyResponse = subprocess.run(
                self.command(opt), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            # print(self.formatResponse(studyResponse))
            formattedStudy = self.formatResponse(studyResponse)

            for series in formattedStudy['data']:
                series['command'] = {}
                series['command']['tag'] = 0
                series['command']['value'] = formattedStudy['command']
                series['command']['label'] = 'command'

                series['status'] = {}
                series['status']['tag'] = 0
                series['status']['value'] = formattedStudy['status']
                series['status']['label'] = 'status'

                results.append(series)

        formattedStudies['dataStudy'] = formattedStudies['data'];
        formattedStudies['data'] = results;
        
        return formattedStudies


    def checkResponse(self, response):
        std_split = response.split('\n')
        info_count = 0
        error_count = 0
        for line in std_split:
            if line.startswith('I: '):
                info_count += 1
            elif line.startswith('E: '):
                error_count += 1

        status = 'error'
        if error_count == 0:
            status = 'success'

        return status

    def parseResponse(self, response):
        data = []

        uid = 0
        std_split = response.split('\n')

        for line in std_split:
            if line.startswith('I: ---------------------------'):
                data.append({})
                data[-1]['uid'] = {}
                data[-1]['uid']['tag'] = 0
                data[-1]['uid']['value'] = uid
                data[-1]['uid']['label'] = 'uid'
                uid += 1

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
