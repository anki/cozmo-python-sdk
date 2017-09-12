#!/bin/bash
trap "exit" INT
TODAY=`date +%Y-%m-%d_%H.%M.%S`

python3 -c "import pylint"
if [ "$?" = "1" ]; then
	echo "Aborting pylint pass - pylint not installed"
	exit 1
fi

mkdir -p logs
LOG_FILE="logs/pylint_log_$TODAY.txt"
SCAN_FILE_PATTERN="../../src/cozmo/*.py"

echo "Running Pylint on \"${SCAN_FILE_PATTERN}\"" > ${LOG_FILE}

FILES_TO_SCAN=`ls -1q ${SCAN_FILE_PATTERN} | wc -l | sed -e 's/ //g'`
FILES_SCANNED=0

pylint -j 4 --rcfile pylintrc ${SCAN_FILE_PATTERN} | grep 'W:\|E:\|Module' >> ${LOG_FILE} 2>&1

PROBLEMS_FOUND=`cat ${LOG_FILE} | grep 'W:\|E:' | wc -l | sed -e 's/ //g'`

if ((${PROBLEMS_FOUND} > 0)); then
	echo "Pylint pass found ${PROBLEMS_FOUND} problems, refer to ${LOG_FILE} for more information"
	echo "- found ${PROBLEMS_FOUND} problems" >> ${LOG_FILE}
	exit 1
else
	echo "Pylint pass completed successfully"
	echo "- found no problems" >> ${LOG_FILE}
	exit 0
fi
