import os
import subprocess
import datetime
import uuid
import shutil
import dicom
import configparser
import ptk.utils

class Listen():
    """docstring for Listen."""
    def __init__(self, args):
        self.tmp_directory = args['tmp_directory']
        self.log_directory = args['log_directory']
        self.data_directory = args['data_directory']

        os.makedirs(self.tmp_directory, exist_ok=True)
        os.makedirs(self.log_directory, exist_ok=True)
        os.makedirs(self.data_directory, exist_ok=True)

        # create unique directory to store inconming data
        self.uuid = str(uuid.uuid4())
        self.uuid_directory = os.path.join( self.tmp_directory, self.uuid)
        self.log_error = os.path.join(self.log_directory, 'err-' + self.uuid + '.txt')
        self.log_output = os.path.join(self.log_directory, 'out-' + self.uuid + '.txt')

        try:
            os.makedirs(self.uuid_directory)
        except OSError as e:
            errorfile = open(self.log_error, 'w')
            errorfile.write('Make ' + self.uuid_directory + ' directory\n')
            errorfile.write('Error number: ' + str(e.errno) + '\n')
            errorfile.write('File name: ' + e.filename + '\n')
            errorfile.write('Error message: ' + e.strerror + '\n')
            errorfile.close()

    def mkdir(self, path):
        
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except OSError as e:
                errorfile = open(self.log_error, 'w')
                errorfile.write('Make ' + path + ' directory\n')
                errorfile.write('Error number: ' + str(e.errno) + '\n')
                errorfile.write('File name: ' + e.filename + '\n')
                errorfile.write('Error message: ' + e.strerror + '\n')
                errorfile.close()

        if not os.path.exists(path):
            errorfile = open(self.log_error, 'w')
            errorfile.write('PatientDirectory doesn\'t exist:' + path + '\n')
            errorfile.close()
            raise NameError('PatientDirectory doesn\'t exist:' + path)

    def saveinfo(self, path, info):

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
            errorfile.write('PatientDirectory doesn\'t exist:' + path + '\n')
            errorfile.close()
            raise NameError('PatientDirectory doesn\'t exist:' + path)

    def run(self):

        # start listening to incoming data
        command = 'storescp -id -od "' + self.uuid_directory + '" -xcr "touch ' + self.uuid_directory + '/#c;touch ' + self.uuid_directory + '/#a" -pm -sp;'
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

        abs_files = [os.path.join(self.uuid_directory,f) for f in os.listdir(self.uuid_directory)]
        abs_dirs =  [f for f in list(abs_files) if os.path.isdir(f)]

        # Start logging
        outputfile = open(self.log_output, 'w')
        outputfile.write( 'UUID DIRECTORY:' + '\n')
        outputfile.write( self.uuid_directory + '\n')

        # Keep track of "receiving.series" files
        series_received = set()

        for directory in abs_dirs:

            outputfile.write( '>>>>>>>>>>> ' + directory + '\n')
            for data in os.listdir(directory):

                outputfile.write( '+++++ ' + data + '\n')
                abs_data = os.path.join(directory, data)
                dcm_info = dicom.read_file(abs_data)

                ###########
                # PATIENT
                #

                # fetch patient info
                patient_id = ptk.utils.sanitize(dcm_info.PatientID)
                patient_name = ptk.utils.sanitize(dcm_info.PatientName)
                outputfile.write( 'PatientID: ' + patient_id + '\n')
                outputfile.write( 'PatientName: ' + patient_name + '\n')

                # create patient directory
                abs_patient = os.path.join(self.data_directory, patient_id + '-' + patient_name)
                self.mkdir(abs_patient)

                # create patient.info file
                patient_info = configparser.ConfigParser()
                patient_info['PATIENT'] = {
                    'PatientID': patient_id,
                    'PatientName': patient_name
                }
                patient_info_path = os.path.join(abs_patient, 'patient.info')
                self.saveinfo(patient_info_path, patient_info)

                ###########
                # STUDY
                #

                # fetch study info
                study_description = ptk.utils.sanitize(dcm_info.StudyDescription)
                study_date = ptk.utils.sanitize(dcm_info.StudyDate)
                study_uid = ptk.utils.sanitize(dcm_info.StudyInstanceUID)
                outputfile.write( 'StudyDescription: ' + study_description + '\n')
                outputfile.write( 'StudyDate: ' + study_date + '\n')
                outputfile.write( 'StudyInstanceUID: ' + study_uid + '\n')

                # create study directory
                abs_study = os.path.join(abs_patient, study_description + '-' + study_date + '-' + study_uid)
                self.mkdir(abs_study)

               # create study.info file
                study_info = configparser.ConfigParser()
                study_info['STUDY'] = {
                    'StudyDescriptiont': study_description,
                    'StudyDate': study_date,
                    'StudyInstanceUID': study_uid
                }
                study_info_path = os.path.join(abs_study, 'study.info')
                self.saveinfo(study_info_path, study_info)

                ###########
                # SERIES
                #

                # fetch series info
                series_description = ptk.utils.sanitize(dcm_info.SeriesDescription)
                series_date = ptk.utils.sanitize(dcm_info.SeriesDate)
                series_uid = ptk.utils.sanitize(dcm_info.SeriesInstanceUID)
                outputfile.write( 'SeriesDescription: ' + series_description + '\n')
                outputfile.write( 'SeriesDate: ' + series_date + '\n')
                outputfile.write( 'SeriesInstanceUID: ' + series_uid + '\n')

                # create series directory
                abs_series = os.path.join(abs_study, series_description + '-' + series_date + '-' + series_uid)
                self.mkdir(abs_series)

               # create study.info file
                series_info = configparser.ConfigParser()
                series_info['SERIES'] = {
                    'SeriesDescription': series_description,
                    'SeriesDate': series_date,
                    'SeriesInstanceUID': series_uid
                }
                series_info_path = os.path.join(abs_series, 'receiving.series')
                series_received.add(series_info_path) 
                self.saveinfo(series_info_path, series_info)

                ###########
                # IMAGE
                #

                # fetch image info
                image_uid = ptk.utils.sanitize(dcm_info.SOPInstanceUID)
                image_instance_number = ptk.utils.sanitize(dcm_info.InstanceNumber)
                outputfile.write( 'SOPInstanceUID: ' + image_uid + '\n')
                outputfile.write( 'InstanceNumber: ' + image_instance_number + '\n')

                abs_image = os.path.join(abs_series, image_instance_number + '-' + image_uid + '.dcm')

                if not os.path.exists(abs_image):
                    try:
                        shutil.copy2(abs_data, abs_image)
                    except OSError as e:
                        errorfile = open(self.log_error, 'w')
                        errorfile.write('Copy ' + abs_data + ' to ' + self.abs_image + '\n')
                        errorfile.write('Error number: ' + str(e.errno) + '\n')
                        errorfile.write('File name: ' + e.filename + '\n')
                        errorfile.write('Error message: ' + e.strerror + '\n')
                        errorfile.close()

                if not os.path.exists(abs_image):
                    errorfile = open(self.log_error, 'w')
                    errorfile.write('PatientDirectory doesn\'t exist:' + abs_image + '\n')
                    errorfile.close()
                    raise NameError('PatientDirectory doesn\'t exist:' + abs_image)

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
        except OSError as e:
            errorfile = open(self.log_error, 'w')
            errorfile.write('Remove ' + self.uuid_directory + ' tree\n')
            errorfile.write('Error number: ' + str(e.errno) + '\n')
            errorfile.write('File name: ' + e.filename + '\n')
            errorfile.write('Error message: ' + e.strerror + '\n')
            errorfile.close()

        # what about log files?
        # import logger?

        outputfile.close()