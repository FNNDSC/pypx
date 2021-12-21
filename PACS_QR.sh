#!/bin/bash

source common.bash
let G_VERBOSE=0
let G_DEBUG=0

#
# Container image
#
export PYPX=fnndsc/pypx

#
# swift storage environment defaults
#
export SWIFTKEY=local
export SWIFTHOST=192.168.1.200
export SWIFTPORT=8080
export SWIFTLOGIN=chris:chris1234
export SWIFTSERVICEPACS=orthanc
declare -i Gb_swiftset=0

#
# CUBE login detail defaults
#
export CUBEKEY=local
export CUBEURL=http://localhost:8000/api/v1/
export CUBEusername=chris
export CUBEuserpasswd=chris1234
declare -i Gb_CUBEset=0

#
# PACS detail defaults
#
# For ex a FUJI PACS
export AEC=CHRIS
export AET=CHRISV3
export PACSIP=134.174.12.21
export PACSPORT=104
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
# NB!!
# * Take care if the BASEMOUNT is across an NFS boundary!
#   This might result in docker root access squash issues.
#
# A workable solution is to mount the actual PACS location
# to this host's /home/dicom
export BASEMOUNT=/neuro/users/chris/PACS
export BASEMOUNT=/home/dicom
export DB=${BASEMOUNT}/log
export DATADIR=${BASEMOUNT}/data

# The HOST/USER here are FNNDSC specific and can be ignored using
# a '-F' to the script
G_HOST="titan"
G_USER="chris-local"
Gb_noCheck=0

# Actions etc
G_ACTION=""
G_REPORTARGS=""
G_REPORTARGSCSV="--printReport csv                                              \
                --csvPrettify                                                  \
                --csvPrintHeaders                                              \
                --reportHeaderStudyTags PatientName,PatientID,StudyDate        \
                --reportBodySeriesTags SeriesDescription,SeriesInstanceUID"

