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

__version__ = "VERSIONNUMBER"
__version_info__ = "VERSIONINFO"




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
    cmds = cmd
    if isinstance(cmd,list):
        cmds = ''
        i = 0
        for c in cmd:
            if i > 0 :
                cmds += ' '
            cmds += '"%s"'%(c)
            i += 1
    p = subprocess.Popen(cmds,stdout=stdoutfile,stderr=stderrfile,shell=shellmode,env=copyenv)
    return p



class _CmdRunObject(object):
    def __trans_to_string(self,s):
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
    def __enqueue_output(self,out, queue,description,endq):
        for line in iter(out.readline, b''):
            transline = self.__trans_to_string(line)
            transline = transline.rstrip('\r\n')
            queue.put(transline)
        endq.put('done')
        endq.task_done()
        return

    def __prepare_out(self):
        if self.__p is not None:
            if self.recvq is None:
                self.recvq = Queue.Queue()
            self.endout = Queue.Queue()
            self.tout = threading.Thread(target=self.__enqueue_output,args=(self.__p.stdout,self.recvq,'stdout',self.endout))
        return

    def __prepare_err(self):
        if self.__p.stderr is not None:
            if self.recvq is None:
                self.recvq = Queue.Queue()
            self.enderr = Queue.Queue()
            self.terr = threading.Thread(target=self.__enqueue_output,args=(self.__p.stderr,self.recvq,'stderr',self.enderr))
        return

    def __start_out(self):
        if self.tout is not None:
            self.tout.start()
            self.outended = False
        return

    def __start_err(self):
        if self.terr is not None:
            self.terr.start()
            self.errended = False
        return

    def __init__(self,cmd,stdoutfile,stderrfile,shellmode,copyenv):
        self.__p = run_read_cmd(cmd,stdoutfile,stderrfile,shellmode,copyenv)
        self.terr = None
        self.tout = None
        self.endout = None
        self.outended = True
        self.errended = True
        self.recvq = None
        self.__prepare_out()
        self.__prepare_err()
        self.__start_out()
        self.__start_err()
        self.__exitcode = 0
        return

    def __wait_err(self):
        if self.terr is not None:
            self.terr.join()
            self.terr = None
        return

    def __wait_out(self):
        if self.tout is not None:
            self.tout.join()
            self.tout = None

    def __wait_recvq(self):
        if self.recvq is not None:
            assert(self.recvq.empty())
            # nothing to be done
            self.recvq = None
        return

    def __get_exitcode(self):
        exitcode = self.__exitcode
        if self.__p is not None:
            while True:
                # wait 
                pret = self.__p.poll()
                if pret is not None:
                    exitcode = pret
                    logging.info('exitcode %d'%(exitcode))
                    break
                # wait for a time
                logging.info('will wait')
                time.sleep(0.1)
            if self.__p.stdout is not None:
                self.__p.stdout.close()
                self.__p.stdout = None
            if self.__p.stderr is not None:
                self.__p.stderr.close()
                self.__p.stderr = None
            self.__p = None
        self.__exitcode = exitcode
        return exitcode

    def call_readback(self,callback,ctx):
        if self.__p is None:
            return
        while True:
            if self.errended and self.outended:
                break
            try:
                rl = self.recvq.get_nowait()
                if callback is not None:
                    callback(rl,ctx)
            except Queue.Empty:
                if not self.errended:
                    try:
                        rl = self.enderr.get_nowait()
                        if rl == 'done':
                            self.errended = True
                            self.enderr.join()
                            self.enderr = None
                    except Queue.Empty:
                        pass
                if not self.outended :
                    try:
                        rl = self.endout.get_nowait()
                        if rl == 'done':
                            self.outended = True
                            self.endout.join()
                            self.endout = None
                    except Queue.Empty:
                        pass
                if not self.errended or not self.outended:
                    # sleep for a while to get 
                    time.sleep(0.1)
        return

    def __clean_resource(self):
        self.__wait_out()
        self.__wait_err()
        self.__wait_recvq()
        return self.__get_exitcode()

    def get_exitcode(self):
        return self.__clean_resource()

    def __del__(self):
        self.__clean_resource()
        return

