PURPOSE="

    This script describes by way of demonstration various explicit examples of
    how to use the pypx family of tools to connect a PACS database to a ChRIS 
    instance. By 'connect' is meant the set of actions to determine images of
    interest in a PACS and to ultimately send those same images to a ChRIS 
    instance for subsequent image analysis.

    The set of operations, broadly, are:

        * pack a bunch of DICOM files that are on the local filesystem into
          the pypx database;

        * explore the local pypx simple database for information on patients
          series / studies;

        * query a PACS for images of interest and report on results in a
          variety of ways;

        * retrieve a set of images of interest;

        * push the retrieved images to CUBE swift storage;

        * register the pushed-into-swift images with CUBE;
        
    Each set of operations is present with as CLI using 'on-the-metal' tools
    installed with PyPI followed by the equivalent docker CLI. The CLI is
    purposefully tailored to show strong overlap between the 'on-the-metal'
    call and the docker call.

    NOTE:

        * This script should work across all shells of note: bash/zsh/fish
          but has only fully tested on 'fish'.

    Q/A LOG:

        * 07-Dec-2021 -> 08-Dec-2021
          Full test of each command/line against a ChRIS instance and orthanc
          server running within a local network.
"

# Which pypx do you want to use? :)
# export PYPX=fnndsc/pypx
export PYPX=local/pypx

#
# Manually run a storescp:
# Obviously change paths accordingly!
# This is only necessary if you are running pypx without/outside of a
# pfdcm service.
#
# MOST LIKELY YOU WILL NOT NEED TO DO THIS
#
storescp    -od /tmp/data                                                   \
            -pm -sp                                                         \
            -xcr "/home/rudolphpienaar/src/pypx/bin/px-repack --xcrdir #p --xcrfile #f --verbosity 0 --logdir /home/dicom/log --datadir /home/dicom/data" \
            -xcs "/home/rudolphpienaar/src/pypx/bin/px-smdb --xcrdir #p --action endOfStudy" \ 
            11113

# Edit any/all of the following as appropriate to your local env.

#
# swift storage environment
#
export SWIFTKEY=pannotia
export SWIFTHOST=192.168.1.200
export SWIFTPORT=8080
export SWIFTLOGIN=chris:chris1234
export SWIFTSERVICEPACS=orthanc

#
# CUBE login details
#
export CUBEKEY=pannotia
export CUBEURL=http://localhost:84444/api/v1/
export CUBEusername=chris
export CUBEuserpasswd=chris1234

#
# PACS details
#
# For ex a FUJI PACS
export AEC=CHRIS
export AET=CHRISV3
export PACSIP=134.174.12.21
export PACSPORT=104
export DB=/neuro/users/chris/PACS/log
#
# For ex an orthanc service
#
export AEC=ORTHANC
export AET=CHRISLOCAL
export PACSIP=192.168.1.200
export PACSPORT=4242

#
# Local file paths -- if you don't have a /home/dicom
# directory, I'd strongly suggest creating one...
#
export DB=/home/dicom/log
export DATADIR=/home/dicom/data
export BASEMOUNT=/home/dicom
export LOCALDICOMDIR=/home/rudolphpienaar/data/4665436-305/all-full

#
# NB!
# Make sure that the $DB directory is accessible as described from the
# host running this script!
#

# Patient / Study / Series detail
# Obviously re-assign these for a given target!
export MRN=4443508
export STUDYUID=1.2.840.113845.11.1000000001785349915.20130312110508.6351586
export SERIESUID=1.3.12.2.1107.5.2.19.45152.2013031212563759711672676.0.0.0
export ACCESSIONNUMBER=22681485

###############################################################################
#_____________________________________________________________________________#
# R E P A C K                                                                 #
#_____________________________________________________________________________#
# Pack a single flat dir of many DICOM files that exist on the local file     #
# system into the pypx database -- this will also organize the files into     #
# nice directory trees / etc in the database directory.                       #
#                                                                             #
# Note that it is also possible to "pack" files by transmitting them to the   #
# DICOM listener service, which will receive the files and then effectively   #
# do this exact px-repack operation. By calling px-repack directly we can     #
# streamline this process a bit. Also the DICOM listener handling process is  #
# rather computationally intensive.                                           #                                                                   #
###############################################################################

