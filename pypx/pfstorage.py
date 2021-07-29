#!/usr/bin/env python3.5

import  abc

import  sys
from    io              import  BytesIO as IO
from    pathlib         import  Path
import  cgi
import  json
import  urllib
import  ast
import  shutil
import  datetime
import  time
import  inspect
import  pprint

import  threading
import  platform
import  socket
import  psutil
import  os
import  multiprocessing
import  configparser
import  swiftclient
import  traceback
from    argparse            import  Namespace

import  pfmisc

# debugging utilities
import  pudb

from    pypx                import  repack

# pfstorage local dependencies
from    pfmisc._colors      import  Colors
from    pfmisc.debug        import  debug
from    pfmisc.C_snode      import  *
from    pfstate             import  S

def static_vars(**kwargs):
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate


class D(S):
    """
    A derived 'pfstate' class that keeps system state.
    """

    def __init__(self, arg, *args, **kwargs):
        """
        Constructor
        """

        self.state_create(
        {
            "swift": {
                "auth_url":                 "http://%s:%s/auth/v1.0" % \
                                            (arg['str_swiftIP'], arg['str_swiftPort']),
                "username":                 arg['str_swiftLogin'],
                "key":                      "testing",
                "container_name":           "users",
                "auto_create_container":    True,
                "file_storage":             "swift.storage.SwiftStorage"
            }
        },
        *args, **kwargs
        )

        self.log    = self.dp.qprint

class PfStorage(metaclass = abc.ABCMeta):

    def state(self, *args):
        """
        Interact with the state object.

        If called with one arg, return the value at that location
        in the state tree representation.

        If called with two args, set the value at a given tree
        state representation.

        For example,

            key = state('/swift/key')

        returns the "/swift/key" while

            state('/swify/key', "a new value")

        sets "/swift/key" to "a new value"
        """

        if len(args) == 1:
            return self.S.T.cat(args[0])
        else:
            self.S.T.touch(args[0], args[1])

    def __init__(self, arg, *args, **kwargs):
        """
        The core constructor -- essentially this adds the main
        operational module objects to this class.
        """

        # pudb.set_trace()
        self.arg            = arg
        self.S              = D(arg, *args, **dict(kwargs, useGlobalState = True))
        self.dp             = pfmisc.debug(
                                verbosity   = self.state('/this/verbosity'),
                                within      = self.state('/this/name')
                            )
        self.log            = self.dp.qprint
        self.packer         = repack.Process(
                                repack.args_impedanceMatch(Namespace(**arg))
                            )
        # A generic member placeholder for an unspecified object --
        # In the case of say a DICOM read, this object is assigned the
        # result of the read and can be used by a friendly caller.
        self.obj            = None

    def filesFind(self, *args, **kwargs) -> dict:
        """
        This method simply returns a list of files
        and directories down a filesystem tree starting
        from the kwarg:

            root        = <someStartPath>
            fileSubStr  = <someSubStr>

        where the 'fileSubStr' optionally filters all the files
        with <someSubStr>.
        """
        d_ret           : dict  = {
            'status':   False,
            'l_fileFS': [],
            'l_dirFS':  [],
            'numFiles': 0,
            'numDirs':  0
        }
        str_rootPath    : str   = ''
        str_fileSubStr  : str   = ''
        for k,v in kwargs.items():
            if k == 'root'          : str_rootPath      = v
            if k == 'fileSubStr'    : str_fileSubStr    = v
        if len(str_rootPath):
            # Create a list of all files down the <str_rootPath>
            for root, dirs, files in os.walk(str_rootPath):
                for filename in files:
                    d_ret['l_fileFS'].append(os.path.join(root, filename))
                    d_ret['status'] = True
                for dirname in dirs:
                    d_ret['l_dirFS'].append(os.path.join(root, dirname))
            if len(str_fileSubStr):
                d_ret['l_fileFS']   = [
                                        f for f in d_ret['l_fileFS']
                                            if str_fileSubStr in f
                                        ]

        d_ret['numFiles']   = len(d_ret['l_fileFS'])
        d_ret['numDirs']    = len(d_ret['l_dirFS'])
        return d_ret

    @abc.abstractmethod
    def connect(self, *args, **kwargs):
        """
        The base connection class.

        This handles the connection to the openstorage providing service.
        """

    @abc.abstractmethod
    def ls_process(self, *args, **kwargs):
        """
        The base ls process method.

        This handles the ls processing in the openstorage providing service.
        """

    @abc.abstractmethod
    def ls(self, *args, **kwargs):
        """
        Base listing class.

        Provide a listing of resources in the openstorage providing
        service.
        """

    @abc.abstractmethod
    def objExists(self, *args, **kwargs):
        """
        Base object existance class.

        Check if an object exists in the openstorage providing service.
        """

    @abc.abstractmethod
    def objPut(self, *args, **kwargs):
        """
        Base object put method.

        Put a list of (file) objects into storage.
        """

    @abc.abstractmethod
    def objPull(self, *args, **kwargs):
        """
        Base object pull method.

        Pull a list of (file) objects from storage.
        """

