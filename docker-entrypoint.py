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
def pxdispatch_do(str_appName, args, unknown):
    str_otherArgs   = ' '.join(unknown)

    str_CMD = "/usr/local/bin/%s %s" % (str_appName, str_otherArgs)
    return str_CMD

parser  = argparse.ArgumentParser(description = str_desc)

parser.add_argument(
    '--px-do',
    action  = 'store_true',
    dest    = 'b_pxdo',
    default = False,
    help    = 'if specified, indicates running px-do.',
)
parser.add_argument(
    '--px-echo',
    action  = 'store_true',
    dest    = 'b_pxecho',
    default = False,
    help    = 'if specified, indicates running px-echo.',
)
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
parser.add_argument(
    '--px-register',
    action  = 'store_true',
    dest    = 'b_pxregister',
    default = False,
    help    = 'if specified, indicates running px-register.',
)
parser.add_argument(
    '--px-repack',
    action  = 'store_true',
    dest    = 'b_pxrepack',
    default = False,
    help    = 'if specified, indicates running px-repack.',
)
parser.add_argument(
    '--px-report',
    action  = 'store_true',
    dest    = 'b_pxreport',
    default = False,
    help    = 'if specified, indicates running px-report.',
)
parser.add_argument(
    '--px-status',
    action  = 'store_true',
    dest    = 'b_pxstatus',
    default = False,
    help    = 'if specified, indicates running px-status.',
)
parser.add_argument(
    '--pfstorage',
    action  = 'store_true',
    dest    = 'b_pfstorage',
    default = False,
    help    = 'if specified, indicates running pfstorage.',
)

args, unknown   = parser.parse_known_args()

if __name__ == '__main__':
    fname   = 'pxdispatch_do("px-find",args, unknown)'

    os.system("/dock/storescp.sh -p 11113 &")
    if args.b_pxdo:         fname   = 'pxdispatch_do("px-do", args, unknown)'
    if args.b_pxecho:       fname   = 'pxdispatch_do("px-echo",args, unknown)'
    if args.b_pxfind:       fname   = 'pxdispatch_do("px-find",args, unknown)'
    if args.b_pxmove:       fname   = 'pxdispatch_do("px-move",args, unknown)'
    if args.b_pxregister:   fname   = 'pxdispatch_do("px-register",args, unknown)'
    if args.b_pxrepack:     fname   = 'pxdispatch_do("px-repack",args, unknown)'
    if args.b_pxreport:     fname   = 'pxdispatch_do("px-report",args, unknown)'
    if args.b_pxstatus:     fname   = 'pxdispatch_do("px-status",args, unknown)'
    if args.b_pfstorage:    fname   = 'pxdispatch_do("pfstorage",args, unknown)'

    try:
        str_cmd = eval(fname)
        # print(str_cmd)
        os.system(str_cmd)
    except:
        print("Misunderstood container app... exiting.")