# Pack a whole slew of files that are in a directory
px-repack                                                                      \
                --logdir $DB                                                   \
                --datadir $DATADIR                                             \
                --xcrdir $LOCALDICOMDIR                                        \
                --parseAllFilesWithSubStr dcm

docker run --rm -ti -v $BASEMOUNT:$BASEMOUNT -v $LOCALDICOMDIR:$LOCALDICOMDIR  \
                $PYPX                                                          \
--px-repack                                                                    \
                --logdir $DB                                                   \
                --datadir $DATADIR                                             \
                --xcrdir $LOCALDICOMDIR                                        \
                --parseAllFilesWithSubStr dcm

###############################################################################
#_____________________________________________________________________________#
# S M D B                                                                     #
#_____________________________________________________________________________#
# Some smdb experiences.                                                      # 
# The smdb is a "simple data base" with all table data represented as JSON    #
# files in the FS. The FS itself provides some hierarchical database          #
# organization
###############################################################################

#
# NOTE!
# o All CLI calls are shown as "on-the-metal" as well as docker equivalents.
#   The docker equivalents are constructed to closely map/mirror the 
#   corresponding on-the-metal call.
# o For the most part, the docker call differs in:
#       [] The "prefix" docker command
#       [] All JSON passed to a command needs special quoting and importantly
#          NO spaces (or at least escaped spaces)
#

# Set the swift login info in a key-ref'd service
px-smdb                                                                        \
                --logdir $DB                                                   \
                --action swift                                                 \
                --actionArgs '
{
        "'$SWIFTKEY'": {
                        "ip": "'$SWIFTHOST'", 
                        "port":"'$SWIFTPORT'", 
                        "login":"'$SWIFTLOGIN'"
        }
}'

# docker equivalent -- note the JSON string needs special quoting and needs to
# be a single-line string WITH NO SPACES!
docker run --rm -ti -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-smdb                                                                      \
                --logdir $DB                                                   \
                --action swift                                                 \
                --actionArgs                                                   \
'{\"'$SWIFTKEY'\":{\"ip\":\"'$SWIFTHOST'\",\"port\":\"'$SWIFTPORT'\",\"login\":\"'$SWIFTLOGIN'\"}}'

# Get the swift login details for all keys
# This examines the service file, swift.json, located in
# $DB/services/swift.json
px-smdb                                                                        \
                --logdir $DB                                                   \
                --action swift

docker run --rm -ti -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-smdb                                                                      \
                --logdir $DB                                                   \
                --action swift

# Query smdb for all image dirs on a patient
px-smdb                                                                        \
                --action imageDirsPatientID                                    \
                --actionArgs $MRN                                              \
                --logdir $DB

docker run --rm -ti -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-smdb                                                                      \
                --action imageDirsPatientID                                    \
                --actionArgs $MRN                                              \
                --logdir $DB

# Query smdb for dir on a SeriesInstanceUID
px-smdb                                                                        \
                --action imageDirsSeriesInstanceUID                            \
                --actionArgs $SERIESUID                                        \
                --logdir $DB

docker run --rm -ti -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-smdb                                                                      \
                --action imageDirsSeriesInstanceUID                            \
                --actionArgs $SERIESUID                                        \
                --logdir $DB


# Explicitly update all maps/catalogues for a Patient
# This is typically only needed if for some (rare) case not all the
# constituent DB json files have been created properly.
px-smdb                                                                        \
                --action mapsUpdateForPatient                                  \
                --actionArgs $MRN                                              \
                --logdir $DB 

docker run --rm -ti -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-smdb                                                                      \
                --action mapsUpdateForPatient                                  \
                --actionArgs $MRN                                              \
                --logdir $DB 

# Check the swift storage --  this will only return a valid payload if files
# have been successfully pushed to swift!
pfstorage                                                                   \
                --swiftIP $SWIFTHOST                                        \
                --swiftPort $SWIFTPORT                                      \
                --swiftLogin $SWIFTLOGIN                                    \
                --verbosity 1                                               \
                --debugToDir /tmp                                           \
                --type swift                                                \
                --do '
           {
               "action":   "ls",
               "args": {
                   "path":        "SERVICES/PACS/'$SWIFTSERVICEPACS'"
                   }
           }
           ' --json

