#!/usr/bin/python

import os
import sys
import subprocess
import logging
import time
import threading
import re
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

def __get_child_pids_win32(pid,recursive=True):
    pids = []
    cmd = 'wmic process where(ParentProcessId=%d) get ProcessId'%(pid)
    logging.info('run (%s)'%(cmd))
    intexpr = re.compile('^([\d]+)\s*$')
    for l in run_cmd_output(cmd):
        logging.info('[%s]'%(l.rstrip('\r\n')))
        l = l.rstrip('\r\n')
        if intexpr.match(l):
            l = l.strip('\t ')
            l = l.rstrip('\t ')
            cpid = int(l)
            logging.info('[%s] cpid %d'%(l,cpid))
            if cpid not in pids:
                pids.append(cpid)
            if recursive:
                cpids = __get_child_pids_win32(cpid,recursive)
                for p in cpids:
                    if p not in pids:
                        pids.append(p)
    return pids


def __get_child_pids_cygwin(pid,recursive=True):
    pids = []
    intexpr = re.compile('([\d]+)')
    for l in run_cmd_output(['ps','-W']):
        l = l.rstrip('\r\n')
        l = l.strip('\t ')
        l = l.rstrip('\t ')
        sarr = re.split('\s+',l)
        if len(sarr) < 2:
            continue
        if not intexpr.match(sarr[0]) or not intexpr.match(sarr[1]):
            continue
        ppid = int(sarr[1])
        if ppid != pid:
            continue
        cpid = int(sarr[0])
        if cpid not in pids:
            pids.append(cpid)
        if recursive:
            cpids = __get_child_pids_cygwin(cpid,recursive)
            for p in cpids:
                if p not in pids:
                    pids.append(p)
    return pids

def __get_child_pids_darwin(pid,recursive=True):
    pids = []
    intexpr = re.compile('([\d]+)')
    for l in run_cmd_output(['ps','-A','-O','ppid']):
        l = l.rstrip('\r\n\t ')
        l = l.strip('\t ')
        sarr = re.split('\s+',l)
        if len(sarr) < 2:
            continue
        if not intexpr.match(sarr[0]) or not intexpr.match(sarr[1]):
            continue
        ppid = int(sarr[1])
        if ppid != pid:
            continue
        cpid = int(sarr[0])
        if cpid not in pids:
            pids.append(cpid)
        if recursive:
            cpids = __get_child_pids_darwin(cpid,recursive)
            for p in cpids:
                if p not in pids:
                    pids.append(p)
    return pids

def __get_child_pids_linux(pid,recursive=True):
    pids = []
    intexpr = re.compile('([\d]+)')
    for l in run_cmd_output(['ps','-e','-O','ppid']):
        l = l.rstrip('\r\n \t')
        l = l.strip('\t ')
        sarr = re.split('\s+',l)
        if len(sarr) < 2:
            continue
        if not intexpr.match(sarr[0]) or not intexpr.match(sarr[1]):
            continue
        ppid = int(sarr[1])
        if ppid != pid:
            continue
        cpid = int(sarr[0])
        if cpid not in pids:
            pids.append(cpid)
        if recursive:
            cpids = __get_child_pids_linux(cpid,recursive)
            for p in cpids:
                if p not in pids:
                    pids.append(p)
    return pids


def get_child_pids(pid,recursive=True):
    osname = sys.platform.lower()
    if osname == 'darwin':
        return __get_child_pids_darwin(pid,recursive)
    elif osname == 'cygwin':
        return __get_child_pids_cygwin(pid,recursive)
    elif osname == 'win32':
        return __get_child_pids_win32(pid,recursive)
    elif osname == 'linux2' or osname == 'linux':
        return __get_child_pids_linux(pid,recursive)
    else:
        raise Exception('not supported platform [%s]'%(osname))

