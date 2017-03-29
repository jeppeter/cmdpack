# cmdpack
> python package for cmd run

### Release History
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