G_DICOMDIR=/home/dicom
G_INSTITUTION="BCH-chris"
G_SYNOPSIS="

  NAME

        PACS_QR.sh

  SYNOPSIS

        PACS_QR.sh                                                      \\
                        [--container    <containerName>]                \\
                        [--baseMount>   <baseDBmountDir>]               \\
                        [-F]                                            \\
                        [--CUBEKEY      <cubeKey>]                      \\
                        [--CUBEURL      <cubeURL>]                      \\
                        [--CUBEuser     <cubeUserName>]                 \\
                        [--CUBEpassword <cubeUserPassword>]             \\
                        [--SWIFTKEY     <swiftKey>]                     \\
                        [--SWIFTHOST    <swiftHost>]                    \\
                        [--SWIFTPORT    <swiftPort>]                    \\
                        [--SWIFTLOGIN   <swiftLogin>]                   \\
                        [--SWIFTPACS    <SERVICESPACSName>]             \\
                        [--PACSIP       <PACSserverIP>]                 \\
                        [--PACSport     <PACSserverPort>]               \\
                        [--AET          <AETitle>]                      \\
                        [--AEC          <CalledAETitle>]                \\
                        [--env          <envLookup>]                    \\
                        [--do           <postFindAction>]               \\
                        [--report       <reportOverrideForFind>]        \\
                        [--debug]                                       \\
                        [-v]                                            \\
                        --
                        <PACSstringLookupExpression>

  DESC

        PACS_QR.sh is a thin convenience wrapper around containerized
        components of the pypx image. This script provides a simple way
        to use the core tools to do PACS Query/Retrieve, PUSH-to-swift,
        and REGISTER-to-CUBE.

        Given the very strong and very implicit dependencies of this script
        on an appropriately configured PACS server, as well a valid path
        from the PACS transmission to a specific 'host', the following
        pre-requesites are required:

  PRE-REQUISITES

        Requirements: general
        
        * This script requires some configuration files to exist in special
          directory (<basrDBmountDir>):

                * swift.json
                * cube.json

           that describe the swift and cube login details. These configuration
           files are only needed for PUSHing and REGISTERing pulled DICOM data
           to swift and cube and are not needed for PACS Query or Retrieve.


        Requirements: PACS retrieve 

        * The BCH Linux host 'titan' must have the necessary listening services
          up and running

        Requirements: retrieve / push / register 

        In the BCH network, if you are running this script stand-alone, you
        MUST:

        * BE ABLE TO RUN DOCKER COMMANDS!
        * make sure you are running this on host 'titan'
        * make note that any pulled DICOMs are saved to

        		/neuro/users/chris/PACS

        (**) typical cmd for setting up a tunnel (on host 'pretoria'):

        ssh -g -f -N -X -L 10402:localhost:10402 rudolphpienaar@titan

  ARGS

        [--container    <containerName>]
        The name of the container image to execute. By default this is 
        'fnndsc/pypx' but can be overriden if local image is to be used.

        [--baseMount>   <baseDBmountDir>]
        The base directory of the pypx tree. This tree contains the internal
        database as well as any received files.

        [-F]
        If specified, do not perform username or hostname checks on the
        scipt environment. By defaul the script will only run as user
        'chris-local' on FNNDSC host 'titan' since this user/host has been
        correctly configured. In other envirnments, use a '-F' to ignore
        this check.

        [--CUBEKEY      <cubeKey>]
        A key lookup in the baseMount services cube.json file that describes
        detail regarding the CUBE service that should register any DICOM files.

        [--CUBEURL      <cubeURL>]                      
        [--CUBEuser     <cubeUserName>]                 
        [--CUBEpassword <cubeUserPassword>]             
        Explicitly set, for <cubeKey>, values in the cube.json config file.
        Typical values:

            {
                \"pannotia\": {
                    \"url\": \"http://192.168.1.200:8000/api/v1/\",
                    \"username\": \"chris\",
                    \"password\": \"chris1234\"
                }
            }

        [--SWIFTKEY     <swiftKey>]                     
        A key lookup in the baseMount services swift.json file that describes
        detail regarding the swift service that should receive any PUSHed
        DICOM files.

        [--SWIFTHOST    <swiftHost>] 
        [--SWIFTPORT    <swiftPort>] 
        [--SWIFTLOGIN   <swiftLogin>]
        Explicitly set, for <swiftKey>, values in the swift.json config file.
        Typical values:

            {
                \"local\": {
                    \"ip\": \"192.168.1.200\",
                    \"port\": \"8080\",
                    \"login\": \"chris:chris1234\"
                }
            }


        [--SWIFTPACS    <SERVICESPACSName>]
        The name of the housing 'directory' in the swift storage as well as
        CUBE internal database for 'this' PACS. Multiple different 'PACS' 
        services can be differentiated by using this field.

        [--PACSIP       <PACSserverIP>]
        The IP address of the PACS service to Query.

        [--PACSport     <PACSserverPort>]
        The port of the PACS service to Query.

        [--AET          <AETitle>]
        The AETitle of 'this' client/service.

        [--AEC          <CalledAETitle>]                
        The CalledAETitle of 'this' client service.

        [--env          <envLookup>]
        An internal convenience named lookup for AET/AEC/PACS[IP|port].

        [--do           <postFindAction>]
        A word describing a 'then' action _after_ a PACS query has been
        performed. Valid actions are:

            * status
            * retrieve
            * push
            * register

        [--report       <reportOverrideForFind>]
        In the case of Query only, the appearance of the on-screen report
        can be tweaked using the <reportOverrideForFind> string.

        [--debug]
        If specified, mount current source code into the container image
        for in-container debugging.

        [-v]
        If specified, print the underlying '--px-find' CLI.

        <PACSstringLookupExpression>
        A string defining the search term to use against the specified PACS.
        The format is '--<DICOMtag> <value>', for example

            \"--PatientID 1234567\"
            \"--AccessionNumber 87654321\"
            \"--StudyDate 20220101\"

        You can create tighter search results by adding several parameters into
        a single string expression:

            \"--PatientID 1234567 --StudyDate 20220101\"

  EXAMPLES

    [] QUERY

        PACS_QR.sh --env BCH-chris -- \"--PatientID 1234567\"

    NOTE: 1234567 is a fake PatientID. Please do not actually use that!

    Query the PACS on the passed PatientID. Note that the following query terms are
    accepted by px-find (and returned by the PACS in Query mode):

        parameters = {
            'AccessionNumber': '',
            'PatientID': '',                     # PATIENT INFORMATION
            'PatientName': '',
            'PatientBirthDate': '',
            'PatientAge': '',
            'PatientSex': '',
            'StudyDate': '',                     # STUDY INFORMATION
            'StudyDescription': '',
            'StudyInstanceUID': '',
            'Modality': '',
            'ModalitiesInStudy': '',
            'PerformedStationAETitle': '',
            'NumberOfSeriesRelatedInstances': '', # SERIES INFORMATION
            'InstanceNumber': '',
            'SeriesDate': '',
            'SeriesDescription': '',
            'SeriesInstanceUID': '',
            'QueryRetrieveLevel': 'SERIES'
        }

    [] SET the swift parameters (atypical)

        PACS_QR.sh  --SWIFTKEY someswift                                    \\
                    --SWIFTHOST some.ip.address                             \\
                    --SWIFTPORT 8080                                        \\
                    --SWIFTLOGIN user:password                              \\
                    -F --

    [] SET the CUBE parameters (atypical)

        PACS_QR.sh  --CUBEKEY someCUBE                                      \\
                    --CUBEURL some.ip.address:8000/api/v1/                  \\
                    --CUBEuser user                                         \\
                    --CUBEpassword password                                 \\
                    -F --

    [] RETRIEVE

        PACS_QR.sh --env BCH-chris --do retrieve -- \"--PatientID 1234567\"

    [] PUSH (to CUBE swift storage)

        PACS_QR.sh --env BCH-chris --do push --SWIFTPACS BCH -- \"--PatientID 1234567\"

    [] RETRIEVE

        PACS_QR.sh --env BCH-chris --do register --SWIFTPACS BCH -- \"--PatientID 1234567\"

    NOTE: 1234567 is a fake PatientID. Please do not actually use that!

