import  subprocess, re, collections, codecs
import  pfmisc
import  pudb
from    pfmisc._colors      import  Colors

# Credit to Anatoly Techtonik
# https://stackoverflow.com/questions/606191/convert-bytes-to-a-string/27527728#27527728
def slashescape(err):
    """ codecs error handler. err is UnicodeDecode instance. return
    a tuple with a replacement for the unencodable part of the input
    and a position where encoding should continue"""
    #print err, dir(err), err.start, err.end, err.object[:err.start]
    thebyte = err.object[err.start:err.end]
    repl = u'\\x'+hex(ord(thebyte))[2:]
    return (repl, err.end)

codecs.register_error('slashescape', slashescape)


class Base():
    """
    A Base class for pypx.
    
    This class is somewhat abstract/virtual in as much as it
    provides a substrate for derived classes and in and of 
    itself does very little.

    """

    def __init__(self,arg):
        """
        Initialize some core self variables common to all derived classes.
        """

        self.arg = arg

        if 'aet' in arg:        self.aet = arg['aet']
        else:                   self.aet = 'CHRIS-ULTRON-AET'

        if 'aec' in arg:        self.aec = arg['aec']
        else:                   self.aec = 'CHRIS-ULTRON-AEC'

        if 'serverIP' in arg:   self.serverIP = arg['serverIP']
        else:                   self.serverIP = '192.168.1.110'

        if 'serverPort' in arg: self.serverPort = arg['serverPort']
        else:                   self.serverPort = '4242'

        self.response = {
            'status': 'error',
            'data': {}
        }

        self.dp = pfmisc.debug(
                    verbosity   = self.arg['verbosity'],
                    within      = 'Base',
                    syslog      = False
        )

    def systemlevel_run(self, opt, d_params):
        """
        Run the system command, based on the passed paramter dictionary
        """
        b_commandGen    = False
        str_cmd         = ''
        d_ret           = {}

        # A function to execute to generate commands
        f_commandGen    = None
        for k,v in d_params.items():
            if k == 'f_commandGen':
                f_commandGen    = v
                b_commandGen    = True 
            else:
                opt[k]  = v

        if b_commandGen:
            str_cmd         = f_commandGen(opt)
            self.dp.qprint("\n%s" % str_cmd, level = 5, type = 'status')
            raw_response    = subprocess.run(
                                str_cmd, 
                                stdout  = subprocess.PIPE, 
                                stderr  = subprocess.STDOUT, 
                                shell   = True
            )
            d_ret   = self.formatResponse(raw_response)

        return d_ret

    def commandSuffix(self):
        # required parameters
        command_suffix =    ' -aec '    + self.aec
        command_suffix +=   ' -aet '    + self.aet
        command_suffix +=   ' '         + self.serverIP
        command_suffix +=   ' '         + self.serverPort

        return command_suffix

    def handle(self, raw_response):
        std = raw_response.stdout.decode('ascii')
        response = {
            'status': 'success',
            'data': '',
            'command': raw_response.args
        }
        if std != '':
            response['status'] = 'error'
            response['data'] = std

        return response

    def checkResponse(self, response):
        std_split = response.split('\n')
        info_count = 0
        error_count = 0
        for line in std_split:
            if line.startswith('I: '):
                info_count += 1
            elif line.startswith('E: '):
                error_count += 1

        status = 'error'
        if error_count == 0:
            status = 'success'

        return status

    def parseResponse(self, response):
        data = []

        uid = 0
        std_split = response.split('\n')

        for line in std_split:
            if line.startswith('I: ---------------------------'):
                data.append({})
                data[-1]['uid'] = {}
                data[-1]['uid']['tag'] = 0
                data[-1]['uid']['value'] = uid
                data[-1]['uid']['label'] = 'uid'
                uid += 1

            elif line.startswith('I: '):
                lineSplit = line.split()
                if len(lineSplit) >= 8 and re.search('\((.*?)\)', lineSplit[1]) != None:
                    # extract DICOM tag
                    tag = re.search('\((.*?)\)', lineSplit[1]).group(0)[1:-1].strip().replace('\x00', '')

                    # extract value
                    value = re.search('\[(.*?)\]', line)
                    if value != None:
                        value = value.group(0)[1:-1].strip().replace('\x00', '')
                    else:
                        value = 'no value provided'

                    # extract label
                    label = lineSplit[-1].strip()

                    data[-1][label] = {}
                    data[-1][label]['tag'] = tag
                    data[-1][label]['value'] = value
                    data[-1][label]['label'] = label

        return data

    def formatResponse(self, raw_response):
        std = raw_response.stdout.decode('utf-8', 'slashescape')
        response = {
            'status':   'success',
            'data':     '',
            'command':  raw_response.args
        }

        status = self.checkResponse(std)

        if status == 'error':
            response['status']  = 'error'
            response['data']    = std
        else:
            response['status']  = 'success'
            response['data']    = self.parseResponse(std)

        return response