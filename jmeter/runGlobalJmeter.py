#!/usr/bin/env python3
'''Loads configuration from test_plan.json and executes the Jmeter script'''
import argparse
import datetime
import glob
import logging
import math
import os
import shutil
import subprocess
import sys
import json
import ncscli.batchRunner as batchRunner
from localizedJmeterProcessor import LocalJMeterFrameProcessor as JMeterFrameProcessor

logger = logging.getLogger(__name__)
logFmt = '%(asctime)s %(levelname)s %(module)s %(funcName)s %(message)s'
logDateFmt = '%Y/%m/%d %H:%M:%S'
formatter = logging.Formatter(fmt=logFmt, datefmt=logDateFmt )
logging.basicConfig(format=logFmt, datefmt=logDateFmt)
logger.setLevel(logging.INFO)

test_plan = {}


def scriptDirPath():
    '''returns the absolute path to the directory containing this script'''
    return os.path.dirname(os.path.realpath(__file__))


try:
    with open("test_plan.json", "r") as test_plan_file:
        test_plan = json.load(test_plan_file)
except Exception as e:
    logger.error(f"Failed to load test plan file! exception : {e}")
    sys.exit(1)


ap = argparse.ArgumentParser( description=__doc__,
    fromfile_prefix_chars='@', formatter_class=argparse.ArgumentDefaultsHelpFormatter )
ap.add_argument( '--authToken', help='the NCS authorization token to use (or none, to use NCS_AUTH_TOKEN env var' )
ap.add_argument( '--outDataDir', required=True, help='a path to the output data dir for this run (required)' )
ap.add_argument( '--jtlFile', help='the file name of the jtl file produced by the test plan (if any)',
    default='TestPlan_results.csv')
ap.add_argument( '--workerDir', help='the directory to upload to workers',
    default='jmeterWorker'
    )
# for analysis and plotting
ap.add_argument( '--rampStepDuration', type=float, default=60, help='duration of ramp step, in seconds' )
ap.add_argument( '--SLODuration', type=float, default=240, help='SLO duration, in seconds' )
ap.add_argument( '--SLOResponseTimeMax', type=float, default=2.5, help='SLO RT threshold, in seconds' )
# environmental
ap.add_argument( '--jmeterBinPath', help='path to the local jmeter.sh for generating html report' )
ap.add_argument( '--cookie' )
args = ap.parse_args()


workerDirPath = args.workerDir.rstrip( '/' )  # trailing slash could cause problems with rsync
if workerDirPath:
    if not os.path.isdir( workerDirPath ):
        logger.error( 'the workerDirPath "%s" is not a directory', workerDirPath )
        sys.exit( 1 )
    JMeterFrameProcessor.workerDirPath = workerDirPath
else:
    logger.error( 'this version requires a workerDirPath' )
    sys.exit( 1 )
logger.debug( 'workerDirPath: %s', workerDirPath )

jmxFilePath = test_plan["testFile"]
jmxFullerPath = os.path.join( workerDirPath, jmxFilePath )
if not os.path.isfile( jmxFullerPath ):
    logger.error( 'the jmx file "%s" was not found in %s', jmxFilePath, workerDirPath )
    sys.exit( 1 )
logger.debug( 'using test plan "%s"', jmxFilePath )


jmeterBinPath = args.jmeterBinPath
if not jmeterBinPath:
    jmeterVersion = '5.4.1'  # 5.3 and 5.4.1 have been tested, others may work as well
    jmeterBinPath = scriptDirPath()+'/apache-jmeter-%s/bin/jmeter.sh' % jmeterVersion


# use given planDuration unless it is not positive, in which case extract from the jmx
planDuration = test_plan["testDuration"]
frameTimeLimit = max( round( planDuration * 1.5 ), planDuration+8*60 ) # some slop beyond the planned duration

JMeterFrameProcessor.JMeterFilePath = jmxFilePath