"

A_hostCheck="checking on this host, you are calling this script on '$(hostname)'"
EM_hostCheck="This must be run host '$G_HOST' (and ideally as user '$G_USER')!

                ┌─────────────────────────────────────────┐
                │  ssh chris-local@titan.tch.harvard.edu  │
                └─────────────────────────────────────────┘

        You can force execution on '$(hostname)' by using a '-H $(hostname)' spec;
        however please note that to work properly, the docker daemon must be setup
        and the '$PYPX' container image installed.

"
EC_hostCheck="10"

A_userCheck="checking on user, you are '$(whoami)'"
EM_userCheck="This must be run as user '$G_USER' (and ideally on host '$G_HOST')!

                ┌─────────────────────────────────────────┐
                │  ssh chris-local@titan.tch.harvard.edu  │
                └─────────────────────────────────────────┘

        You can force execution as '$(whoami)' by using a '-U $(whoami)' spec;
        however please note that to work properly, the '$(whoami)' user should
        have passwordless docker access and be able to run docker commands.

"
EC_userCheck="12"

function substrInStr
{
    local SUBSTR="$1"
    local STR="$2"

    if [[ "$STR" == *"$SUBSTR"* ]] ; then
        echo 1
    else 
        echo 0
    fi
}

function host_check
{
    local HOST=$(hostname)

    if (( ${#G_ACTION} )) ; then
        if [[ $HOST != $G_HOST ]] ; then
            fatal hostCheck
        fi
        if (( $(substrInStr retrieve "$G_ACTION") )) ; then
            echo "
 ┌───────────┐
┌┤ PACS PULL ├─────────────────────────────────┐
│└───────────┘                                 │
│       A PACS PULL has been specified.        │
│                                              │
│   Any retrieved results will be saved here:  │
└──────────────────────────────────────────────┘
$DATADIR"
        fi
    fi
}

function user_check
{
    if [[ $(whoami) != "$G_USER" ]] ; then
        fatal userCheck
    fi
}

function institution_set
{
    local INSTITUTION=$1

    case "$INSTITUTION"
    in
        orthanc)
            SWIFTKEY=orthanc
            CUBEKEY=orthanc
            SWIFTPACS=orthanc
            AET=CHRISLOCAL
            PACSIP=127.0.0.1
            PACSPORT=4242
            AEC=ORTHANC
        ;;
        BCH-chris)
            SWIFTKEY=local
            CUBEKEY=local
            SWIFTPACS=PACSDCM
            AET=CHRISV3
            PACSIP=134.174.12.21
            PACSPORT=104
            AEC=CHRIS
        ;;
        BCH-chrisdev)
            SWIFTKEY=local
            CUBEKEY=local
            SWIFTPACS=PACSDCM
            AET=CHRISV3
            PACSIP=134.174.12.21
            PACSPORT=104
            AEC=CHRIS
        ;;
        BCH-christest)
            SWIFTKEY=local
            CUBEKEY=local
            SWIFTPACS=PACSDCM
            AET=CHRISV3
            PACSIP=134.174.12.21
            PACSPORT=104
            AEC=CHRIS
        ;;
        MGH)
            SWIFTKEY=local
            CUBEKEY=local
            SWIFTPACS=PACSDCM
            AET=ELLENGRANT
            PACSIP=172.16.128.91
            PACSPORT=104
            AEC=SDM1
        ;;
        MGH2)
            SWIFTKEY=local
            CUBEKEY=local
            SWIFTPACS=PACSDCM
            AET=ELLENGRANT-CH
            PACSIP=172.16.128.91
            PACSPORT=104
            AEC=SDM1
        ;;
        *) ;;
    esac
}