class CmdObjectAttr(object):
    def __init__(self):
        pass

    def __getattr__(self,k,defval=None):
        if k not in self.__dict__.keys():
            return defval
        return self.__dict__[k]

    def __setattr__(self,k,v):
        self.__dict__[k] = v
        return

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
            queue.put(transline)
        endq.put('done')
        endq.task_done()
        return
    def __prepare_out(self):
        if self.__p.stdout is not None:
            if self.recvq is None:
                self.recvq = Queue.Queue()
            assert(self.endout is None)
            self.endout = Queue.Queue()
            assert(self.tout is None)
            self.tout = threading.Thread(target=self.__enqueue_output,args=(self.__p.stdout,self.recvq,'stdout',self.endout))
        return

    def __prepare_err(self):
        if self.__p.stderr is not None:
            if self.recvq is None:
                self.recvq = Queue.Queue()
            assert(self.enderr is None)
            self.enderr = Queue.Queue()
            assert(self.terr is None)
            self.terr = threading.Thread(target=self.__enqueue_output,args=(self.__p.stderr,self.recvq,'stderr',self.enderr))
        return

    def __start_out(self):
        if self.tout is not None:
            self.tout.start()
            self.outended = False
            logging.info('outended False')
        return

    def __start_err(self):
        if self.terr is not None:
            self.terr.start()
            self.errended = False
            logging.info('errended False')
        return

    def __init__(self,cmd,stdoutfile,stderrfile,shellmode,copyenv):
        self.__p = run_read_cmd(cmd,stdoutfile,stderrfile,shellmode,copyenv)
        self.terr = None
        self.tout = None
        self.endout = None
        self.outended = True
        self.errended = True
        self.recvq = None
        self.enderr = None
        self.endout = None
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
                logging.info('outended errended')
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
                            logging.info('errended')
                            self.errended = True
                            self.enderr.join()
                            self.enderr = None
                    except Queue.Empty:
                        pass
                if not self.outended :
                    try:
                        rl = self.endout.get_nowait()
                        if rl == 'done':
                            logging.info('outended')
                            self.outended = True
                            self.endout.join()
                            self.endout = None
                    except Queue.Empty:
                        pass
                if not self.errended or not self.outended:
                    # sleep for a while to get 
                    time.sleep(0.1)
        return

    def __iter__(self):
        if self.__p is not None:
            while True:
                if self.errended and self.outended:
                    break
                try:
                    rl = self.recvq.get_nowait()
                    yield rl
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
            # all is ok ,so remove the resource
            self.__clean_resource()


    def __clean_resource(self):
        self.__wait_out()
        self.__wait_err()
        self.__wait_recvq()
        return self.__get_exitcode()

    def __send_kill(self,pid):
        osname = sys.platform.lower()
        logging.info('send kill [%s]'%(pid))
        if osname == 'win32':
            cmd = 'taskkill /F /PID %d'%(pid)
            logging.info('call [%s]'%(cmd))
            devnullfd=open(os.devnull,'wb')
            subprocess.call(cmd,stdout=devnullfd,stderr=devnullfd,shell=True) 
            devnullfd.close()
            devnullfd = None
        elif osname == 'cygwin' or osname == 'linux' or osname == 'linux2' or osname == 'darwin':
            cmd='kill -9 %d'%(pid)
            devnullfd=open(os.devnull,'wb')
            subprocess.call(cmd,stdout=devnullfd,stderr=devnullfd,shell=True)
            devnullfd.close()
            devnullfd = None
        else:
            raise Exception('unsupported osname [%s]'%(osname))
        return

    def __kill_proc_childs(self,pid):
        cpids = get_child_pids(pid)
        self.__send_kill(pid)
        for p in cpids:            
            self.__send_kill(p)
        return

    def __kill_proc(self,attr=None):
        maxwtime = None
        if attr is not None:
            maxwtime = attr.maxwtime
        exitcode = self.__exitcode
        stime = time.time()
        if self.__p is not None:
            while True:
                if self.errended and self.outended:
                    break
                try:
                    rl = self.recvq.get_nowait()
                    logging.info('rl (%s)'%(rl.rstrip('\r\n')))
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
                        if maxwtime is not None:
                            ctime = time.time()
                            if (ctime - stime) > maxwtime:
                                logging.info('[%s] kill[%s]'%(ctime,self.__p.pid))
                                self.__kill_proc_childs(self.__p.pid)
                        time.sleep(0.1)
        self.__exitcode = exitcode
        return exitcode



    def get_exitcode(self,attr=None):
        self.__kill_proc(attr)
        return self.__clean_resource()

    def __del__(self):
        self.__clean_resource()
        return

def run_command_callback(cmd,callback,ctx,stdoutfile=subprocess.PIPE,stderrfile=None,shellmode=True,copyenv=None):
    cmdobj = _CmdRunObject(cmd,stdoutfile,stderrfile,shellmode,copyenv)
    cmdobj.call_readback(callback,ctx)
    return cmdobj.get_exitcode()


