# NOTE:
# this script assumes fish conventions
#

# Manually run a storescp:
storescp        -od /tmp/data                                                  \
                -pm -sp                                                        \
                -xcr "/home/rudolphpienaar/src/pypx/bin/px-repack --xcrdir #p --xcrfile #f --verbosity 0 --logdir /home/dicom/log --datadir /home/dicom/data"                                                \
                -xcs "/home/rudolphpienaar/src/pypx/bin/px-smdb --xcrdir #p --action endOfStudy" \ 
                11113

# Pack a single file
px-repack       --logdir /home/dicom/log                                       \
                --datadir /home/dicom/data                                     \
                --xcrdir ~/data/4665436-305/all                                \
                --parseAllFilesWithSubStr dcm

set SWIFTHOST 192.168.1.200
set SWIFTPORT 8080
set SWIFTLOGIN chris:chris1234
set SWIFTKEY swiftStorage

# Set the swift login info in a key-ref'd service
px-smdb         --logdir /home/dicom/log                                       \
                --action swift                                                 \
                --actionArgs '
{
        "'$SWIFTKEY'": {
                        "ip": "'$SWIFTHOST'", 
                        "port":"'$SWIFTPORT'", 
                        "login":"'$SWIFTLOGIN'"
        }
}'

px-smdb         --logdir /home/dicom/log                                       \
                --action swift                                                 \
                --actionArgs '
{
        "swiftStorage": {
                        "ip": "localhost", 
                        "port":"8080", 
                        "login":"chris:chris1234"
        }
}'

# Get the swift login details for all keys
px-smdb         --logdir /home/dicom/log                                       \
                --action swift

# Query smdb for all image dirs on a patient
px-smdb         --action imageDirsForPatientID                                 \
                --actionArgs 5644810                                           \
                --logdir /home/dicom/log

# Query smdb for dir on a SeriesInstanceUID
px-smdb         --action imageDirsSeriesInstanceUID                            \
                --actionArgs 1.3.12.2.1107.5.2.19.45479.2021061717351923347817670.0.0.0 \
                --logdir /home/dicom/log

# Explicitly update all maps/catalogues for a Patient
px-smdb         --action mapsUpdateForPatient                                  \
                --actionArgs 5644810                                           \
                --logdir /home/dicom/log 


# on the metal
pfstorage                                                                      \
                --swiftIP $SWIFTHOST                                           \
                --swiftPort $SWIFTPORT                                         \
                --swiftLogin $SWIFTLOGIN                                       \
                --verbosity 1                                                  \
                --debugToDir /tmp                                              \
                --type swift                                                   \
                --do '
           {
               "action":   "ls",
               "args": {
                   "path":        "SERVICES/PACS/covidnet"
                   }
           }
           ' --json

# docker equivalent
docker run --rm -ti local/pypx  --pfstorage                                    \
                --swiftIP $SWIFTHOST                                           \
                --swiftPort $SWIFTPORT                                         \
                --swiftLogin $SWIFTLOGIN                                       \
                --verbosity 1                                                  \
                --debugToDir /tmp                                              \
                --do '{\"action\":\"ls\",\"args\":{\"path\":\"SERVICES/PACS/covidnet\"}}' --json

# Retrieve:
px-find         --aec ORTHANC                                                  \
                --aet CHRISLOCAL                                               \
                --serverIP 192.168.1.189                                       \
                --serverPort 4242                                              \
                --PatientID 5644810                                            \
                --db /home/dicom/log                                           \
                --verbosity 1                                                  \
                --json                                                         \
                --then retrieve                                                \
                --intraSeriesRetrieveDelay dynamic:10                          \
                --withFeedBack

# Check the status
px-find         --aec ORTHANC                                                  \
                --aet CHRISLOCAL                                               \
                --serverIP 192.168.1.189                                       \
                --serverPort 4242                                              \
                --PatientID 5644810                                            \
                --db /home/dicom/log                                           \
                --verbosity 1                                                  \
                --json                                                         \
                --then status                                                  \
                --withFeedBack


# Push some data to swift storage:
px-push                                                                        \
                   --swiftIP $SWIFTHOST                                        \
                   --swiftPort $SWIFTPORT                                      \
                   --swiftLogin $SWIFTLOGIN                                    \
                   --swiftServicesPACS covidnet                                \
                   --db /home/dicom/log                                        \
                   --swiftPackEachDICOM                                        \
                   --xcrdir /home/rudolphpienaar/data/WithProtocolName/all     \
                   --parseAllFilesWithSubStr dcm                               \
                   --verbosity 1                                               \
                   --json > push.json

px-push                                                                        \
                   --swift $SWIFTKEY                                           \
                   --swiftServicesPACS test                                    \
                   --db /home/dicom/log                                        \
                   --swiftPackEachDICOM                                        \
                   --xcrdir /home/rudolphpienaar/data/WithProtocolName/all     \
                   --parseAllFilesWithSubStr dcm                               \
                   --verbosity 1                                               \
                   --json > push.json


# Push from a find event:
px-find         --aec ORTHANC                                                  \
                --aet CHRISLOCAL                                               \
                --serverIP 192.168.1.189                                       \
                --serverPort 4242                                              \
                --PatientID 5644810                                            \
                --db /home/dicom/log                                           \
                --verbosity 1                                                  \
                --json                                                         \
                --then push                                                    \
                --thenArgs '
                {
                        "db":                   "/home/dicom/log", 
                        "swift":                "swiftStorage", 
                        "swiftServicesPACS":    "BCH", 
                        "swiftPackEachDICOM":   true
                }'                                                             \
                --withFeedBack


set CUBEKEY megalodon
set CUBEURL http://localhost:84444/api/v1/
set CUBEusername chris
set CUBEuserpasswd chris1234

# Set lookup in smbdb
px-smdb         --logdir /home/dicom/log                                       \
                --action CUBE                                                 \
                --actionArgs '
{
        "'$CUBEKEY'": {
                        "url": "'$CUBEURL'", 
                        "username":"'$CUBEusername'", 
                        "password":"'$CUBEuserpasswd'"
        }
}'

# Register from a find event
px-find         --aec ORTHANC                                                  \
                --aet CHRISLOCAL                                               \
                --serverIP 192.168.1.189                                       \
                --serverPort 4242                                              \
                --PatientID 5644810                                            \
                --db /home/dicom/log                                           \
                --verbosity 1                                                  \
                --json                                                         \
                --then register                                                \
                --thenArgs '
                {
                        "db":                           "/home/dicom/log", 
                        "CUBE":                         "'$CUBEKEY'", 
                        "swiftServicesPACS":            "BCH", 
                        "parseAllFilesWithSubStr":      "dcm"
                }'                                                             \
                --withFeedBack

# Register 
px-register                                                                    \
                --CUBE $CUBEKEY                                                \
                --swiftServicesPACS test3                                      \
                --db /home/dicom/log                                           \
                --xcrdir /home/rudolphpienaar/data/WithProtocolName/all        \
                --parseAllFilesWithSubStr dcm                                  \
                --verbosity 1                                                  \
                --json 


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

px-register                                                                    \
                       --upstreamFile push.json                                \
                       --CUBE $CUBEKEY                                         \
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
                   
                   
             
