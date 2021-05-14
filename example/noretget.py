#! /usr/bin/python

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


_reload_cmdpack_path(os.path.abspath(os.path.join(os.path.dirname(__file__),'..')))
import cmdpack
import time

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