#!/usr/bin/python

import os
import sys
import subprocess
import logging
import time
import threading
try:
    import Queue
except ImportError:
    import queue as Queue



import platform
import unittest
import tempfile


def run_cmd_wait(cmd,mustsucc=1,noout=1):
    logging.debug('run (%s)'%(cmd))
    if noout > 0:
        ret = subprocess.call(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
    else:
        ret = subprocess.call(cmd,shell=True)
    if mustsucc and ret != 0:
        raise Exception('run cmd (%s) error'%(cmd))
    return ret

def run_read_cmd(cmd,stdoutfile=subprocess.PIPE,stderrfile=subprocess.PIPE,shellmode=True,copyenv=None):
    #logging.info('run %s stdoutfile %s stderrfile %s shellmode %s copyenv %s'%(cmd,stdoutfile,stderrfile,shellmode,copyenv))
    if copyenv is None:
        copyenv = os.environ.copy()
    p = subprocess.Popen(cmd,stdout=stdoutfile,stderr=stderrfile,shell=shellmode,env=copyenv)
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


def __enqueue_output(out, queue,description,endq):
    for line in iter(out.readline, b''):
        transline = __trans_to_string(line)
        transline = transline.rstrip('\r\n')
        queue.put(transline)
    endq.put('done')
    endq.task_done()
    return

def run_command_callback(cmd,callback,ctx,stdoutfile=subprocess.PIPE,stderrfile=None,shellmode=True,copyenv=None):
    p = run_read_cmd(cmd,stdoutfile,stderrfile,shellmode,copyenv)
    terr = None
    tout = None
    endout = None
    enderr = None
    outended = True
    errended = True
    recvq = None

    if p.stdout is not None:
        if recvq is None:
            recvq = Queue.Queue()
        endout = Queue.Queue()
        tout = threading.Thread(target=__enqueue_output, args=(p.stdout, recvq,'stdout',endout))

    if p.stderr is not None:
        if recvq is None:
            recvq = Queue.Queue()
        enderr = Queue.Queue()
        terr = threading.Thread(target=__enqueue_output,args=(p.stderr,recvq,'stderr',enderr))

    if tout is not None:
        tout.start()
        outended = False

    if terr is not None:
        terr.start()
        errended = False

    exitcode = -1
    while True:
        if errended and outended:
            break
        try:
            rl = recvq.get_nowait()
            if callback is not None:
                callback(rl,ctx)
        except Queue.Empty:
            if not errended:
                try:
                    rl = enderr.get_nowait()
                    if rl == 'done':
                        errended = True
                        enderr.join()
                        enderr = None
                except Queue.Empty:
                    pass
            if not outended :
                try:
                    rl = endout.get_nowait()
                    if rl == 'done':
                        outended = True
                        endout.join()
                        endout = None
                except Queue.Empty:
                    pass
            if not errended or not outended:
                # sleep for a while to get 
                time.sleep(0.1)

    logging.info('over done')
    if terr is not None:
        logging.info('terr wait')
        terr.join()
        terr = None
        logging.info('terr done')
    if tout is not None:
        logging.info('tout wait')
        tout.join()
        tout = None
        logging.info('tout done')
    if recvq is not None:
        assert(recvq.empty())
        # nothing to be done
        recvq = None
        logging.info('recvq done')


    if p is not None:
        while True:
            # wait 
            pret = p.poll()
            if pret is not None:
                exitcode = pret
                logging.info('exitcode %d'%(exitcode))
                break
            # wait for a time
            logging.info('will wait')
            time.sleep(0.1)
        if p.stdout is not None:
            p.stdout.close()
            p.stdout = None
        if p.stderr is not None:
            p.stderr.close()
            p.stderr = None
        p = None
    return exitcode


def a001_callback(rl,self):
    self.callback001(rl)
    return

class debug_cmpack_test_case(unittest.TestCase):
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
        logging.info('__testlines %s'%(self.__testlines))
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

    def test_A005(self):
        cmds = []
        cmds.append(sys.executable)
        cmds.append(__file__)
        cmds.append('cmderr')
        cmds.append('001')
        cmds.append('002')
        cmds.append('003')
        cmds.append('004')
        uname0 = platform.uname()[0].lower()
        devnullfd = None
        try:
            if uname0 == 'windows':
                devnullfd = open('NUL','w')
            elif uname0 == 'linux':
                devnullfd = open('/dev/null','w')
            else:
                raise Exception('can not make err')
            run_command_callback(cmds,a001_callback,self,stdoutfile=subprocess.PIPE,stderrfile=devnullfd,shellmode=False,copyenv=None)
            self.assertEqual(len(self.__testlines),0)
            self.__testlines = []
            run_command_callback(cmds,a001_callback,self,stdoutfile=devnullfd,stderrfile=subprocess.PIPE,shellmode=False,copyenv=None)
            logging.info('__testlines %s'%(self.__testlines))
            self.assertEqual(len(self.__testlines),4)
            self.assertEqual(self.__testlines[0], '001')
            self.assertEqual(self.__testlines[1], '002')
            self.assertEqual(self.__testlines[2], '003')
            self.assertEqual(self.__testlines[3], '004')
        finally:
            if devnullfd is not None:
                devnullfd.close()
            devnullfd = None
        return

    def test_A006(self):
        cmd = []
        cmd.append('%s'%(sys.executable))
        cmd.append('%s'%(__file__))
        cmd.append('cmderr')
        for x in range(1000):
            cmd.append('%d'%(x))
        uname0 = platform.uname()[0].lower()
        devnullfd = None
        try:
            if uname0 == 'windows':
                devnullfd = open('NUL','w')
            elif uname0 == 'linux':
                devnullfd = open('/dev/null','w')
            else:
                raise Exception('can not make err')
            run_command_callback(cmd,a001_callback,self,subprocess.PIPE,devnullfd,False,None)
            self.assertEqual(len(self.__testlines),0)
            self.__testlines = []
            run_command_callback(cmd,a001_callback,self,stdoutfile=devnullfd,stderrfile=subprocess.PIPE,shellmode=False,copyenv=None)
            self.assertEqual(len(self.__testlines),1000)
            for i in range(1000):
                self.assertEqual(self.__testlines[i],'%d'%(i))
        finally:
            if devnullfd is not None:
                devnullfd.close()
            devnullfd = None
        return



def out_print_out(args):
    for a in args:
        print(a)
    return

def err_out(args):
    for a in args:
        sys.stderr.write('%s\n'%(a))
    return

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'cmdout':
        out_print_out(sys.argv[2:])
        return
    elif len(sys.argv) > 1 and sys.argv[1] == 'cmderr':
        err_out(sys.argv[2:])
        return
    if '-v' in sys.argv[1:] or '--verbose' in sys.argv[1:]:
        loglvl = logging.DEBUG
        fmt = "%(levelname)-8s [%(filename)-10s:%(funcName)-20s:%(lineno)-5s] %(message)s"
        logging.basicConfig(level=loglvl,format=fmt)
    unittest.main()

if __name__ == '__main__':
    main()