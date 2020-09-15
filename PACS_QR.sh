#!/bin/bash

source common.bash
let G_VERBOSE=0
let G_DEBUG=0
G_DICOMDIR=/neuro/users/chris/data-ng
G_AETITLE=CHIPS
let Gb_AETITLE=0
G_QUERYHOST=127.0.0.1
let Gb_QUERYHOST=0
G_QUERYPORT=4242
let Gb_QUERYPORT=0
G_CALLTITLE=ORTHANC
let Gb_CALLTITLE=0
G_INSTITUTION=BCH-chrisdev
G_HOST=titan
G_USER=chris-local
G_DOCKERORG=fnndsc
G_SYNOPSIS="

  NAME

        PACS_QR.sh

  SYNOPSIS

        PACS_QR.sh                                                      \\
                        [-h <institution>]                              \\
                        [-P <PACSserver>]                               \\
                        [-p <PACSport>]                                 \\
                        [-a <AETitle>]                                  \\
                        [-c <CalledAETitle>]                            \\
                        [-H <hostCheck>]                                \\
                        [-U <userCheck>]                                \\
                        [-D]                                            \\
                        [-d <dicomDir>]                                 \\
                        [-C]                                            \\
                        [-r <dockerorg>]                                \\
                        [-v]                                            \\
                         -Q <px-find.py args>

  DESC

        PACS_QR.sh is a thin convenience wrapper around a containerized
        call to \"fnndsc/pypx --px-find\".

        Given the very strong and very implicit dependencies of this script
        on an appropriately configured PACS server, as well a valid path
        from the PACS transmission to a specific 'host', the following
        pre-requesites are required:

  PRE-REQUISITES

        In the BCH network, if you are running this script stand-alone, you
        MUST:

        * BE ABLE TO RUN DOCKER COMMANDS!
        * have an ssh tunnel from 'pretoria:10402' to '$G_HOST:10402' (**)
        * make sure you are running this on host 'titan'
        * make note that any pulled DICOMs are saved to

                /neuro/users/chris/data/dicom-ng

        (**) typical cmd for setting up a tunnel (on host 'pretoria'):

        ssh -g -f -N -X -L 10402:localhost:10402 rudolphpienaar@titan

  ARGS

        -h <institution>
        If specified, assigns some default AETITLE and PACS variables
        appropriate to the <institution>. Valid <institutions> are

            [
                'Orthanc',
                'BCH',
                'BCH-chris',
                'BCH-chrisdev',
                'BCH-christest',
                'MGH',
                'MGH2'
            ]

        [-P <PACSserver>]
        Explicitly set the PACS IP to <PACSserver>.

        [-p <PACSport>]
        Explicitly set the PACS port to <PACSport>.

        [-a <AETitle>]
        Explicitly set the AETitle of the client to <AETitle>

        [-c <CalledAETitle>]
        Explicitly set the CalledAETitle to <CalledAETitle>.

        [-H <hostCheck>]
        Check that *this* host is the same as the <hostCheck>. This is
        a convenient way to check that the script runs only on a host
        that has appropriate ssh tunnel connections configured for
        receiving DICOM data transimission.

        [-U <userCheck>]
        Check that *this* user is the same as <userCheck>. Since this
        script calls the docker daemon, the user running the script
        needs to in the docker group. This is convenient method of
        making sure that a docker approved user is executing this script.

        [-D]
        If specified, volume mount source files into the container for
        debugging.

        NOTE: This assumes the script is run from the root github repo
              directory!

        [-d <dicomDir>]
        Set the <dicomDir> in the host that is mounted into the container. This
        MUST be an ABSOLUTE directory spec.

        [-C]
        If specified, delete and recreate the <dicomDir> (assuming appropriate
        file system permissions).

        [-r <dockerorg>]
        The docker organization (or 'base' repository). This defauls to 'fnndsc'
        but if you have built a 'local' version -- with for example:

            docker build -t local/pypx

        use

          -r local

        to use this 'local' build.

        [-v]
        If specified, toggle verbose output on which essentially just shows
        the final docker CLI.

        -Q <px-find args>
        This flag captures CLI that are passed to the px-find module.

  EXAMPLE

    QUERY

        PACS_QR.sh -Q \"--PatientID 1234567\"

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

    RETRIEVE

        PACS_QR.sh -Q \"--PatientID 1234567 --retrieve --printReport ''\"

    NOTE: 1234567 is a fake PatientID. Please do not actually use that!

"

A_hostCheck="checking on this host"
EM_hostCheck="This must be run as user '$G_USER' and on host '$G_HOST'!

                ┌─────────────────────────────────────────┐
                │  ssh chris-local@titan.tch.harvard.edu  │
                └─────────────────────────────────────────┘
"
EC_hostCheck="10"

A_userCheck="checking on user, you are '$(whoami)'"
EM_userCheck="This must be run as user '$G_USER' and on host '$G_HOST'!

                ┌─────────────────────────────────────────┐
                │  ssh chris-local@titan.tch.harvard.edu  │
                └─────────────────────────────────────────┘
"
EC_userCheck="12"

