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