while :; do
    case $1 in
        -h|-\?|-x|--help)
                        printf "%s" "$G_SYNOPSIS"
                        exit 1                  ;;    
        --container)    PYPX=$2                 ;;
        --baseMount)    BASEMOUNT=$2            ;;
        --debug)        let Gb_DEBUG=1          ;;
        -v)             let G_VERBOSE=1         ;;
        --CUBEKEY)      CUBEKEY=$2              ;;
        --CUBEURL)      CUBEURL=$2                   
                        let Gb_CUBEset=1        ;;
        --CUBEuser)     CUBEusername=$2         
                        let Gb_CUBEset=1        ;;
        --CUBEpassword) CUBEuserpasswd=$2       
                        let Gb_CUBEset=1        ;;
        --SWIFTKEY)     SWIFTKEY=$2             ;;
        --SWIFTHOST)    SWIFTHOST=$2      
                        let Gb_swiftset=1       ;;
        --SWIFTPORT)    SWIFTPORT=$2             
                        let Gb_swiftset=1       ;;
        --SWIFTLOGIN)   SWIFTLOGIN=$2           
                        let Gb_swiftset=1       ;;
        --SWIFTPACS)    SWIFTSERVICEPACS=$2     ;;
        --PACSIP)       QUERYHOST=$2
                        Gb_QUERYHOST=1          ;;
        --PACSport)     QUERYPORT=$2
                        let Gb_QUERYPORT=1      ;;
        --AET)          AET=$2
                        let Gb_AETITLE=1        ;;
        --AEC)          AEC=$2
                        let Gb_CALLTITLE=1      ;;
        --env)          G_INSTITUTION=$2
                        let Gb_institution=1    ;;
        -F)             let Gb_noCheck=1        ;;
        --do)           G_ACTION=$2             ;;
        --report)       G_REPORTARGS=$2         ;;
        --) # End of all options
                        shift
                        break                   ;;
    esac
    shift
done
ARGS=$*

if (( ! $Gb_noCheck )) ; then
    user_check
    host_check
fi
institution_set $G_INSTITUTION

if [[ "$G_REPORTARGS" == "csv" ]] ; then
    G_REPORTARGS=$G_REPORTARGSCSV
fi

if [[ "$G_REPORTARGS" == "" ]] ; then
    G_REPORTARGS="--printReport tabular"
fi


if (( Gb_QUERYHOST )) ; then  PACSIP=$QUERYHOST;    fi
if (( Gb_QUERYPORT )) ; then  PACSPORT=$QUERYPORT;  fi
if (( Gb_AETITLE )) ;   then  AET=$AETITLE;         fi
if (( Gb_CALLTITLE )) ; then  AEC=$CALLTITLE;       fi

