#!/usr/bin/env python3

# Single entry point / dispatcher for simplified running of pxpy bin 
# apps

import  argparse
import  os
import  pudb

str_desc = """

 NAME

    docker-entrypoint.py

 SYNOPSIS

    docker-entrypoint.py  [optional cmd args for each sub-module]


 DESCRIPTION

    'docker-entrypoint.py' is the main entrypoint for running pypx
    containerized apps.

"""

def pxfind_do(args, unknown):

    str_otherArgs   = ' '.join(unknown)

    str_CMD = "/usr/local/bin/px-find  %s" % (str_otherArgs)
    return str_CMD


parser  = argparse.ArgumentParser(description = str_desc)

parser.add_argument(
    '--px-find',
    action  = 'store_true',
    dest    = 'b_pxfind',
    default = False,
    help    = 'if specified, indicates running px-find.',
)
parser.add_argument(
    '--px-move',
    action  = 'store_true',
    dest    = 'b_pxmove',
    default = False,
    help    = 'if specified, indicates running px-move.',
)

args, unknown   = parser.parse_known_args()

if __name__ == '__main__':
    if args.b_pxfind:
        try:
            fname   = 'pxfind_do(args, unknown)'
            str_cmd = eval(fname)
            # print(str_cmd)
            os.system(str_cmd)
        except:
            print("Misunderstood container app... exiting.")
