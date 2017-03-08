#! /bin/bash

_script_file=`python -c "import sys;import os;print('%s'%(os.path.abspath(sys.argv[1])));" "$0"`
script_dir=`dirname $_script_file`
packagename=cmdpack

if [ -z "$PYTHON" ]
	then
	PYTHON=`which python`
	export PYTHON
fi

wait_file_until()
{
	_waitf="$1"
	_maxtime=100
	_checked=0
	if [ $# -gt 1 ]
		then
		_maxtime=$2
	fi
	_cnt=0
	while [ 1 ]
	do
		if [ -f "$_waitf" ]
			then
			if [ $_checked -gt 3 ]
				then
				rm -f "$_waitf"
				break
			fi
			/bin/echo  "import time;time.sleep(0.1)" | $PYTHON
			_checked=`expr $_checked \+ 1`
		else
			_checked=0
			/bin/echo "import time;time.sleep(0.1)" | $PYTHON	
			_cnt=`expr $_cnt \+ 1`
			if [ $_cnt -gt $_maxtime ]
				then
				/bin/echo "can not wait ($_waitf)" >&2
				exit 3
			fi
		fi
	done	
}

rm -f $script_dir/$packagename/__init__.py.touched 
rm -f $script_dir/test/release/release.py.touched

$PYTHON $script_dir/make_setup.py
$PYTHON $script_dir/src/$packagename/__init_debug__.py --release $script_dir/$packagename/__init__.py
wait_file_until "$script_dir/$packagename/__init__.py.touched"

$PYTHON $script_dir/test/release/releasetest.py release
wait_file_until "$script_dir/test/release/release.py.touched"

$PYTHON $script_dir/test/release/release.py test
_res=$?
if [ $_res -ne 0 ]
	then
	/bin/echo "can not run ok"
	exit $_res
fi