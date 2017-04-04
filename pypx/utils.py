# Global modules
import os

def sanitize(value):
    # convert to string and remove trailing spaces
    tvalue = str(value).strip()
    # only keep alpha numeric characters and replace the rest by "_"
    svalue = "".join(character if character.isalnum() else '.' for character in tvalue)
    if not svalue:
        svalue = "no value provided"
    return svalue

def patientPath(data_directory, patient_id, patient_name):
    # should check validity of data_directory somehow
    return os.path.join(data_directory, sanitize(patient_id) + '-' + sanitize(patient_name))

def studyPath(patient_directory, study_description, study_date, study_uid):
    # should check validity of patient_directory somehow
    return os.path.join(
        patient_directory,
        sanitize(study_description) +
        '-' + sanitize(study_date) +
        '-' + sanitize(study_uid))

def seriesPath(study_directory, series_description, series_date, series_uid):
    # should check validity of study_directory somehow
    return os.path.join(
        study_directory,
        sanitize(series_description) +
        '-' + sanitize(series_date) +
        '-' + sanitize(series_uid))

def dataPath(series_directory, image_instance_number, image_uid):
    # should check validity of study_directory somehow

    # image_instance_number must be 5 characters long to appear nicely on filesystem
    #https://pyformat.info/#string_pad_align
    padded_image_instance_number = '{:0>5}'.format(sanitize(image_instance_number))
    return os.path.join(
        series_directory, padded_image_instance_number +
        '-' + sanitize(image_uid) + '.dcm')
