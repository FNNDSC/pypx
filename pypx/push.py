# Global modules
import  subprocess
import  pudb
import  json
import  pfmisc
from    pfmisc._colors      import  Colors

import  os
from    os                  import  listdir
from    os.path             import  isfile, join

from    .pfstorage          import  swiftStorage

# PYPX modules
from .base import Base

class Push(Base):
    """
        ``px-push`` is the primary vehicle for transmitting a DICOM file
        to a remote location. The remote location can be either another
        PACS node (in which case the PACS related args are used), or
        swift storage (in which the swift related args are used). In the
        case of swift storage, and if CUBE related args are used, then
        this module will also register the files that have been pushed
        to the CUBE instance.
    """

    def __init__(self, arg):
        """
        Constructor.

        Largely simple/barebones constructor that calls the Base()
        and sets up the executable name.
        """
        self.l_files        : list  = []

        # Check if an upstream 'reportData' exists, and if so
        # merge those args with the current namespace:
        if 'reportData' in arg.keys():
            d_argCopy           = arg.copy()
            # "merge" these 'arg's with upstream.
            arg.update(arg['reportData']['args'])
            # Since this might overwrite some args specific to this
            # app, we update again to the copy.
            arg.update(d_argCopy)

        super(Push, self).__init__(arg)
        self.dp             = pfmisc.debug(
                                verbosity   = self.verbosity,
                                within      = 'Push',
                                syslog      = False
        )
        self.log            = self.dp.qprint
        self.arg['name']    = "Push/PfStorage"

    def movescu_command(self, opt={}) -> str:
        command = '-S --move ' + opt['aet']
        command += ' --timeout 5'
        command += ' -k QueryRetrieveLevel=SERIES'
        command += ' -k StudyInstanceUID='  + opt['study_uid']
        command += ' -k SeriesInstanceUID=' + opt['series_uid']

        str_cmd     = "%s %s %s" % (
                        self.movescu,
                        command,
                        self.commandSuffix()
        )
        return str_cmd

    def pushToPACS_true(self):
        """
        Return a bool condition that indicates if the image data is
        to be sent to a PACS
        """
        b_pushToPACS        : bool  = False
        return b_pushToPACS

    def pushToSwift_true(self):
        """
        Return a bool condition that indicates if the image data is
        to be sent to swift storage
        """
        b_pushToSwift       : bool  = True
        return b_pushToSwift

    def path_pushToSwift(self):
        """
        Push files in the path <xcrdir> to swift
        """
        d_do                : dict  = {
            'action'    :       'objPut',
            'args'      : {
                'localpath'         :   self.arg['str_xcrdir'],
                'DICOMsubstr'       :   self.arg['str_filesubstr'],
                'packEachDICOM'     :   self.arg['b_swiftPackEachDICOM'],
                'toLocation'        :   'SERVICES/PACS/%s/%%pack' % \
                                            self.arg['str_swiftServicesPACS'],
                'mapLocationOver'   :   self.arg['str_xcrdir']
            }
        }
        d_store     = swiftStorage(self.arg).run(d_do)

        return d_store

    def run(self, opt={}) -> dict:

        d_push              : dict  = {}

        if self.pushToSwift_true():
            d_push  = self.path_pushToSwift()

        return d_push