device_requirements = test_plan["device_requirements"]
device_count = test_plan["device_count"]

total_devices_required = 0


for device_prop in device_count:
    total_devices_required += device_prop["count"]

""""


HERE SHOULD BE THE CODE TO EXECUTE BATCHES IN PARALLEL


"""

def executeBatch(frameProcessor, filters, timeLimit, nWorkers):
    try:
        rc = batchRunner.runBatch(
            frameProcessor = frameProcessor,
            commonInFilePath = frameProcessor.workerDirPath,
            authToken = args.authToken or os.getenv( 'NCS_AUTH_TOKEN' ) or 'YourAuthTokenHere',
            cookie = args.cookie,
            encryptFiles=False,
            timeLimit = timeLimit + 40*60,
            instTimeLimit = 6*60,
            frameTimeLimit = frameTimeLimit,
            filter = filters,
            outDataDir = outDataDir,
            startFrame = 1,
            endFrame = nWorkers,
            nWorkers = nWorkers,
            limitOneFramePerWorker = True,
            autoscaleMax = 1
        )
    except KeyboardInterrupt:
        print("Interruption occured")
    return rc

nFrames = args.nWorkers
#nWorkers = round( nFrames * 1.5 )  # old formula
nWorkers = math.ceil(nFrames*1.5) if nFrames <=10 else round( max( nFrames*1.12, nFrames + 5 * math.log10( nFrames ) ) )

dateTimeTag = datetime.datetime.now().strftime( '%Y-%m-%d_%H%M%S' )
outDataDir = args.outDataDir

try:
    if (rc == 0) and os.path.isfile( outDataDir +'/recruitLaunched.json' ):
        rampStepDuration = args.rampStepDuration
        SLODuration = args.SLODuration
        SLOResponseTimeMax = args.SLOResponseTimeMax

        rc2 = subprocess.call( [sys.executable, scriptDirPath()+'/plotJMeterOutput.py',
            '--dataDirPath', outDataDir,
            '--rampStepDuration', str(rampStepDuration), '--SLODuration', str(SLODuration),
            '--SLOResponseTimeMax', str(SLOResponseTimeMax)
            ],
            stdout=subprocess.DEVNULL )
        if rc2:
            logger.warning( 'plotJMeterOutput exited with returnCode %d', rc2 )
 
        jtlFileName = args.jtlFile  # make this match output file name from the .jmx (or empty if none)
        if jtlFileName:
            nameParts = os.path.splitext(jtlFileName)
            mergedJtlFileName = nameParts[0]+'_merged_' + dateTimeTag + nameParts[1]
            rc2 = subprocess.call( [sys.executable, scriptDirPath()+'/mergeBatchOutput.py',
                '--dataDirPath', outDataDir,
                '--csvPat', 'jmeterOut_%%03d/%s' % jtlFileName,
                '--mergedCsv', mergedJtlFileName
                ], stdout=subprocess.DEVNULL
                )
            if rc2:
                logger.warning( 'mergeBatchOutput.py exited with returnCode %d', rc2 )
            else:
                if not os.path.isfile( jmeterBinPath ):
                    logger.info( 'no jmeter installed for producing reports (%s)', jmeterBinPath )
                else:
                    rcx = subprocess.call( [jmeterBinPath,
                        '-g', os.path.join( outDataDir, mergedJtlFileName ),
                        '-o', os.path.join( outDataDir, 'htmlReport' )
                        ], stderr=subprocess.DEVNULL
                    )
                    try:
                        shutil.move( 'jmeter.log', os.path.join( outDataDir, 'genHtml.log') )
                    except Exception as exc:
                        logger.warning( 'could not move the jmeter.log file (%s) %s', type(exc), exc )
                    if rcx:
                        logger.warning( 'jmeter reporting exited with returnCode %d', rcx )
    sys.exit( rc )
except KeyboardInterrupt:
    logger.warning( 'an interuption occurred')
