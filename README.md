# cmdpack
> python package for cmd run

### Release History
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

