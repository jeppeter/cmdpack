# cmdpack
> python package for cmd run

### Release History
* Jul 30th 2021 Release 0.5.2 to add is_running for _CmdRunObject
* May 14th 2021 Release 0.5.0 to make linebuf attribute in CmdObjectAttr to get lines with not return just get
* May 13th 2021 Release 0.4.8 to add get_lines method for CmdObjectAttr to get lines in timeout
* Mar 29th 2017 Release 0.4.6 fixup bug when call shell quote string
* Mar 28th 2017 Release 0.4.4 fixup bug when call \_\_retcode not in the \_\_del\_\_ function and cmds when in shellmode=False list not form to string
* Mar 12th 2017 Release 0.4.2 fixup hang over when call cmdlist
* Mar 11th 2017 Release 0.3.4 to make log when set CMDPACK_LOGLEVEL and CMDPACK_LOGFMT
* Mar 9th 2017 Release 0.3.0 to fixup bug in \_\_del\_\_ function in _CmdRunObject
* Mar 8th 2017 Release 0.2.8 to add kill child process
* Mar 5th 2017 Release 0.2.6 to release the run_cmd_output command with iter mode and make the coding as the input and output
* Mar 4th 2017 Release 0.2.2 to add new function run_cmd_output
* Feb 14th 2017 Release 0.2.0 to fixup bug when call shell mode not in multiple args
* Dec 29th 2016 Release 0.1.8 to make expand the call for run_command_callback and give the long output handle ok




### simple example
```python
import cmdpack
import sys
class cmdobj(object):
    def __init__(self):
        self.__cmds=[]
        return
    def runcmd(self,rl):
        self.__cmds.append(rl)
        return
    def print_out(self):
        for s in self.__cmds:
            print('%s'%(s))
        return

def filter_cmd(rl,ctx):
    ctx.runcmd(rl)
    return

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'cmdout'  :
        for s in sys.argv[2:]:
            print('%s'%(s))
        return
    cmdo = cmdobj()
    cmd = '"%s" "%s" cmdout "hello" "ok"'%(sys.executable,__file__)
    cmdpack.run_command_callback(cmd,filter_cmd,cmdo)
    cmdo.print_out()

if __name__ == '__main__':
    main()
```

> if the command line like this
> python script.py
 
> result is like this
```shell
hello
ok
```

> this package ,just to make the cmdpack as filter out

## run out
```python
import cmdpack
import sys


def test_outline():
    cmds = []
    cmds.append('%s'%(sys.executable))
    cmds.append(__file__)
    cmds.append('cmdout')
    cmds.append('hello')
    cmds.append('world')
    for l in cmdpack.run_cmd_output(cmds):
        print('%s'%(l))
    return

def cmdoutput(args):
    for c in args:
        print('%s'%(c))
    sys.exit(0)
    return

def main():
    if len(sys.argv) >= 2 and sys.argv[1] == 'cmdout':
        cmdoutput(sys.argv[2:])
        return
    test_outline()
    return

if __name__ == '__main__':
    main()
```

> shell output
```shell
hello
world
```


> get lines in some times to return this will get lines in timeout 0.5 and min lines 1

## run out
```python
import cmdpack
import time

def test_outline():
    cmds = []
    cmds.append('%s'%(sys.executable))
    cmds.append(__file__)
    cmds.append('cmdout')
    cmds.append('hello')
    cmds.append('world')
    p = cmdpack.run_cmd_output(cmds)
    while True:
        if p.errended and p.outended:
            break
        rlines = p.get_lines(0.5,2)
        if len(rlines) > 0:
            for l in rlines:
                sys.stdout.write('%s'%(l))
        else:
            sys.stdout.write('get [0] lines\n')

    return

def cmdoutput(args):
    for c in args:
        time.sleep(1.0)
        sys.stdout.write('%s\n'%(c))
        sys.stdout.flush()
    sys.exit(0)
    return

def main():
    if len(sys.argv) >= 2 and sys.argv[1] == 'cmdout':
        cmdoutput(sys.argv[2:])
        return
    test_outline()
    return

if __name__ == '__main__':
    main()
```

> shell output
```shell
get [0] lines
get [0] lines
hello
get [0] lines
world
```


> get lines without linebuf just immediately

## run out
```python
import cmdpack
import time
import sys

def test_outline():
    cmds = []
    cmds.append('%s'%(sys.executable))
    cmds.append(__file__)
    cmds.append('cmdout')
    cmds.append('hello')
    cmds.append('world')
    p = cmdpack.run_cmd_output(cmds,linebuf=False)
    while True:
        if p.errended and p.outended:
            break
        rlines = p.get_lines(0.3,2)
        sys.stdout.write('just get [%d]\n'%(len(rlines)))
        if len(rlines) > 0:
            sys.stdout.write('===========\n')
            for l in rlines:
                sys.stdout.write('%s'%(l))
            sys.stdout.write('\n+++++++++++++++++\n')


    return

def cmdoutput(args):
    for c in args:
        sys.stdout.write('%s'%(c))
        sys.stdout.flush()
        time.sleep(2.0)
    sys.exit(0)
    return

def main():
    if len(sys.argv) >= 2 and sys.argv[1] == 'cmdout':
        cmdoutput(sys.argv[2:])
        return
    test_outline()
    return

if __name__ == '__main__':
    main()
```

> shell output
```shell
just get [2]
===========
he
+++++++++++++++++
just get [2]
===========
ll
+++++++++++++++++
just get [1]
===========
o
+++++++++++++++++
just get [0]
just get [0]
just get [0]
just get [0]
just get [0]
just get [2]
===========
wo
+++++++++++++++++
just get [2]
===========
rl
+++++++++++++++++
just get [1]
===========
d
+++++++++++++++++
just get [0]
just get [0]
just get [0]
just get [0]
just get [0]
just get [0]
```