def run_command_callback(cmd,callback,ctx,stdoutfile=subprocess.PIPE,stderrfile=None,shellmode=True,copyenv=None):
    cmdobj = _CmdRunObject(cmd,stdoutfile,stderrfile,shellmode,copyenv)
    cmdobj.call_readback(callback,ctx)
    return cmdobj.get_exitcode()

class _StoreLines(object):
    def __init__(self):
        self.__lines = []
        return

    def store_line(self,rl):
        self.__lines.append(rl)
        return

    def get_outs(self):
        return self.__lines

def _call_out_Storeline(rl,ctx):
    ctx.store_line(rl)
    return

def run_cmd_output(cmd,stdout=True,stderr=False,shellmode=True,copyenv=None):
    if stdout:
        stdoutfile=subprocess.PIPE
    else:
        stdoutfile=open(os.devnull,'wb')

    if stderr:
        stderrfile=subprocess.PIPE
    else:
        stderrfile=open(os.devnull,'wb')
    store = _StoreLines()
    run_command_callback(cmd,_call_out_Storeline,store,stdoutfile,stderrfile,shellmode,copyenv)
    return store.get_outs()



##importdebugstart
import unittest
import tempfile



##handleoutstart

def a001_callback(rl,self):
    self.callback001(rl)
    return

def make_dir_safe(dname=None):
    if dname is not None:
        if not os.path.isdir(dname):
            try:
                os.makedirs(dname)
            except:
                pass
            if not os.path.isdir(dname):
                raise Exception('can not make [%s]'%(dname))

def make_tempdir(prefix=None):
    make_dir_safe(prefix)
    return tempfile.mkdtemp(dir=prefix)

def make_tempfile(prefix=None):
    make_dir_safe(prefix)
    fd,result = tempfile.mkstemp(dir=prefix)
    os.close(fd)
    return result


def out_print_out(args):
    for a in args:
        print(a)
    return

def err_out(args):
    for a in args:
        sys.stderr.write('%s\n'%(a))
    return

def echo_out(args):
    i = 0 
    for c in args:
        if i > 0 :
            sys.stdout.write(' ')
        sys.stdout.write('%s'%(c))
        i += 1
    sys.stdout.write('\n')
    return

##handleoutend