class swiftStorage(PfStorage):

    def __init__(self, arg, *args, **kwargs):
        """
        Core initialization and logic in the base class
        """
        # Check if an upstream object exists, and if so
        # merge those args with the current namespace:
        if 'upstream' in arg.keys():
            d_argCopy           = arg.copy()
            # "merge" these 'arg's with upstream.
            arg.update(arg['reportData']['args'])
            # Since this might overwrite some args specific to this
            # app, we update again to the copy.
            arg.update(d_argCopy)

        PfStorage.__init__(self, arg, *args, **kwargs)

    @static_vars(str_prependBucketPath = "")
    def connect(self, *args, **kwargs) -> dict:
        """
        Connect to swift storage and return the connection object,
        as well an optional "prepend" string to fully qualify
        object location in swift storage.

        The 'prependBucketPath' is somewhat 'legacy' to a similar
        method in charm.py and included here with the idea
        to eventually converge on a single swift-based intermediary
        library for both pfcon and CUBE.
        """

        d_ret       = {
            'status':               True,
            'conn':                 None,
            'user':                 self.state('/swift/username'),
            'key':                  self.state('/swift/key'),
            'authurl':              self.state('/swift/auth_url'),
            'container_name':       self.state('/swift/container_name')
        }

        # initiate a swift service connection, based on internal
        # settings already available in the django variable space.
        try:
            d_ret['conn'] = swiftclient.Connection(
                user    = d_ret['user'],
                key     = d_ret['key'],
                authurl = d_ret['authurl']
            )
        except:
            d_ret['status'] = False

        return d_ret

    def rmtree_process(self, *args, **kwargs) -> dict:
        """
        Process the 'rmtree' directive.
        """
        d_ret       = {
            'status':   False,
            'msg':      "No 'meta' JSON directive found in request"
        }
        d_msg       = {}
        d_args      = {}

        for k, v in kwargs.items():
            if k == 'request':      d_msg       = v

        if 'args' in d_msg:
            d_args  = d_msg['args']
            d_ret   = self.rmtree(**d_args)

        return d_ret


    def rmtree(self, **kwargs)  -> dict:
        """
        Remove a "tree" of objects in swift
        """
        d_ret = {
            'status'    : False,
            'dellist'   : []
        }

        d_conn  = self.connect(**kwargs)

        # Get a list of objects
        d_ls    = self.ls(**kwargs)
        if d_ls['status']:
            d_ret['status']     = True
            d_ret['dellist']    = d_ls['list_ls']
            for obj in d_ls['list_ls']:
                d_conn['conn'].delete_object(
                    d_conn['container_name'],
                    obj
                )

        return d_ret

    def ls_process(self, *args, **kwargs) -> dict:
        """
        Process the 'ls' directive (in the appropriate subclass).
        For the case of 'swift', the return dictionary contains a
        key, 'objectDict' containing a list of dictionaries which
        in turn have keys:
            'hash', 'last_modified', 'bytes', 'name', 'content-type'
        """
        d_ret       : dict = {'status': False}
        d_ls        : dict = {}
        d_lsFilter  : dict = {}
        d_msg       : dict = {}
        d_args      : dict = {}
        l_retSpec   : list = ['name', 'bytes', 'hash', 'last_modified']

        for k, v in kwargs.items():
            if k == 'request':      d_msg   = v

        if 'args' in d_msg:
            d_args  = d_msg['args']
            if 'retSpec' in d_args:
                l_retSpec   = d_args['retSpec']
            try:
                d_ls = self.ls(**d_args)
                d_ret['status'] = d_ls['status']
                if len(l_retSpec):
                    d_lsFilter  = [ {x: y[x] for x in l_retSpec}
                                    for y in d_ls['listDict_obj'] ]
                    d_ret['ls'] = d_lsFilter
                else:
                    d_ret['ls'] = d_ls
            except Exception as e:
                d_ret['lsError'] = '%s' % e

        return d_ret

    def ls(self, **kwargs) -> dict:
        """
        Return a dictionary of information about objects in swiftstorage.

        Behaviour specifiers (kwargs):

            path   = <locationInSwift>
            substr      = filter return objects on <substr> in their name
            retSpec     = list of specs to return.
                        Default: ['hash', 'last_modified', 'bytes', 'name']

        Return
        {
            'status':           the status of this call (True/False),
            'listDict_obj':     a list of dictionary objects,
            'list_ls':          a list of object names at the query path,
        }

        """

        l_ls                    : list  = []    # The listing of names to return
        ld_obj                  : list  = []    # List of dictionary objects in swift
        str_path                : str   = '/'
        str_subString           : str   = ''
        b_status                : bool  = False
        l_retSpec               : list  = []

        for k,v in kwargs.items():
            if k == 'path'      : str_path            = v
            if k == 'substr'    : str_subString       = v
            if k == 'retSpec'   : l_retSpec           = v

        # Remove any leading noise on the str_path, specifically
        # any leading '.' characters.
        # This is probably not very robust!
        while str_path[:1] == '.':  str_path    = str_path[1:]

        d_conn          = self.connect(**kwargs)
        if d_conn['status']:
            conn        = d_conn['conn']

            # get the full list of objects in Swift storage with given prefix
            ld_obj = conn.get_container(
                        d_conn['container_name'],
                        prefix          = str_path,
                        full_listing    = True)[1]

            if len(str_subString):
                ld_obj      = [x for x in ld_obj if str_subString in x['name']]

            l_ls            = [x['name'] for x in ld_obj]

            if len(l_retSpec):
                ld_obj      = [ {x: y[x] for x in l_retSpec}
                                    for y in ld_obj ]

            if len(l_ls):   b_status    = True

        return {
            'status':       b_status,
            'listDict_obj': ld_obj,
            'list_ls':      l_ls,
            'conn':         conn
        }

    def objExists(self, **kwargs) -> bool:
        """
        Return True/False if the object at 'path' exists in swift storage.
        """
        b_exists                : bool      = False
        str_obj                 : str       = ''

        for k,v in kwargs.items():
            if k == 'path'      : str_obj   = v

        if len(str_obj):
            kwargs['path']          = str_obj
            d_ls                    = self.ls(**kwargs)
            if d_ls['status']:
                for name in d_ls['list_ls']:
                    if name == str_obj:
                        b_exists = True

        return b_exists

    def objPut_process(self, *args, **kwargs) -> dict:
        """
        Process the 'objPut' directive.

        DICOM handling
        --------------

        A special behaviour is available for DICOM files, triggered by passing
        a kwarg of 'DICOMsubstr = <X>'. In this case, DICOM files (as identi-
        fied by containing the substring pattern within the filename) will be
        read for tag information used to generate the fully qualified storage
        path.

        This fully qualified storage path will be substituted into the
        'toLocation = <someswiftpath>' by replacing the special tag
        '%pack' in the <someswiftpath>.

        NOTE:
        * Typically a list of files all constitute the same DICOM SERIES
          and as such, only one of file in the list needs to be processed for
          packing tags.
        * If the 'do' 'objPut' directive contains a true value for the field
          'packEachDICOM', then each DICOM will be explicitly examined and
          packed individually.

        """

        def toLocation_updateWithDICOMtags(str_DICOMfilename) -> dict:
            """
            Read the str_DICOMfilename, determine the pack path,
            and update the 'toLocation' if necessary.

            Return the original and modified 'toLocation' and status flag.
            """
            b_pack                      = False
            d_DICOMread                 = self.packer.DICOMfile_read(file = str_DICOMfilename)
            d_path                      = self.packer.packPath_resolve(d_DICOMread)
            self.obj[str_DICOMfilename] = d_DICOMread
            str_origTo                  = d_args['toLocation']
            if '%pack' in d_args['toLocation']:
                b_pack  = True
                d_args['toLocation'] = \
                    d_args['toLocation'].replace('%pack', d_path['packDir'])
            return {
                'pack'              : b_pack,
                'originalLocation'  : str_origTo,
                'path'              : d_path,
                'toLocation'        : d_args['toLocation']
            }

        def files_putSingly() -> dict:
            """
            Handle a single file put, return and update d_ret
            """
            nonlocal d_ret
            nonlocal b_singleShot
            d_pack  : dict          = {}
            b_singleShot            = True
            d_ret                   = {
                'status'            : False,
                'localFileList'     : [],
                'objectFileList'    : []
            }
            self.obj                = {}
            # pudb.set_trace()
            for f in d_fileList['l_fileFS']:
                d_pack                  = toLocation_updateWithDICOMtags(f)
                d_args['file']          = f
                d_args['remoteFile']    = d_pack['path']['imageFile']
                d_put                   = self.objPut(**d_args)
                d_ret[f]                = d_put
                d_args['toLocation']    = d_pack['originalLocation']
                d_ret['status']         = d_put['status']
                if d_ret['status']:
                    d_ret['localFileList'].append(d_put['localFileList'][0])
                    d_ret['objectFileList'].append(d_put['objectFileList'][0])
                else:
                    break
            return d_ret

        d_ret           :   dict  = {
            'status'    :   False,
            'msg'       :   "No 'arg' JSON directive found in request"
        }

        d_msg           : dict  = {}
        d_args          : dict  = {}
        str_localPath   : str   = ""
        str_DICOMsubstr : str   = ""
        b_singleShot    : bool  = False

        for k, v in kwargs.items():
            if k == 'request':      d_msg       = v
        # pudb.set_trace()
        if 'args' in d_msg:
            d_args  = d_msg['args']
            if 'localpath' in d_args:
                str_localPath       = d_args['localpath']
                if 'DICOMsubstr' in d_args:
                    d_fileList      = self.filesFind(
                                        root        = str_localPath,
                                        fileSubStr  = d_args['DICOMsubstr']
                                    )
                    if 'packEachDICOM' in d_args:
                        if d_args['packEachDICOM']: files_putSingly()
                    if len(d_fileList['l_fileFS']) and not b_singleShot:
                        toLocation_updateWithDICOMtags(d_fileList['l_fileFS'][0])
                else:
                    d_fileList      = self.filesFind(
                                        root        = str_localPath
                    )
                if d_fileList['status'] and not b_singleShot:
                    d_args['fileList']  = d_fileList['l_fileFS']
                    d_ret               = self.objPut(**d_args)
                elif not d_fileList['status']:
                    d_ret['msg']    = 'No valid file list generated'
        return d_ret

    def objPut(self, *args, **kwargs) -> dict:
        """
        Put an object (or list of objects) into swift storage.

        This method also "maps" tree locations in the local storage
        to new locations in the object storage. For example, assume
        a list of local locations starting with:

                /home/user/project/data/ ...

        and we want to pack everything in the 'data' dir to
        object storage, at location '/storage'. In this case, the
        pattern of kwargs specifying this would be:

                fileList = ['/home/user/project/data/file1',
                            '/home/user/project/data/dir1/file_d1',
                            '/home/user/project/data/dir2/file_d2'],
                toLocation      = '/storage',
                mapLocationOver = '/home/user/project/data'

        will replace, for each file in <fileList>, the <mapLocationOver> with
        <inLocation>, resulting in a new list

                '/storage/file1',
                '/storage/dir1/file_d1',
                '/storage/dir2/file_d2'

        """
        b_status                : bool  = True
        l_localfile             : list  = []    # Name on the local file system
        l_remotefileName        : list  = []    # A replacement for the remote filename
        l_objectfile            : list  = []    # Name in the object storage
        str_swiftLocation       : str   = ''
        str_mapLocationOver     : str   = ''
        str_localfilename       : str   = ''
        str_storagefilename     : str   = ''
        str_swiftLocation       : str   = ""
        str_remoteFile          : str   = ""
        d_ret                   : dict  = {
                                            'status':           b_status,
                                            'localFileList':    [],
                                            'objectFileList':   [],
                                            'localpath':        ''
                                        }

        d_conn  = self.connect(*args, **kwargs)

        for k,v in kwargs.items():
            if k == 'file'              : l_localfile.append(v)
            if k == 'remoteFile'        : l_remotefileName.append(v)
            if k == 'remoteFileList'    : l_remotefileName      = v
            if k == 'fileList'          : l_localfile           = v
            if k == 'toLocation'        : str_swiftLocation     = v
            if k == 'mapLocationOver'   : str_mapLocationOver   = v

        if len(str_mapLocationOver):
            # replace the local file path with object store path
            l_objectfile    = [w.replace(str_mapLocationOver, str_swiftLocation) \
                                for w in l_localfile]
        else:
            # Prepend the swiftlocation to each element in the localfile list:
            l_objectfile    = [str_swiftLocation + '{0}'.format(i) for i in l_localfile]

        # Check and possibly change the actual file *names* to put into swift storage
        # (the default is to use the same name as the local file -- however in the
        # case of DICOM files, the actual final file name might also change)
        if len(l_remotefileName):
            l_objectfile    = [l.replace(os.path.basename(l), f) for l,f in
                                    zip(l_objectfile, l_remotefileName)]

        d_ret['localpath']  = os.path.dirname(l_localfile[0])

        if d_conn['status']:
            for str_localfilename, str_storagefilename in zip(l_localfile, l_objectfile):
                try:
                    d_ret['status'] = True and d_ret['status']
                    with open(str_localfilename, 'rb') as fp:
                        d_conn['conn'].put_object(
                            d_conn['container_name'],
                            str_storagefilename,
                            contents=fp.read()
                        )
                except Exception as e:
                    d_ret['error']  = '%s' % e
                    d_ret['status'] = False
                d_ret['localFileList'].append(str_localfilename)
                d_ret['objectFileList'].append(str_storagefilename)
        return d_ret

    def objPull_process(self, *args, **kwargs):
        """
        Process the 'objPull' directive.
        """
        d_ret       :   dict  = {
            'status':   False,
            'msg'   :   "No 'meta' JSON directive found in request"
        }
        d_msg       = {}
        d_args      = {}

        for k, v in kwargs.items():
            if k == 'request':      d_msg       = v

        if 'args' in d_msg:
            d_args  = d_msg['args']
            d_ret   = self.objPull(**d_args)

        return d_ret

    def objPull(self, *args, **kwargs):
        """
        Pull an object (or set of objects) from swift storage and
        onto the local filesystem.

        This method can also "map" locations in the object storage
        to new locations in the filesystem storage. For example, assume
        a list of object locations starting with:

                user/someuser/uploads/project/data ...

        and we want to pack everything from 'data' to the local filesystem
        to, for example,

                /some/dir/data

        In this case, the pattern of kwargs specifying this would be:

                    fromLocation    = user/someuser/uploads/project/data
                    toLocation      = /some/dir/data

        if 'toLocation' is not specified, then the local file system
        location will be the 'fromLocation' prefixed with a '/'.

        """
        b_status                : bool  = True
        l_localfile             : list  = []    # Name on the local file system
        l_objectfile            : list  = []    # Name in the object storage
        str_swiftLocation       : str   = ''
        str_mapLocationOver     : str   = ''
        str_localfilename       : str   = ''
        str_storagefilename     : str   = ''
        str_swiftLocation       : str   = ""
        d_ret                   = {
            'status':           b_status,
            'localFileList':    [],
            'objectFileList':   [],
            'localpath':        ''
        }

        d_conn  = self.connect(*args, **kwargs)

        for k,v in kwargs.items():
            if k == 'fromLocation'  : str_swiftLocation   = v
            if k == 'toLocation'    : str_mapLocationOver = v

        kwargs['path']  = str_swiftLocation
        # Get dictionary of objects in storage
        d_ls            = self.ls(*args, **kwargs)

        # List of objects in storage
        l_objectfile    = [x['name'] for x in d_ls['listDict_obj']]

        if len(str_mapLocationOver):
            # replace the local file path with object store path
            l_localfile         = [w.replace(str_swiftLocation, str_mapLocationOver) \
                                    for w in l_objectfile]
        else:
            # Prepend a '/' to each element in the l_objectfile:
            l_localfile         = ['/' + '{0}'.format(i) for i in l_objectfile]
            str_mapLocationOver =  '/' + str_swiftLocation

        d_ret['localpath']          = str_mapLocationOver
        d_ret['currentWorkingDir']  = os.getcwd()

        if d_conn['status']:
            for str_localfilename, str_storagefilename in zip(l_localfile, l_objectfile):
                try:
                    d_ret['status'] = True and d_ret['status']
                    obj_tuple       = d_conn['conn'].get_object(
                                                    d_conn['container_name'],
                                                    str_storagefilename
                                                )
                    str_parentDir   = os.path.dirname(str_localfilename)
                    os.makedirs(str_parentDir, exist_ok = True)
                    with open(str_localfilename, 'wb') as fp:
                        # fp.write(str(obj_tuple[1], 'utf-8'))
                        fp.write(obj_tuple[1])
                except Exception as e:
                    d_ret['error']  = str(e)
                    d_ret['status'] = False
                d_ret['localFileList'].append(str_localfilename)
                d_ret['objectFileList'].append(str_storagefilename)
        return d_ret

    def run(self, opt={}) -> dict:
        """
        Perform the storage operation
        """
        d_actionResult  : dict  = {
            'status'    : False,
            'msg'       : ''
        }
        try:
            # First see if the "do" directive is a CLI
            # flag captured in the self.arg structure
            d_do            : dict  = json.loads(self.arg['do'])
        except:
            # Else, assume that the d_do is the passed opt
            d_do            = opt
        if 'action' in d_do:
            self.log("verb: %s detected." % d_do['action'],
                      comms = 'status')
            str_method      = '%s_process' % d_do['action']
            self.log("method to call: %s(request = d_msg) " % str_method,
                      comms = 'status')
            try:
                # pudb.set_trace()
                method              = getattr(self, str_method)
                d_actionResult      = method(request = d_do)
            except:
                str_msg     = "Class '{}' does not implement method '{}'".format(
                                        self.__class__.__name__,
                                        str_method)
                d_actionResult      = {
                    'status':   False,
                    'msg':      str_msg
                }
                self.log(str_msg, comms = 'error')
            self.log(json.dumps(d_actionResult, indent = 4), comms = 'tx')

        return d_actionResult