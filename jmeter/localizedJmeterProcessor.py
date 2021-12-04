import ncscli.batchRunner as batchRunner
import glob
import os


class LocalJMeterFrameProcessor(batchRunner.frameProcessor):
    '''
    Defines installation and execution of a jmeter test, for a single region within a global context
    

    '''

    def __init__(self, current_instance_count, current_location, number_of_local_instances, number_of_global_instances, test_properties):
        self.current_location = current_location
        self.instance_begin_count = current_instance_count
        self.local_instances = number_of_local_instances
        self.number_of_global_instances = number_of_global_instances
        self.test_properties = test_properties

    homeDirPath = '/root'
    workerDirPath = 'jmeterWorker'
    JMeterFilePath = workerDirPath+'/XXX.jmx'
    JVM_ARGS ='-Xms30m -XX:MaxMetaspaceSize=64m -Dnashorn.args=--no-deprecation-warning'
    # a shell command that uses python psutil to get a recommended java heap size
    # computes available ram minus some number for safety, but not less than some minimum
    clause = "python3 -c 'import psutil; print( max( 32000000, psutil.virtual_memory().available-400000000 ) )'"

    def installerCmd( self ):
        cmd = 'free --mega -t 1>&2'
        cmd += f" && {self._get_copy_jars_cmd()}"
        cmd += " && JVM_ARGS='%s -Xmx$(%s)' /opt/apache-jmeter/bin/jmeter.sh --version" % (self.JVM_ARGS, self.clause)

        # tougher pretest
        pretestFilePath = self.workerDirPath+'/pretest.jmx'
        if os.path.isfile( pretestFilePath ):
            cmd += " && cd %s && JVM_ARGS='%s -Xmx$(%s)' /opt/apache-jmeter/bin/jmeter -n -t %s/%s/pretest.jmx -l jmeterOut/pretest_results.csv -D httpclient4.time_to_live=1 -D httpclient.reset_state_on_thread_group_iteration=true" % (
                self.workerDirPath, self.JVM_ARGS, self.clause, self.homeDirPath, self.workerDirPath
            )
        return cmd

    def frameOutFileName( self, frameNum ):
        return 'jmeterOut_%03d' % frameNum + self.instance_begin_count
        #return 'TestPlan_results_%03d.csv' % frameNum

    def frameCmd( self, frameNum ):
        cmd = f"{self._get_id_config_command(frameNum)} && "
        cmd += f"{self._get_split_files_cmd()} && "
        cmd += f"""cd {self.workerDirPath} && mkdir -p jmeterOut && JVM_ARGS="{self.JVM_ARGS} -Xmx$({self.clause})" /opt/apache-jmeter/bin/jmeter.sh -n -t {self.homeDirPath}/{self.workerDirPath}/{self.JMeterFilePath} -l jmeterOut/TestPlan_results.csv -D httpclient4.time_to_live=1 -D httpclient.reset_state_on_thread_group_iteration=true"""
        cmd += f" && mv jmeterOut ~/{self.frameOutFileName(frameNum)}"
        return cmd

    def _get_copy_jars_cmd(self):
        cmd = ""
        if glob.glob(os.path.join( self.workerDirPath, '*.jar')):
            cmd += ' && cp -p %s/*.jar /opt/apache-jmeter/lib/ext' % self.workerDirPath
        return cmd

    def _get_update_properties_cmd(self):
        cmd = f"{self._get_update_localized_properties_cmd()}"
        return cmd

    def _get_update_localization_properties_cmd(self):
        cmd = f"python3 {self.homeDirPath}/{self.workerDirPath}/loadLocalDeviceProperties.py"
        return cmd

    def _get_id_config_command(self, ordered_instance_id):
        cmd = f"""export GLOBAL_INSTANCE_ID={ordered_instance_id + self.instance_begin_count} && \
            export LOCAL_INSTANCE_ID={ordered_instance_id} && \
            export GLOBAL_INSTANCE_COUNT={self.number_of_global_instances} && \
            export LOCAL_INSTANCE_COUNT={self.local_instances} && \
            export CURRENT_LOCATION={self.current_location}"""
        return cmd

    def _get_split_files_cmd(self):
        cmd = f"python3 {self.homeDirPath}/{self.workerDirPath}/splitFiles.py"
        return cmd