
# Perform a find on a given PatientID
docker run  --rm -ti -v $PWD/dicom:/home/dicom                                 \
                   local/pypx                                                  \
                   --px-find                                                   \
                   --aet CHRISLOCAL                                            \
                   --aec ORTHANC                                               \
                   --serverIP  192.168.1.189                                   \
                   --serverPort 4242                                           \
                   --PatientID 4780041                                         \
                   --db /home/dicom/log                                        \
                   --verbosity 1                                               \
                   --json
                   
# Perform a find and generate a report
docker run  --rm -ti -v $PWD/dicom:/home/dicom                                 \
                   local/pypx                                                  \
                   --px-find                                                   \
                   --aet CHRISLOCAL                                            \
                   --aec ORTHANC                                               \
                   --serverIP  192.168.1.189                                   \
                   --serverPort 4242                                           \
                   --PatientID 4780041                                         \
                   --db /home/dicom/log                                        \
                   --verbosity 1                                               \
                   --json                                                     |\
docker run --rm -i -v $PWD/dicom:/home/dicom                                   \
                   local/pypx                                                  \
                   --px-report                                                 \
                   --colorize dark                                             \
                   --printReport csv --csvPrettify --csvPrintHeaders           \
                   --reportHeaderStudyTags PatientName,PatientID
                   
# Perform a find then retrieve on a given PatientID
docker run  --rm -ti -v $PWD/dicom:/home/dicom                                 \
                   local/pypx                                                  \
                   --px-find                                                   \
                   --then retrieve                                             \
                   --aet CHRISLOCAL                                            \
                   --aec ORTHANC                                               \
                   --serverIP  192.168.1.189                                   \
                   --serverPort 4242                                           \
                   --PatientID 4780041                                         \
                   --db /home/dicom/log                                        \
                   --verbosity 1                                               \
                   --json

# Read an upstream find.json                   
docker run  --rm -ti -v $PWD/dicom:/home/dicom                                 \
                   local/pypx                                                  \
                   --px-do                                                     \
                   --db /home/dicom/log                                        \ 
                   --reportDataFile /home/dicom/find.json                      \
                   --then status                                               \
                   --withFeedBack                                              \
                   --verbosity 1               
                   
# Input from an upstream find.json
docker run  --rm -i -v $PWD/dicom:/home/dicom                                  \
                   local/pypx                                                  \
                   --px-do                                                     \
                   --db /home/dicom/log                                        \
                   --then status                                               \
                   --withFeedBack                                              \
                   --verbosity 1  < find.json
             
# Retrieve from an upstream find.json
docker run  --rm -i -v $PWD/dicom:/home/dicom                                  \
                   -p 11113:11113                                              \
                   local/pypx                                                  \
                   --px-do                                                     \
                   --db /home/dicom/log                                        \ 
                   --then retrieve,status,status                               \
                   --intraSeriesRetrieveDelay dynamic:6                        \
                   --withFeedBack                                              \
                   --verbosity 1  < find.json


             
# Perform a find then retrieve on a given PatientID
docker run  --rm -ti -v $PWD/dicom:/home/dicom                                 \
                   local/pypx                                                  \
                   --px-find                                                   \
                   --then retrieve                                             \
                   --aet CHRISLOCAL                                            \
                   --aec ORTHANC                                               \
                   --serverIP  192.168.1.189                                   \
                   --serverPort 4242                                           \
                   --PatientID 4780041                                         \
                   --db /home/dicom/log                                        \
                   --verbosity 1                                               \
                   --json                                                      |\
docker run  --rm -i -v $PWD/dicom:/home/dicom                                  \
                   local/pypx                                                  \
                   --px-do                                                     \
                   --then status                                               \
                   --withFeedBack                                              \
                   --verbosity 1
                   
                   
             
