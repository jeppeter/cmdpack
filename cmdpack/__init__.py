#!/usr/bin/python

import os
import sys
import subprocess
import logging
import unittest
import tempfile
import time

def run_cmd_wait(cmd,mustsucc=1,noout=1):
    logging.debug('run (%s)'%(cmd))
    if noout > 0:
        ret = subprocess.call(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
    else:
        ret = subprocess.call(cmd,shell=True)
    if mustsucc and ret != 0:
        raise Exception('run cmd (%s) error'%(cmd))
    return ret

def run_read_cmd(cmd):
    #logging.debug('run (%s)'%(cmd))
    p = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
    return p

def __trans_to_string(s):
    if sys.version[0] == '3':
        encodetype = ['UTF-8','latin-1']
        idx=0
        while idx < len(encodetype):
            try:
                return s.decode(encoding=encodetype[idx])
            except:
                idx += 1
        raise Exception('not valid bytes (%s)'%(repr(s)))
    return s

def read_line(pin,ch='\r'):
    s = ''
    retbyte = '\n'
    chbyte = ch
    if sys.version[0] == '3':
        retbyte = '\n'.encode(encoding='UTF-8')
        chbyte = ch.encode(encoding='UTF-8')
        s = bytes()
    while True:
        b = pin.read(1)
        if b is None or len(b) == 0:
            if len(s) == 0:
                return None
            return __trans_to_string(s)
        if b != chbyte and b != retbyte:
            if sys.version[0] == '3':
                # it is python3
                s += b
            else:
                s += b
            continue

        return __trans_to_string(s)
    return __trans_to_string(s)


def run_command_callback(cmd,callback,ctx):
    p = run_read_cmd(cmd)
    exited = 0
    exitcode = -1
    while exited == 0:
        pret = p.poll()
        #logging.debug('pret %s'%(repr(pret)))
        if pret is not None:
            exitcode = pret
            exited = 1
            #logging.debug('exitcode (%d)'%(exitcode))
            while True:
                rl = read_line(p.stdout)
                #logging.debug('read (%s)'%(rl))
                if rl is None:
                    break
                if callback is not None:
                    callback(rl,ctx)
            break
        else:
            rl = read_line(p.stdout)
            #logging.debug('read (%s)'%(rl))
            if rl :
                if callback is not None:
                    callback(rl,ctx)
    return exitcode


def a001_callback(rl,self):
    self.callback001(rl)
    return

class CmdpackTestCase(unittest.TestCase):
    def setUp(self):
        self.__testlines = []
        return

    def tearDown(self):
        pass


    def callback001(self,rl):
        self.__testlines.append(rl)
        return

    def test_A001(self):
        cmd = '"%s" "%s" "cmdout" "001" '%(sys.executable,__file__)
        run_command_callback(cmd,a001_callback,self)
        self.assertEqual(len(self.__testlines),1)
        self.assertEqual(self.__testlines[0],'001')
        return

    def test_A002(self):
        cmd = '"%s" "%s" "cmdout" "002"'%(sys.executable,__file__)
        run_cmd_wait(cmd)
        return

    def test_A003(self):
        tmpfile = None
        try:
            fd,tmpfile = tempfile.mkstemp(suffix='.py',prefix='cmd',dir=None,text=True)  
            logging.info('tmpfile %s'%(tmpfile))      
            os.close(fd)
            with open(tmpfile,'w+') as f:
                f.write('wrong cmd')

            cmd = '"%s" "%s"'%(sys.executable,tmpfile)
            ok = 0
            try:
                run_cmd_wait(cmd)
            except Exception as e:
                ok = 1
            self.assertEqual(ok,1)
        finally:
            tmpfile = None
        return

    def test_A004(self):
        cmd = '"%s" "%s" "cmdout" "001" "002" "003" "004"'%(sys.executable,__file__)
        run_command_callback(cmd,a001_callback,self)
        self.assertEqual(len(self.__testlines),4)
        self.assertEqual(self.__testlines[0], '001')
        self.assertEqual(self.__testlines[1], '002')
        self.assertEqual(self.__testlines[2], '003')
        self.assertEqual(self.__testlines[3], '004')
        return


def out_print_out(args):
    for a in args:
        print(a)
    return

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'cmdout':
        out_print_out(sys.argv[2:])
        return
    if '-v' in sys.argv[1:] or '--verbose' in sys.argv[1:]:
        loglvl = logging.DEBUG
        fmt = "%(levelname)-8s [%(filename)-10s:%(funcName)-20s:%(lineno)-5s] %(message)s"
        logging.basicConfig(level=loglvl,format=fmt)
    unittest.main()

if __name__ == '__main__':
    main()