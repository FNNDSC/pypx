set SWIFTHOST 192.168.1.200
set SWIFTPORT 8080
set SWIFTLOGIN chris:chris1234

# Push some data to swift storage:
px-push                                                                        \
                   --swiftIP $SWIFTHOST                                        \
                   --swiftPort $SWIFTPORT                                      \
                   --swiftLogin $SWIFTLOGIN                                    \
                   --swiftServicesPACS covidnet                                \
                   --swiftPackEachDICOM                                        \
                   --xcrdir /home/rudolphpienaar/data/WithProtocolName/all     \
                   --parseAllFilesWithSubStr dcm                               \
                   --verbosity 1                                               \
                   --json > push.json

set CUBEURL http://localhost:84444/api/v1/
set CUBEusername chris
set CUBEuserpasswd chris1234
px-register                                                                    \
                       --upstreamFile push.json                                \
                       --CUBEURL $CUBEURL                                      \
                       --CUBEusername $CUBEusername                            \
                       --CUBEuserpasswd $CUBEuserpasswd                        \
                       --swiftServicesPACS covidnet                            \
                       --verbosity 1                                           \
                       --json                                                  \
                       --logdir /home/dicom/log                                \
                       --debug


# Perform a find on a given PatientID
# using docker and assuming container image is ``local/pypx``
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

# Perform a find on a given PatientID
# on the metal and generate a report...
px-find                                                                        \
                   --aet CHRISV3                                               \
                   --serverIP  134.174.12.21                                   \
                   --serverPort 104                                            \
                   --PatientID 4780041                                         \
                   --db /neuro/users/chris/PACS/log                            \
                   --verbosity 1                                               \
                   --json                                                     |\
px-report                                                                      \
                   --colorize dark                                             \
                   --printReport csv --csvPrettify --csvPrintHeaders           \
                   --reportHeaderStudyTags PatientName,PatientID,AccessionNumber,StudyDate

                   
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
                   --withFeedBack                                              \
                   --intraSeriesRetrieveDelay dynamic:6                        \
                   --aet CHRISLOCAL                                            \
                   --aec ORTHANC                                               \
                   --serverIP  192.168.1.189                                   \
                   --serverPort 4242                                           \
                   --PatientID 4780041                                         \
                   --db /home/dicom/log                                        \
                   --verbosity 1                                               \
                   --json

# Perform a find then retrieve on a given PatientID
px-find                                                                        \
                   --aet CHRISV3                                               \
                   --serverIP  134.174.12.21                                   \
                   --serverPort 104                                            \
                   --PatientID 4780041                                         \
                   --db /neuro/users/chris/PACS/log                            \
                   --verbosity 1                                               \
                   --json                                                     |\
px-do                                                                          \
                   --db /neuro/users/chris/PACS/log                            \
                   --then retrieve,status,status                               \
                   --intraSeriesRetrieveDelay dynamic:6                        \
                   --withFeedBack                                              \
                   --verbosity 1 

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
                   
                   
             