# docker equivalent -- note the JSON string needs special quoting and needs to
# be a single-line string WITH NO SPACES!
docker run --rm -ti -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
 --pfstorage                                                                   \
                --swiftIP $SWIFTHOST                                           \
                --swiftPort $SWIFTPORT                                         \
                --swiftLogin $SWIFTLOGIN                                       \
                --verbosity 1                                                  \
                --debugToDir /tmp                                              \
                --do                                                           \
    '{\"action\":\"ls\",\"args\":{\"path\":\"SERVICES/PACS/'$SWIFTSERVICEPACS'\"}}' --json

###############################################################################
#_____________________________________________________________________________#
# S E A R C H                                                                 #
#_____________________________________________________________________________#
#                                                                             #
# Some search experiences.                                                    # 
# Note that if $SEARCHTAG and $SEARCHVAL are NOT set, then orthanc            #
# will return data on all PATIENTS/STUDIES/SERIES                             #
###############################################################################
# Search targets
# Edit the following as you see fit!
export SEARCHTAG="--PatientID"
export SEARCHTAG="--AccessionNumber"
export SEARCHVAL=$ACCESSIONNUMBER

export SEARCHTAG="--SeriesInstanceUID"
export SEARCHVAL=$SERIESUID

# Simple "search":
px-find                                                                        \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                $SEARCHTAG $SEARCHVAL                                          \
                --db $DB                                                       \
                --verbosity 1                                                  \
                --json                                                         \
                --then report                                                  \
                --withFeedBack

docker run --rm -ti -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-find                                                                      \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                $SEARCHTAG $SEARCHVAL                                          \
                --db $DB                                                       \
                --verbosity 1                                                  \
                --json                                                         \
                --then report                                                  \
                --withFeedBack


# Simple "search" with more detailed reporting
px-find                                                                        \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                $SEARCHTAG $SEARCHVAL                                          \
                --db $DB                                                       \
                --json                                                        |\
px-report                                                                      \
                --colorize dark                                                \
                --printReport csv                                              \
                --csvPrettify                                                  \
                --csvPrintHeaders                                              \
                --reportHeaderStudyTags PatientName,PatientID,StudyDate        \
                --reportBodySeriesTags SeriesDescription,SeriesInstanceUID

docker run --rm -ti -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-find                                                                      \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                $SEARCHTAG $SEARCHVAL                                          \
                --db $DB                                                       \
                --json                                                        |\
docker run --rm -i  -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-report                                                                    \
                --colorize dark                                                \
                --printReport csv                                              \
                --csvPrettify                                                  \
                --csvPrintHeaders                                              \
                --reportHeaderStudyTags PatientName,PatientID,StudyDate        \
                --reportBodySeriesTags SeriesDescription,SeriesInstanceUID


# Let's reduce the header to only the PatientID, StudyDate and StudyInstanceUID
px-find                                                                        \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                $SEARCHTAG $SEARCHVAL                                          \
                --db $DB                                                       \
                --json                                                        |\
px-report                                                                      \
                --colorize dark                                                \
                --printReport csv                                              \
                --csvPrettify                                                  \
                --csvPrintHeaders                                              \
                --reportHeaderStudyTags PatientID,StudyDate,StudyInstanceUID   \
                --reportBodySeriesTags SeriesDescription,SeriesInstanceUID

docker run --rm -ti -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-find                                                                      \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                $SEARCHTAG $SEARCHVAL                                          \
                --db $DB                                                       \
                --json                                                        |\
docker run --rm -i  -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-report                                                                    \
                --colorize dark                                                \
                --printReport csv                                              \
                --csvPrettify                                                  \
                --csvPrintHeaders                                              \
                --reportHeaderStudyTags PatientID,StudyDate,StudyInstanceUID   \
                --reportBodySeriesTags SeriesDescription,SeriesInstanceUID

###############################################################################
#_____________________________________________________________________________#
# R E T R I E V E                                                             #
#_____________________________________________________________________________#
# Now for some search driven retrieves.                                       # 
# The semantics are built around a <search>then<retrieve> construct           #
###############################################################################
# Retrieve
# The --intraSeriesRetrieveDelay is a throttle that might be necessary if you
# are running this infrastructure on a low spec machine.
#
px-find                                                                        \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                $SEARCHTAG $SEARCHVAL                                          \
                --db $DB                                                       \
                --json                                                         \
                --then retrieve                                                \
                --withFeedBack                                                 \
                --intraSeriesRetrieveDelay dynamic:10                          \