DEBUG=""
if (( Gb_DEBUG )) ; then
        DEBUG=" --volume $(pwd)/pypx:/usr/local/lib/python3.8/dist-packages/pypx \
                --volume $(pwd)/bin/pfstorage:/usr/local/bin/pfstorage \
                --volume $(pwd)/bin/px-do:/usr/local/bin/px-do \
                --volume $(pwd)/bin/px-echo:/usr/local/bin/px-echo \
                --volume $(pwd)/bin/px-find:/usr/local/bin/px-find \
                --volume $(pwd)/bin/px-listen:/usr/local/bin/px-listen \
                --volume $(pwd)/bin/px-move:/usr/local/bin/px-move \
                --volume $(pwd)/bin/px-push:/usr/local/bin/px-push \
                --volume $(pwd)/bin/px-register:/usr/local/bin/px-register \
                --volume $(pwd)/bin/px-repack:/usr/local/bin/px-repack \
                --volume $(pwd)/bin/px-report:/usr/local/bin/px-report \
                --volume $(pwd)/bin/px-status:/usr/local/bin/px-status \
                --volume $(pwd)/bin/px-smdb:/usr/local/bin/px-smdb \
 "
fi

if (( Gb_swiftset )) ; then
    docker run --rm -ti -v $BASEMOUNT:$BASEMOUNT $PYPX                         \
    --px-smdb                                                                  \
                --logdir $DB                                                   \
                --action swift                                                 \
                --actionArgs                                                   \
'{\"'$SWIFTKEY'\":{\"ip\":\"'$SWIFTHOST'\",\"port\":\"'$SWIFTPORT'\",\"login\":\"'$SWIFTLOGIN'\"}}'
    exit 0
fi

if (( Gb_CUBEset )) ; then
    docker run --rm -ti -v $BASEMOUNT:$BASEMOUNT $PYPX                             \
    --px-smdb                                                                      \
                --logdir /home/dicom/log                                       \
                --action CUBE                                                  \
                --actionArgs                                                   \
'{\"'$CUBEKEY'\":{\"url\":\"'$CUBEURL'\",\"username\":\"'$CUBEusername'\",\"password\":\"'$CUBEuserpasswd'\"}}'
    exit 0
fi

# The --tty --interactive is necessary to allow for realtime
# logging of activity
# G_REPORTARGS="--printReport tabular"
QUERY="docker run $DEBUG                                                       \
            --tty --interactive                                                \
            --rm                                                               \
            --volume $BASEMOUNT:$BASEMOUNT                                     \
            $PYPX                                                              \
    --px-find                                                                  \
            --aec $AEC                                                         \
            --aet $AET                                                         \
            --serverIP $PACSIP                                                 \
            --serverPort $PACSPORT                                             \
            --db $DB                                                           \
            --verbosity 1                                                      \
            --json                                                             \
            $ARGS"

if (( !${#G_ACTION} )) ; then
    CLI="$QUERY                                                               |\
    docker run --rm -i -v $BASEMOUNT:$BASEMOUNT $PYPX                          \
    --px-report                                                                \
                --colorize dark                                                \
                $G_REPORTARGS"
else
    if (( $(substrInStr retrieve "$G_ACTION") )) ; then
        CLI="$QUERY --then retrieve --withFeedBack"
    fi
    if (( $(substrInStr push "$G_ACTION") )) ; then
        CLI="$QUERY --then push --withFeedBack \
            --thenArgs '{\\\"db\\\":\\\"$DB\\\",\\\"swift\\\":\\\"$SWIFTKEY\\\",\\\"swiftServicesPACS\\\":\\\"$SWIFTSERVICEPACS\\\",\\\"swiftPackEachDICOM\\\":true}'"
    fi
    if (( $(substrInStr register "$G_ACTION") )) ; then
        CLI="$QUERY --then register --withFeedBack \
            --thenArgs '{\\\"db\\\":\\\"$DB\\\",\\\"CUBE\\\":\\\"$CUBEKEY\\\",\\\"swiftServicesPACS\\\":\\\"$SWIFTSERVICEPACS\\\",\\\"parseAllFilesWithSubStr\\\":\\\"dcm\\\"}'"
    fi
    if (( $(substrInStr status "$G_ACTION") )) ; then
        CLI="$QUERY --then status --withFeedBack"
    fi
fi

if (( G_VERBOSE )) ; then
    CLIp=$(echo "$CLI" | sed 's/--/\n\t--/g' | sed 's/\(.*\)/\1 \\/' | sed 's/        \+/ /')
    printf "%s\n" "$CLIp"
fi
eval $CLI
