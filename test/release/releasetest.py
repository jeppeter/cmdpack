#! /usr/bin/env python

import os
import sys

def _release_path_test(curpath,*paths):
    testfile = os.path.join(curpath,*paths)
    if os.path.exists(testfile):
        if curpath != sys.path[0]:
            if curpath in sys.path:
                sys.path.remove(curpath)
            oldpath=sys.path
            sys.path = [curpath]
            sys.path.extend(oldpath)
    return

def _reload_cmdpack_path(curpath):
	return _release_path_test(curpath,'cmdpack','__init__.py')

def _reload_cmdpack_debug_path(curpath):
	return _release_path_test(curpath,'__init_debug__.py')


def _reload_rtools_path(curpath):
	return _release_path_test(curpath,'rtools.py')

topdir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)),'..','..'))
_reload_cmdpack_path(topdir)
_reload_rtools_path(topdir)

import extargsparse
import logging
import unittest
import re
import importlib
import rtools
import tempfile
import subprocess
import platform
import random
import time
from cmdpack import run_cmd_wait,run_read_cmd,run_command_callback,run_cmd_output
from cmdpack import __version__ as cmdpack_version
from cmdpack import __version_info__ as cmdpack_version_info


test_placer_holder=True

class debug_version_test(unittest.TestCase):
    def setUp(self):
        return

    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass


    def test_A001(self):
    	verfile = os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','VERSION')
    	vernum = '0.0.1'
    	with open(verfile,'r') as f:
    		for l in f:
    			l = l.rstrip('\r\n')
    			vernum = l
    	self.assertEqual(vernum , cmdpack_version)
    	sarr = re.split('\.',vernum)
    	self.assertEqual(len(sarr),3)
    	i = 0
    	while i < len(sarr):
    		sarr[i] = int(sarr[i])
    		self.assertEqual(cmdpack_version_info[i],sarr[i])
    		i += 1
    	return




def set_log_level(args):
    loglvl= logging.ERROR
    if args.verbose >= 3:
        loglvl = logging.DEBUG
    elif args.verbose >= 2:
        loglvl = logging.INFO
    elif args.verbose >= 1 :
        loglvl = logging.WARN
    # we delete old handlers ,and set new handler
    logging.basicConfig(level=loglvl,format='%(asctime)s:%(filename)s:%(funcName)s:%(lineno)d\t%(message)s')
    return


def release_handler(args,parser):
	set_log_level(args)
	global topdir
	_reload_cmdpack_debug_path(os.path.join(topdir,'src','cmdpack'))
	mod = importlib.import_module('__init_debug__')
	includes = args.release_importnames
	macros = []
	i = 0
	while i < len(args.release_macros):
		curmacros = []
		curmacros.append(args.release_macros[i])
		curmacros.append(args.release_macros[i+1])
		macros.append(curmacros)
		i += 2
	logging.info('args %s includes %s macros %s'%(repr(args),includes,macros))
	repls = dict()

	logging.info('includes %s repls %s'%(includes,repr(repls)))
	s = rtools.release_get_catch(mod,includes,macros,repls)
	outs = slash_string(s)
	releaserepls = dict()
	releasekey = 'test_placer_holder'
	releasekey += '='
	releasekey += "True"
	releaserepls[releasekey] = outs
	logging.info('releaserepls %s'%(repr(releaserepls)))
	rtools.release_file(None,args.release_output,[],[],[],releaserepls)
	sys.exit(0)
	return

def test_handler(args,parser):
	set_log_level(args)
	testargs = []
	testargs.extend(args.subnargs)
	sys.argv[1:] = testargs
	unittest.main(verbosity=args.verbose,failfast=args.failfast)
	sys.exit(0)
	return

def slash_string(s):
	outs =''
	for c in s:
		if c == '\\':
			outs += '\\\\'
		else:
			outs += c
	return outs

def cmdout_handler(args,parser):
	out_print_out(args.subnargs)
	sys.exit(0)
	return

def cmderr_handler(args,parser):
	err_out(args.subnargs)
	sys.exit(0)
	return

def echoout_handler(args,parser):
	echo_out(args.subnargs)
	sys.exit(0)
	return

def outtime_handler(args,parser):
	out_time(args.subnargs)
	sys.exit(0)
	return



def errtime_handler(args,parser):
	err_time(args.subnargs)
	sys.exit(0)
	return


def main():
	outputfile_orig = os.path.join(os.path.dirname(os.path.abspath(__file__)),'release.py')
	outputfile = slash_string(outputfile_orig)
	commandline_fmt = '''
		{
			"verbose|v" : "+",
			"failfast|f" : true,
			"release<release_handler>##release file##" : {
				"output|O" : "%s",
				"importnames|I" : ["debug_cmpack_case"],
				"macros|M" : ["##handleoutstart","##handleoutend"]
			},
			"test<test_handler>##test mode##" : {
				"$" : "*"
			},
			"cmdout<cmdout_handler>" : {
				"$" : "*"
			},
			"cmderr<cmderr_handler>" : {
				"$" : "*"
			},
			"echoout<echoout_handler>" : {
				"$" : "*"
			},
			"outtime<outtime_handler>" : {
				"$" : "*"
			},
			"errtime<errtime_handler>" : {
				"$" : "*"
			}
		}
	'''
	commandline = commandline_fmt%(outputfile)
	options = extargsparse.ExtArgsOptions()
	parser = extargsparse.ExtArgsParse(options)
	parser.load_command_line_string(commandline)
	args = parser.parse_command_line()
	return

if __name__ == '__main__':
	main()