docker run --rm -i  -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-find                                                                      \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                $SEARCHTAG $SEARCHVAL                                          \
                --db $DB                                                       \
                --json                                                         \
                --then retrieve                                                \
                --withFeedBack                                                 \
                --intraSeriesRetrieveDelay dynamic:10                          \

###############################################################################
#_____________________________________________________________________________#
# S T A T U S                                                                 #
#_____________________________________________________________________________#
# Check status in internal smdb       .                                       # 
# The semantics are built around a <search>then<retrieve> construct           #
###############################################################################
px-find                                                                        \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                $SEARCHTAG $SEARCHVAL                                          \
                --db $DB                                                       \
                --verbosity 1                                                  \
                --json                                                         \
                --then status                                                  \
                --withFeedBack

docker run --rm -i  -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-find                                                                      \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                $SEARCHTAG $SEARCHVAL                                          \
                --db $DB                                                       \
                --verbosity 1                                                  \
                --json                                                         \
                --then status                                                  \
                --withFeedBack


# Retrieve only a single series in a study
export STUDYINSTANCEUID=1.2.840.113845.11.1000000001785349915.20130312110508.6351586
export SERIESINSTANCEUID=1.3.12.2.1107.5.2.19.45152.30000013022413214670400289776

# Check that this is the study/series of interest
px-find                                                                        \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                --StudyInstanceUID $STUDYINSTANCEUID                           \
                --SeriesInstanceUID $SERIESINSTANCEUID                         \
                --db $DB                                                       \
                --json                                                         \
                --then report                                                  \
                --withFeedBack

docker run --rm -i  -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-find                                                                      \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                --StudyInstanceUID $STUDYINSTANCEUID                           \
                --SeriesInstanceUID $SERIESINSTANCEUID                         \
                --db $DB                                                       \
                --json                                                         \
                --then report                                                  \
                --withFeedBack

# Now pull it... (and show the status after pulling)
px-find                                                                        \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                --StudyInstanceUID $STUDYINSTANCEUID                           \
                --SeriesInstanceUID $SERIESINSTANCEUID                         \
                --db $DB                                                       \
                --json                                                         \
                --then retrieve,status                                         \
                --withFeedBack

docker run --rm -it -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-find                                                                      \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                --StudyInstanceUID $STUDYINSTANCEUID                           \
                --SeriesInstanceUID $SERIESINSTANCEUID                         \
                --db $DB                                                       \
                --json                                                         \
                --then retrieve,status                                         \
                --withFeedBack

# Check the status using the report module:
px-find                                                                        \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                $SEARCHTAG $SEARCHVAL                                          \
                --db $DB                                                       \
                --verbosity 1                                                  \
                --json                                                         \
                --then status                                                 |\
px-report                                                                      \
                --seriesSpecial seriesStatus                                   \
                --printReport tabular                                          \
                --colorize dark                                                \
                --reportBodySeriesTags seriesStatus

docker run --rm -i  -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-find                                                                      \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                $SEARCHTAG $SEARCHVAL                                          \
                --db $DB                                                       \
                --verbosity 1                                                  \
                --json                                                         \
                --then status                                                 |\
docker run --rm -i  -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-report                                                                    \
                --seriesSpecial seriesStatus                                   \
                --printReport tabular                                          \
                --colorize dark                                                \
                --reportBodySeriesTags seriesStatus


# Check the status using the report module and csv output:
px-find                                                                        \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                $SEARCHTAG $SEARCHVAL                                          \
                --db $DB                                                       \
                --verbosity 1                                                  \
                --json                                                         \
                --then status                                                 |\
px-report                                                                      \
                --seriesSpecial seriesStatus                                   \
                --printReport csv                                              \
                --csvPrettify                                                  \
                --csvPrintHeaders                                              \
                --reportHeaderStudyTags PatientName,StudyDate		           \
                --reportBodySeriesTags seriesStatus