def run_cmd_output(cmd,stdout=True,stderr=False,shellmode=True,copyenv=None):
    stdouttype = type(stdout)
    if isinstance(stdout,bool):
        if stdout:
            stdoutfile=subprocess.PIPE
        else:
            stdoutfile=open(os.devnull,'wb')
    elif isinstance(stdout,str) or (sys.version[0] == '2' and isinstance(stdout,unicode)) :
        stdoutfile=open(stdout,'wb')
    else:
        stdoutfile=stdout

    if isinstance(stderr,bool):
        if stderr:
            stderrfile=subprocess.PIPE
        else:
            stderrfile=open(os.devnull,'wb')
    elif isinstance(stderr,str) or (sys.version[0] == '2' and isinstance(stderr,unicode)):
        stderrfile=open(stderr,'wb')
    else:
        stderrfile=stderr
    return _CmdRunObject(cmd,stdoutfile,stderrfile,shellmode,copyenv)



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

def out_time(args):
    for c in args:
        sys.stdout.write('%s\n'%(c))
        sys.stdout.flush()
        time.sleep(1.0)
    return

def err_time(args):
    for c in args:
        sys.stderr.write('%s\n'%(c))
        sys.stderr.flush()
        time.sleep(1.0)
    return


##handleoutend


class debug_cmdpack_case(unittest.TestCase):
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
        self.assertEqual(self.__testlines[0].rstrip('\r\n'),'001')
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
        self.assertEqual(self.__testlines[0].rstrip('\r\n'), '001')
        self.assertEqual(self.__testlines[1].rstrip('\r\n'), '002')
        self.assertEqual(self.__testlines[2].rstrip('\r\n'), '003')
        self.assertEqual(self.__testlines[3].rstrip('\r\n'), '004')
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
            self.assertEqual(self.__testlines[0].rstrip('\r\n'), '001')
            self.assertEqual(self.__testlines[1].rstrip('\r\n'), '002')
            self.assertEqual(self.__testlines[2].rstrip('\r\n'), '003')
            self.assertEqual(self.__testlines[3].rstrip('\r\n'), '004')
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
                self.assertEqual(self.__testlines[i].rstrip('\r\n'),'%d'%(i))
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
        self.assertEqual(self.__testlines[0].rstrip('\r\n'),'cc bb')
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
                self.assertEqual(l.rstrip('\r\n'),'cc bb')
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
                self.assertEqual(l.rstrip('\r\n'),'001')
            elif idx == 1:
                self.assertEqual(l.rstrip('\r\n'),'002')
            elif idx == 2:
                self.assertEqual(l.rstrip('\r\n'),'003')
            elif idx == 3:
                self.assertEqual(l.rstrip('\r\n'),'004')
            idx +=1
        self.assertEqual(idx,4)
        return

    def __self_time_assert(self,lasttime,mosttime):
        ctime = time.time()
        self.assertTrue( (ctime - lasttime) < mosttime)
        return ctime

    def test_A010(self):
        cmds = []
        cmds.append(sys.executable)
        cmds.append(__file__)
        cmds.append('outtime')
        cmds.append('001')
        cmds.append('002')
        cmds.append('003')
        cmds.append('004')
        idx = 0
        stime = time.time()
        for l in run_cmd_output(cmds,True,False):
            if idx == 0:
                self.assertEqual(l.rstrip('\r\n'),'001')
                # make sure time is at most 2 second
                stime = self.__self_time_assert(stime,2.0)
            elif idx == 1:
                self.assertEqual(l.rstrip('\r\n'),'002')
                # make sure time is at most 2 second
                stime = self.__self_time_assert(stime,2.0)
            elif idx == 2:
                self.assertEqual(l.rstrip('\r\n'),'003')
                # make sure time is at most 2 second
                stime = self.__self_time_assert(stime,2.0)
            elif idx == 3:
                self.assertEqual(l.rstrip('\r\n'),'004')
                # make sure time is at most 2 second
                stime = self.__self_time_assert(stime,2.0)
            idx +=1
        self.assertEqual(idx,4)

        cmds = []
        cmds.append(sys.executable)
        cmds.append(__file__)
        cmds.append('errtime')
        cmds.append('001')
        cmds.append('002')
        cmds.append('003')
        cmds.append('004')
        idx = 0
        stime = time.time()
        for l in run_cmd_output(cmds,False,True):
            if idx == 0:
                self.assertEqual(l.rstrip('\r\n'),'001')
                # make sure time is at most 2 second
                stime = self.__self_time_assert(stime,2.0)
            elif idx == 1:
                self.assertEqual(l.rstrip('\r\n'),'002')
                # make sure time is at most 2 second
                stime = self.__self_time_assert(stime,2.0)
            elif idx == 2:
                self.assertEqual(l.rstrip('\r\n'),'003')
                # make sure time is at most 2 second
                stime = self.__self_time_assert(stime,2.0)
            elif idx == 3:
                self.assertEqual(l.rstrip('\r\n'),'004')
                # make sure time is at most 2 second
                stime = self.__self_time_assert(stime,2.0)
            idx +=1
        self.assertEqual(idx,4)
        return

    def test_A011(self):
        for i in range(100):
            cmds=[]
            cmds.append('%s'%(sys.executable))
            cmds.append(__file__)
            cmds.append('cmdout')
            cmds.append('gg')
            cmds.append('bb')
            idx=0
            tempf = make_tempfile()
            for l in run_cmd_output(cmds,tempf):
                idx += 1
            self.assertEqual(idx,0)
            os.remove(tempf)
            fd,f=tempfile.mkstemp()
            # we make sure this would be no more run fd
            if 'TEST_VERBOSE' in os.environ.keys():
                logging.info('fd %s'%(fd))
            elif (i % 20) == 0:
                sys.stderr.write('.')
                sys.stderr.flush()
            self.assertTrue( fd < 10)
            os.close(fd)
            os.remove(f)
        for i in range(100):
            cmds=[]
            cmds.append('%s'%(sys.executable))
            cmds.append(__file__)
            cmds.append('cmderr')
            cmds.append('gg')
            cmds.append('bb')
            idx=0
            tempf = make_tempfile()
            for l in run_cmd_output(cmds,False,tempf):
                idx += 1
            self.assertEqual(idx,0)
            idx= 0
            with open(tempf,'rb') as fin:
                for l in fin:
                    l = l.rstrip('\r\n')
                    if idx == 0:
                        self.assertEqual(l.rstrip('\r\n'),'gg')
                    elif idx == 1:
                        self.assertEqual(l.rstrip('\r\n'),'bb')
                    idx += 1
            self.assertEqual(idx,2)
            os.remove(tempf)
            fd,f=tempfile.mkstemp()
            # we make sure this would be no more run fd
            if 'TEST_VERBOSE' in os.environ.keys():
                logging.info('fd %s'%(fd))
            elif (i % 20) == 0:
                sys.stderr.write('.')
                sys.stderr.flush()
            self.assertTrue( fd < 10)
            os.close(fd)
            os.remove(f)
        return

    def test_A012(self):
        cmds = []
        cmds.append('%s'%(sys.executable))
        cmds.append(__file__)
        cmds.append('outtime')
        cmds.extend(['cc','bb','dd','ee','ff'])
        p = run_cmd_output(cmds)
        idx = 0
        stime = time.time()
        for l in p:
            if idx == 0:
                self.assertEqual(l.rstrip('\r\n'),'cc')
            else:
                break
            idx += 1
        attr = CmdObjectAttr()
        attr.maxwtime = 1.0
        exitcode = p.get_exitcode(attr)
        ctime = time.time()
        self.assertTrue( (ctime - stime) < 3.0)
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
    elif len(sys.argv) > 1 and sys.argv[1] == 'outtime':
        out_time(sys.argv[2:])
        return
    elif len(sys.argv) > 1 and sys.argv[1] == 'errtime':
        err_time(sys.argv[2:])
        return

    if '--release' in sys.argv[1:]:
        debug_release()
        return
    if '-v' in sys.argv[1:] or '--verbose' in sys.argv[1:]:
        loglvl = logging.DEBUG
        fmt = "%(levelname)-8s [%(filename)-10s:%(funcName)-20s:%(lineno)-5s] %(message)s"
        os.environ['TEST_VERBOSE'] = '1'
        logging.basicConfig(level=loglvl,format=fmt)
    elif 'TEST_VERBOSE' in os.environ.keys():
        del os.environ['TEST_VERBOSE']
    unittest.main()

if __name__ == '__main__':
    main()
##importdebugend