function host_check
{
    local HOST=$(hostname)
    local b_retrieve=0
    local b_move=0

    if [[ "$ARGS" == *"retrieve"* ]] ; then
        b_retrieve=1
    fi
    if [[ "$ARGS" == *"move"* ]] ; then
        b_move=1
    fi

    if (( $b_move || $b_retrieve )) ; then
        if [[ $HOST != $G_HOST ]] ; then
            fatal hostCheck
        fi
        echo "
┌────────────────│ PACS PULL │─────────────────┐
│       A PACS PULL has been specified.        │
│                                              │
│   Any retrieved results will be saved here:  │
└──────────────────────────────────────────────┘
    $G_DICOMDIR

        "
        exit 1
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
          G_AETITLE=CHIPS
          G_QUERYHOST=127.0.0.1
          G_QUERYPORT=4242
          G_CALLTITLE=ORTHANC
        ;;
        BCH-chris)
          G_AETITLE=FNNDSC-CHRIS
          G_QUERYHOST=134.174.12.21
          G_QUERYPORT=104
          G_CALLTITLE=CHRIS
        ;;
        BCH-chrisdev)
          G_AETITLE=FNNDSC-CHRISDEV
          G_QUERYHOST=134.174.12.21
          G_QUERYPORT=104
          G_CALLTITLE=CHRIS
        ;;
        BCH-christest)
          G_AETITLE=FNNDSC-CHRISTEST
          G_QUERYHOST=134.174.12.21
          G_QUERYPORT=104
          G_CALLTITLE=CHRIS
        ;;
        MGH)
          G_AETITLE=ELLENGRANT
          G_QUERYHOST=172.16.128.91
          G_QUERYPORT=104
          G_CALLTITLE=SDM1
        ;;
        MGH2)
          G_AETITLE=ELLENGRANT-CH
          G_QUERYHOST=172.16.128.91
          G_QUERYPORT=104
          G_CALLTITLE=SDM1
        ;;
    esac
}

while getopts h:Q:DCd:H:P:p:a:c:r:v option ; do
    case "$option"
    in
        Q) ARGS="$OPTARG"               ;;
        d) G_DICOMDIR=$OPTARG           ;;
        r) G_DOCKERORG=$OPTARG          ;;
        H) G_HOST=$OPTARG               ;;
        C) let Gb_CLEAR=1               ;;
        D) let Gb_DEBUG=1               ;;
        v) let G_VERBOSE=1              ;;
        P) QUERYHOST=$OPTARG
           Gb_QUERYHOST=1               ;;
        p) QUERYPORT=$OPTARG
           Gb_QUERYPORT=1               ;;
        a) AETITLE=$OPTARG
           Gb_AETITLE=1                 ;;
        c) CALLTITLE=$OPTARG
           Gb_CALLTITLE=1               ;;
        h) G_INSTITUTION=$OPTARG
           let Gb_institution=1         ;;
        *) synopsis_show
           shut_down 1                  ;;
    esac
done

user_check
host_check
institution_set $G_INSTITUTION

if (( Gb_QUERYHOST )) ; then  G_QUERYHOST=$QUERYHOST;  fi
if (( Gb_QUERYPORT )) ; then  G_QUERYPORT=$QUERYPORT;  fi
if (( Gb_AETITLE )) ;   then  G_AETITLE=$AETITLE;      fi
if (( Gb_CALLTITLE )) ; then  G_CALLTITLE=$CALLTITLE;  fi

if (( Gb_CLEAR )) ; then
        printf "%80s" "Removing $G_DICOMDIR... "
        sudo rm -fr $G_DICOMDIR
        printf "[ OK ]\n"
        printf "%80s" "Creating $G_DICOMDIR... "
        mkdir $G_DICOMDIR
        chmod 777 $G_DICOMDIR
        printf "[ OK ]\n"
fi

DEBUG=""
if (( Gb_DEBUG )) ; then
        DEBUG=" --volume $(pwd)/pypx:/usr/local/lib/python3.8/dist-packages/pypx \
                --volume $(pwd)/bin/px-echo:/usr/local/bin/px-echo \
                --volume $(pwd)/bin/px-find:/usr/local/bin/px-find \
                --volume $(pwd)/bin/px-move:/usr/local/bin/px-move \
                --volume $(pwd)/bin/px-listen:/usr/local/bin/px-listen "
fi

# The --tty --interactive is necessary to allow for realtime
# logging of activity
CLI="docker run                                 \
            --tty --interactive                 \
            --rm                                \
            --publish 10402:10402               \
            --volume $G_DICOMDIR:/dicom $DEBUG  \
            ${G_DOCKERORG}/pypx                 \
            --px-find                           \
            --aec $G_CALLTITLE                  \
            --aet $G_AETITLE                    \
            --serverIP $G_QUERYHOST             \
            --serverPort $G_QUERYPORT           \
            --colorize dark                     \
            --printReport tabular               \
            $ARGS"

if (( G_VERBOSE )) ; then
    CLIp=$(echo "$CLI" | sed 's/--/\n\t--/g' | sed 's/\(.*\)/\1 \\/' | sed 's/        \+/ /')
    printf "%s\n" "$CLIp"
fi

exec $CLI
