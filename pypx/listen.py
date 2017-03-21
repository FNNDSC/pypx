# Global modules
import os
import subprocess
import uuid
import shutil
import configparser

# PyDicom module
import dicom

# PYPX modules
import pypx.utils

class Listen():
    """docstring for Listen."""
    def __init__(self, args):
        self.tmp_directory = args['tmp_directory']
        self.log_directory = args['log_directory']
        self.data_directory = args['data_directory']
        self.executable = args['executable']

        # maybe it should not create it, as it is a requirement
        os.makedirs(self.tmp_directory, exist_ok=True)
        os.makedirs(self.log_directory, exist_ok=True)
        os.makedirs(self.data_directory, exist_ok=True)

        # create unique directory to store inconming data
        self.uuid = str(uuid.uuid4())
        self.uuid_directory = os.path.join(self.tmp_directory, self.uuid)
        self.log_error = os.path.join(self.log_directory, 'err-' + self.uuid + '.txt')
        self.log_output = os.path.join(self.log_directory, 'out-' + self.uuid + '.txt')

        self.mkdir(self.uuid_directory, self.log_error)

    def mkdir(self, path, log_file):

        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except OSError as e:
                errorfile = open(log_file, 'w')
                errorfile.write('Make ' + path + ' directory\n')
                errorfile.write('Error number: ' + str(e.errno) + '\n')
                errorfile.write('File name: ' + e.filename + '\n')
                errorfile.write('Error message: ' + e.strerror + '\n')
                errorfile.close()

        if not os.path.exists(path):
            errorfile = open(log_file, 'w')
            errorfile.write('File doesn\'t exist:' + path + '\n')
            errorfile.close()
            raise NameError('File doesn\'t exist:' + path)

    def saveInformation(self, path, info):

        if not os.path.exists(path):

            with open(path, 'w') as info_file:
                try:
                    info.write(info_file)
                except OSError as e:
                    errorfile = open(self.log_error, 'w')
                    errorfile.write('Write ' + path + ' file\n')
                    errorfile.write('Error number: ' + str(e.errno) + '\n')
                    errorfile.write('File name: ' + e.filename + '\n')
                    errorfile.write('Error message: ' + e.strerror + '\n')
                    errorfile.close()

        if not os.path.exists(path):
            errorfile = open(self.log_error, 'w')
            errorfile.write('File doesn\'t exist:' + path + '\n')
            errorfile.close()
            raise NameError('File doesn\'t exist:' + path)

    def processDicomField(self, dcm_info, field):
        value = "undefined"
        if field in dcm_info:
            value = pypx.utils.sanitize(dcm_info.data_element(field).value)
        return value

    def processPatient(self, dcm_info, log_file, data_directory):
        # get information of interest
        patient_id = self.processDicomField(dcm_info, "PatientID")
        patient_name = self.processDicomField(dcm_info, "PatientName")

        # log it
        log_file.write('    PatientID: ' + patient_id + '\n')
        log_file.write('    PatientName: ' + patient_name + '\n')

        # create patient directory
        patient_directory = pypx.utils.patientPath(data_directory, patient_id, patient_name)
        self.mkdir(patient_directory, self.log_error)

        # create patient.info file
        patient_info = configparser.ConfigParser()
        patient_info['PATIENT'] = {
            'PatientID': patient_id,
            'PatientName': patient_name,
            'Location': patient_directory
        }

        return patient_info

    def processStudy(self, dcm_info, log_file, patient_directory):
        # get information of interest
        study_description = self.processDicomField(dcm_info, "StudyDescription")
        study_date = self.processDicomField(dcm_info, "StudyDate")
        study_uid = self.processDicomField(dcm_info, "StudyInstanceUID")

        # log it
        log_file.write('      StudyDescription: ' + study_description + '\n')
        log_file.write('      StudyDate: ' + study_date + '\n')
        log_file.write('      StudyInstanceUID: ' + study_uid + '\n')

        # create study directory
        study_directory = pypx.utils.studyPath(
            patient_directory, study_description, study_date, study_uid)
        self.mkdir(study_directory, self.log_error)

        # create study.info file
        study_info = configparser.ConfigParser()
        study_info['STUDY'] = {
            'StudyDescription': study_description,
            'StudyDate': study_date,
            'StudyInstanceUID': study_uid,
            'Location': study_directory
        }

        return study_info

    def processSeries(self, dcm_info, log_file, study_directory):
        # get information of interest
        series_description = self.processDicomField(dcm_info, "SeriesDescription")
        series_date = self.processDicomField(dcm_info, "SeriesDate")
        series_uid = self.processDicomField(dcm_info, "SeriesInstanceUID")

        # log it
        log_file.write('        SeriesDescription: ' + series_description + '\n')
        log_file.write('        SeriesDate: ' + series_date + '\n')
        log_file.write('        SeriesInstanceUID: ' + series_uid + '\n')

        # create series directory
        series_directory = pypx.utils.seriesPath(
            study_directory, series_description, series_date, series_uid)
        self.mkdir(series_directory, self.log_error)

        # store information as a configuration
        series_info = configparser.ConfigParser()
        series_info['SERIES'] = {
            'SeriesDescription': series_description,
            'SeriesDate': series_date,
            'SeriesInstanceUID': series_uid,
            'Location': series_directory
        }

        return series_info

    def processImage(self, dcm_info, log_file, error_file, series_directory, tmp_file):
        # get information of interest
        image_uid = self.processDicomField(dcm_info, "SOPInstanceUID")
        image_instance_number = self.processDicomField(dcm_info, "InstanceNumber")

        # log it
        log_file.write('          SOPInstanceUID: ' + image_uid + '\n')
        log_file.write('          InstanceNumber: ' + image_instance_number + '\n')

        image_path = pypx.utils.dataPath(series_directory, image_instance_number, image_uid)

        if not os.path.exists(image_path):
            try:
                shutil.copy2(tmp_file, image_path)
            except OSError as e:
                errorfile = open(error_file, 'w')
                errorfile.write('Copy ' + tmp_file + ' to ' + image_path + '\n')
                errorfile.write('Error number: ' + str(e.errno) + '\n')
                errorfile.write('File name: ' + e.filename + '\n')
                errorfile.write('Error message: ' + e.strerror + '\n')
                errorfile.close()

        if not os.path.exists(image_path):
            errorfile = open(error_file, 'w')
            errorfile.write('File doesn\'t exist:' + image_path + '\n')
            errorfile.close()
            raise NameError('File doesn\'t exist:' + image_path)

    def run(self):

        # start listening to incoming data
        command = self.executable + ' -id -od "' + \
          self.uuid_directory + '" -xcr "touch ' + \
          self.uuid_directory + '/#c;touch ' + \
          self.uuid_directory + '/#a" -pm -sp;'
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

        abs_files = [os.path.join(self.uuid_directory,f) for f in os.listdir(self.uuid_directory)]
        abs_dirs = [f for f in list(abs_files) if os.path.isdir(f)]

        # Start logging
        stdout_file = open(self.log_output, 'w')
        stdout_file.write('UUID DIRECTORY:' + '\n')
        stdout_file.write(self.uuid_directory + '\n')

        # Keep track of "receiving.series" files
        series_received = set()

        for directory in abs_dirs:

            stdout_file.write('> ' + directory + '\n')
            for data in os.listdir(directory):

                stdout_file.write('>>> ' + data + '\n')
                # abs path to data
                abs_data = os.path.join(directory, data)
                dcm_info = dicom.read_file(abs_data)

                # process patient
                patient_info = self.processPatient(dcm_info, stdout_file, self.data_directory)
                patient_info_path = os.path.join(
                    patient_info['PATIENT']['Location'], 'patient.info')
                self.saveInformation(patient_info_path, patient_info)

                # process study
                study_info = self.processStudy(
                    dcm_info, stdout_file, patient_info['PATIENT']['Location'])
                study_info_path = os.path.join(study_info['STUDY']['Location'], 'study.info')
                self.saveInformation(study_info_path, study_info)

                # process series
                series_info = self.processSeries(
                    dcm_info, stdout_file, study_info['STUDY']['Location'])
                series_info_path = os.path.join(
                    series_info['SERIES']['Location'], 'receiving.series')
                self.saveInformation(series_info_path, series_info)
                # keep track of series we are receiving
                # receiving.series will be rename to series.info
                # when all the series has been received
                series_received.add(series_info_path)

                # process image
                self.processImage(
                    dcm_info, stdout_file, self.log_error,
                    series_info['SERIES']['Location'], abs_data)
                # image.info file
                # mri_info? :/

        # rename receiving.series to series.info
        # changing name lets external applications know the incoming data has been received
        for series in series_received:
            last_index = series.rfind('receiving.series')
            target = series[:last_index] + 'series.info'
            os.rename(series, target)

        # cleanup
        try:
            shutil.rmtree(self.uuid_directory)
        except OSError as err:
            errorfile = open(self.log_error, 'w')
            errorfile.write('Remove ' + self.uuid_directory + ' tree\n')
            errorfile.write('Error number: ' + str(err.errno) + '\n')
            errorfile.write('File name: ' + err.filename + '\n')
            errorfile.write('Error message: ' + err.strerror + '\n')
            errorfile.close()

        # what about log files?
        # import logger?

        stdout_file.close()