docker run --rm -i  -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-find                                                                      \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                $SEARCHTAG $SEARCHVAL                                          \
                --db $DB                                                       \
                --verbosity 1                                                  \
                --json                                                         \
                --then status                                                 |\
docker run --rm -i  -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-report                                                                    \
                --seriesSpecial seriesStatus                                   \
                --printReport csv                                              \
                --csvPrettify                                                  \
                --csvPrintHeaders                                              \
                --reportHeaderStudyTags PatientName,StudyDate		           \
                --reportBodySeriesTags seriesStatus


###############################################################################
#_____________________________________________________________________________#
# P U S H                                                                     #
#_____________________________________________________________________________#
# Once data is pulled locally, either from a retrieve or from some other      #
# mechanism, we can now push images to CUBE swift storage.                    #
#                                                                             #
#                                                                             # 
# As earlier with the retrieve, we can do a <search>then<push> construct.     #
# The <source> to PUSH is a directory on the locally accessible filesystem    #
# which can either be specified directly with the '--xcrdir' parameter, or    #
# resolved by a call to find event off a connected PACS (this is ultimately   #
# used simply to determine the location of files within the smdb tree).       #
###############################################################################


# Now, choose a single series by simply passing the SeriesInstanceUID and
# StudyInstanceUID in the `px-find` appropriately

# Push some data to swift storage:
export SWIFTSERVICEPACS=covidnet
export LOCALDICOMDIR=/home/rudolphpienaar/data/WithProtocolName/all
px-push                                                                        \
                --swiftIP $SWIFTHOST                                           \
                --swiftPort $SWIFTPORT                                         \
                --swiftLogin $SWIFTLOGIN                                       \
                --swiftServicesPACS $SWIFTSERVICEPACS                          \
                --db $DB                                                       \
                --swiftPackEachDICOM                                           \
                --xcrdir $LOCALDICOMDIR                                        \
                --parseAllFilesWithSubStr dcm                                  \
                --verbosity 1                                                  \
                --json > push.json

docker run --rm -i -v $LOCALDICOMDIR:$LOCALDICOMDIR -v $BASEMOUNT:$BASEMOUNT $PYPX \
--px-push                                                                      \
                --swiftIP $SWIFTHOST                                           \
                --swiftPort $SWIFTPORT                                         \
                --swiftLogin $SWIFTLOGIN                                       \
                --swiftServicesPACS $SWIFTSERVICEPACS                          \
                --db $DB                                                       \
                --swiftPackEachDICOM                                           \
                --xcrdir $LOCALDICOMDIR                                        \
                --parseAllFilesWithSubStr dcm                                  \
                --verbosity 1                                                  \
                --json


# Or, using the $SWIFTKEY...
px-push                                                                        \
                --swift $SWIFTKEY                                              \
                --swiftServicesPACS $SWIFTSERVICEPACS                          \
                --db $DB                                                       \
                --swiftPackEachDICOM                                           \
                --xcrdir $LOCALDICOMDIR                                        \
                --parseAllFilesWithSubStr dcm                                  \
                --verbosity 1                                                  \
                --json

docker run --rm -i -v $LOCALDICOMDIR:$LOCALDICOMDIR -v $BASEMOUNT:$BASEMOUNT $PYPX \
--px-push                                                                      \
                --swift $SWIFTKEY                                              \
                --swiftServicesPACS $SWIFTSERVICEPACS                          \
                --db $DB                                                       \
                --swiftPackEachDICOM                                           \
                --xcrdir $LOCALDICOMDIR                                        \
                --parseAllFilesWithSubStr dcm                                  \
                --verbosity 1                                                  \
                --json
                
# Push from a find event:
px-find                                                                        \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                $SEARCHTAG $SEARCHVAL                                          \
                --db $DB                                                       \
                --verbosity 1                                                  \
                --json                                                         \
                --then push                                                    \
                --thenArgs '
                {
                        "db":                   "'$DB'", 
                        "swift":                "'$SWIFTKEY'", 
                        "swiftServicesPACS":    "'$SWIFTSERVICEPACS'", 
                        "swiftPackEachDICOM":   true
                }'                                                             \
                --withFeedBack

