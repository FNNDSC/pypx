def init(obj,arg):
    obj.arg = arg

    if 'aet' in arg:
        obj.aet = arg['aet']
    else:
        obj.aet = 'CHRIS-ULTRON-AET'

    if 'aec' in arg:
        obj.aec = arg['aec']
    else:
        obj.aec = 'CHRIS-ULTRON-AEC'

    if 'server_ip' in arg:
        obj.server_ip = arg['server_ip']
    else:
        obj.server_ip = '192.168.1.110'

    if 'server_port' in arg:
        obj.server_port = arg['server_port']
    else:
        obj.server_port = '4241'

    obj.query = ''
    obj.command_suffix = ''
    commandSuffix(obj)

    obj.response = {
        'status': 'error',
        'data': {}
    }

def commandSuffix(obj):
    # required parameters
    obj.command_suffix = ' -aec ' + obj.aec
    obj.command_suffix += ' -aet ' + obj.aet
    obj.command_suffix += ' ' + obj.server_ip
    obj.command_suffix += ' ' + obj.server_port

def sanitize(value):

    # convert to string and remove trailing spaces
    tvalue = str(value).strip()
    # only keep alpha numeric characters and replace the rest by "_"
    svalue = "".join(character if character.isalnum() else '.' for character in tvalue )
    return svalue