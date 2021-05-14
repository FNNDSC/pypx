# Global modules
import  subprocess
import  pudb
import  json
import  pfmisc
from    pfmisc._colors      import  Colors
from    pypx                import pfstorage

import  os
from    os                  import  listdir
from    os.path             import  isfile, join


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

    def filesOnFS_determine(self):
        """
        Determine the location on the file system of the directory
        containing files to all push.
        """
        self.filesToPush_determine()

    def filesToPush_determine(self):
        """
        Based on the pattern of CLI calling flags, determine which
        file system files to actually push.

        The location of the files to push is specified either directly
        with explicit CLI for xcrdir/xcrfile or indirectly via study/series
        lookup.
        """

        if len(self.arg['str_xcrdirfile']):
            self.arg['str_xcrdir']      = os.path.dirname(
                                                self.arg['str_xcrdirfile']
                                        )
            self.arg['str_xcrfile']     = os.path.basename(
                                                self.arg['str_xcrdirfile']
                                        )

        if self.arg['str_filesubstr']:
            # First create a list of all the files...
            self.l_files    = [
                f                                                       \
                    for f in listdir(self.arg['str_xcrdir'])              \
                        if isfile(join(self.arg['str_xcrdir'], f))
            ]
            # Now filter them according to the passed filesubstr
            self.l_files    = [
                x                                                       \
                    for y in self.arg['str_filesubstr'].split(',')        \
                        for x in self.l_files if y in x
            ]
        else:
            self.l_files.append(self.arg['str_xcrfile'])


    def __init__(self, arg):
        """
        Constructor.

        Largely simple/barebones constructor that calls the Base()
        and sets up the executable name.
        """
        pudb.set_trace()

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
        self.swift          = pfstorage.swiftStorage(args = self.arg)

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

    def pushToSwift_files(self):
        """
        Push the self.l_files list to swift storage
        """
        d_ls = self.swift.ls(swiftpath = 'chris/uploads')
        b_exists = self.swift.objExists(swiftpath = 'chrris/uploads/pl-fshack-infant/SAG-anon.nii')

    def swift_filesDelete(self):
        """
        bulk delete files from swift
        """

    def registerToCUBE_true(self):
        """
        Return a bool condition that indicates if the image data is
        to be registered to CUBE
        """
        b_registerToCUBE    : bool  = False
        return b_registerToCUBE


    def run(self, opt={}) -> dict:

        d_push              : dict  = {}

        pudb.set_trace()
        self.filesOnFS_determine()
        if self.pushToSwift_true():
            self.pushToSwift_files()

        return d_push
