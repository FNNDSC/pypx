#!/usr/bin/env bash


SYNOPSIS="

NAME

  storescp.sh

SYNPOSIS

  storescp.sh           [-p <port>]                                         \\
                        [-E <execRootPath>]                                 \\
                        [-D <dataRootPath>]

DESC

  'storescp.sh' is a simple wrapper around a 'storescp' listener
  service. Due to complexities in embedding the full storescp
  command in an xinet.d service file, an alternate solution is
  to place a simpler script in the service file. This script in
  turn launches the actual listener.
"

PORT=10402
EXECROOTPATH="/usr/local/bin"
DATAROOTPATH="/home/dicom"
TMPINCOMINGDATA=/tmp/data

while getopts "p:E:D:t:" opt; do
    case $opt in
        t) TMPINCOMINGDATA=$OPTARG              ;;
        p) PORT=$OPTARG                         ;;
        E) EXECROOTPATH=$OPTARG                 ;;
        D) DATAROOTPATH=$OPTARG                 ;;
    esac
done
mkdir $TMPINCOMINGDATA
eval storescp -od $TMPINCOMINGDATA -pm -sp -xcr \"$EXECROOTPATH/px-repack --xcrdir \#p --xcrfile \#f --verbosity 0 --logdir $DATAROOTPATH/log --datadir $DATAROOTPATH/data --cleanup\" $PORT