docker run --rm -i  -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-find                                                                      \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                $SEARCHTAG $SEARCHVAL                                          \
                --db $DB                                                       \
                --verbosity 1                                                  \
                --json                                                         \
                --then push                                                    \
                --thenArgs                                                     \
'{\"db\":\"'$DB'\",\"swift\":\"'$SWIFTKEY'\",\"swiftServicesPACS\":\"'$SWIFTSERVICEPACS'\",\"swiftPackEachDICOM\":true}' \
                --withFeedBack

###############################################################################
#_____________________________________________________________________________#
# R E G I S T E R                                                             #
#_____________________________________________________________________________#
# Pushing data to swift storage does not make ChRIS aware of the data yet.    #
# In order for the data to be visible to ChRIS, it needs to be registered to  #
# ChRIS from swift.                                                           #
#                                                                             #
###############################################################################

# Set lookup in smdb
px-smdb                                                                      \
                --logdir /home/dicom/log                                       \
                --action CUBE                                                  \
                --actionArgs                                                   \
                '
{
        "'$CUBEKEY'": {
                        "url": "'$CUBEURL'", 
                        "username":"'$CUBEusername'", 
                        "password":"'$CUBEuserpasswd'"
        }
}'

docker run --rm -ti -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-smdb                                                                      \
                --logdir /home/dicom/log                                       \
                --action CUBE                                                  \
                --actionArgs                                                   \
'{\"'$CUBEKEY'\":{\"url\":\"'$CUBEURL'\",\"username\":\"'$CUBEusername'\",\"password\":\"'$CUBEuserpasswd'\"}}'


# Get the CUBE login details for all keys
# This examines the service file, swift.json, located in
# $DB/services/swift.json
# Get the swift login details for all keys
# This examines the service file, swift.json, located in
# $DB/services/swift.json
px-smdb                                                                        \
                --logdir $DB                                                   \
                --action CUBE

docker run --rm -ti -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
--px-smdb                                                                      \
                --logdir $DB                                                   \
                --action CUBE

# Register from a set of local directories (assuming this directory has already
# been pushed)
px-register                                                                    \
                --CUBE $CUBEKEY                                                \
                --swiftServicesPACS $SWIFTSERVICEPACS                          \
                --db $DB                                                       \
                --xcrdir $LOCALDICOMDIR                                        \
                --parseAllFilesWithSubStr dcm                                  \
                --verbosity 1                                                  \
                --json 

docker run --rm -i -v $LOCALDICOMDIR:$LOCALDICOMDIR -v $BASEMOUNT:$BASEMOUNT $PYPX \
--px-register                                                                    \
                --CUBE $CUBEKEY                                                \
                --swiftServicesPACS $SWIFTSERVICEPACS                          \
                --db $DB                                                       \
                --xcrdir $LOCALDICOMDIR                                        \
                --parseAllFilesWithSubStr dcm                                  \
                --verbosity 1                                                  \
                --json 

# Register from a find event
px-find                                                                        \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                $SEARCHTAG $SEARCHVAL                                          \
                --db $DB                                                       \
                --verbosity 1                                                  \
                --json                                                         \
                --then register                                                \
                --thenArgs '
                {
                        "db":                           "'$DB'", 
                        "CUBE":                         "'$CUBEKEY'", 
                        "swiftServicesPACS":            "'$SWIFTSERVICEPACS'", 
                        "parseAllFilesWithSubStr":      "dcm"
                }'                                                             \
                --withFeedBack

docker run --rm -i -v $LOCALDICOMDIR:$LOCALDICOMDIR -v $BASEMOUNT:$BASEMOUNT $PYPX \
--px-find                                                                      \
                --aec $AEC                                                     \
                --aet $AET                                                     \
                --serverIP $PACSIP                                             \
                --serverPort $PACSPORT                                         \
                $SEARCHTAG $SEARCHVAL                                          \
                --db $DB                                                       \
                --verbosity 1                                                  \
                --json                                                         \
                --then register                                                \
                --thenArgs '
{\"db\":\"'$DB'\",\"CUBE\":\"'$CUBEKEY'\",\"swiftServicesPACS\":\"'$SWIFTSERVICEPACS'\",\"parseAllFilesWithSubStr\":\"dcm\"}' \
                --withFeedBack

# ends.
#
#_-30-_

                   
             