class debug_cmpack_test_case(unittest.TestCase):
    def setUp(self):
        self.__testlines = []
        return

    def tearDown(self):
        pass


    def write_tempfile(self,s):
        tempf = make_tempfile()
        with open(tempf,'wb') as fout:
            fout.write('%s'%(s))
        return tempf


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
        devnullfd = None
        try:
            devnullfd= open(os.devnull,'w')
            run_command_callback(cmds,a001_callback,self,stdoutfile=subprocess.PIPE,stderrfile=devnullfd,shellmode=True,copyenv=None)
            self.assertEqual(len(self.__testlines),0)
            self.__testlines = []
            run_command_callback(cmds,a001_callback,self,stdoutfile=devnullfd,stderrfile=subprocess.PIPE,shellmode=True,copyenv=None)
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
        devnullfd = None
        try:
            devnullfd = open(os.devnull,'w')
            run_command_callback(cmd,a001_callback,self,subprocess.PIPE,devnullfd,True,None)
            self.assertEqual(len(self.__testlines),0)
            self.__testlines = []
            run_command_callback(cmd,a001_callback,self,stdoutfile=devnullfd,stderrfile=subprocess.PIPE,shellmode=True,copyenv=None)
            self.assertEqual(len(self.__testlines),1000)
            for i in range(1000):
                self.assertEqual(self.__testlines[i],'%d'%(i))
        finally:
            if devnullfd is not None:
                devnullfd.close()
            devnullfd = None
        return


    def test_A007(self):
        cmd = []
        cmd.append('%s'%(sys.executable))
        cmd.append('%s'%(__file__))
        cmd.append('echoout')
        cmd.append('cc')
        cmd.append('bb')
        retcode = run_command_callback(cmd,a001_callback,self,stdoutfile=subprocess.PIPE,stderrfile=None,shellmode=True,copyenv=None)
        self.assertEqual(len(self.__testlines),1)
        self.assertEqual(self.__testlines[0],'cc bb')
        return

    def test_A008(self):
        cmd = []
        cmd.append('%s'%(sys.executable))
        cmd.append('%s'%(__file__))
        cmd.append('echoout')
        cmd.append('cc')
        cmd.append('bb')
        idx= 0
        for l in run_cmd_output(cmd):
            if idx == 0:
                self.assertEqual(l,'cc bb')
            idx += 1
        self.assertEqual(idx,1)
        return

    def test_A009(self):
        cmds = []
        cmds.append(sys.executable)
        cmds.append(__file__)
        cmds.append('cmderr')
        cmds.append('001')
        cmds.append('002')
        cmds.append('003')
        cmds.append('004')
        idx = 0
        for l in run_cmd_output(cmds,False,True):
            if idx == 0:
                self.assertEqual(l,'001')
            elif idx == 1:
                self.assertEqual(l,'002')
            elif idx == 2:
                self.assertEqual(l,'003')
            elif idx == 3:
                self.assertEqual(l,'004')
            idx +=1
        self.assertEqual(idx,4)
        return




sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..')))
import rtools
import re

def debug_release():
    if '-v' in sys.argv[1:]:
        #sys.stderr.write('will make verbose\n')
        loglvl =  logging.DEBUG
        logging.basicConfig(level=loglvl,format='%(asctime)s:%(filename)s:%(funcName)s:%(lineno)d\t%(message)s')
    topdir = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..'))
    tofile= os.path.abspath(os.path.join(topdir,'cmdpack','__init__.py'))
    if len(sys.argv) > 2:
        for k in sys.argv[1:]:
            if not k.startswith('-'):
                tofile = k
                break
    versionfile = os.path.abspath(os.path.join(topdir,'VERSION'))
    if not os.path.exists(versionfile):
        raise Exception('can not find VERSION file')
    with open(versionfile,'r') as f:
        for l in f:
            l = l.rstrip('\r\n')
            vernum = l
            break
    sarr = re.split('\.',vernum)
    if len(sarr) != 3:
        raise Exception('version (%s) not format x.x.x'%(vernum))
    VERSIONNUMBER = vernum
    VERSIONINFO='( %s, %s, %s)'%(sarr[0],sarr[1],sarr[2])
    repls = dict()
    repls[r'VERSIONNUMBER'] = VERSIONNUMBER
    repls[r'"VERSIONINFO"'] = VERSIONINFO
    logging.info('repls %s tofile (%s)'%(repls.keys(),tofile))
    rtools.release_file('__main__',tofile,[r'^debug_*'],[[r'##importdebugstart.*',r'##importdebugend.*']],[],repls)
    return


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'cmdout':
        out_print_out(sys.argv[2:])
        return
    elif len(sys.argv) > 1 and sys.argv[1] == 'cmderr':
        err_out(sys.argv[2:])
        return
    elif len(sys.argv) > 1 and sys.argv[1] == 'echoout':
        echo_out(sys.argv[2:])
        return

    if '--release' in sys.argv[1:]:
        debug_release()
        return
    if '-v' in sys.argv[1:] or '--verbose' in sys.argv[1:]:
        loglvl = logging.DEBUG
        fmt = "%(levelname)-8s [%(filename)-10s:%(funcName)-20s:%(lineno)-5s] %(message)s"
        logging.basicConfig(level=loglvl,format=fmt)
    unittest.main()

if __name__ == '__main__':
    main()
##importdebugend