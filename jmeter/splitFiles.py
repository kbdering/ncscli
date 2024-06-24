"""
Splits files between the machines - works for a row-separated files, like csv.
Assures uniqueness of datasets on the machine, without breaking the compatibility with the test scripts
Parition options are:
- REGIONAL: 
    File is partitioned between machines in a single region, i.e. US
- GLOBAL:
    File is partitioned between all the launched machines
- UNIQUE_LOCAL:
    File will be available only on a single machine from defined region
- UNIQUE_GLOBAL:
    File will be available only on a single machine from all the regions

"""
import os 
import shutil
import sys
import json

# file buffer size
BUF_SIZE = 1024
TEST_PLAN_PATH = "test_plan.json"

def splitFile(filename, contains_headers, partition_id, number_of_partitions):
    file_copy = f"{filename}.bak"
    shutil.copyfile(filename, file_copy)
    with open (file_copy, "rt") as infile:
        with open(filename, "wt") as outfile:
            if contains_headers:
                outfile.write(infile.readline(BUF_SIZE))
            index = 0
            while True:
                line = infile.readline(BUF_SIZE)
                if not line:
                    break
                if number_of_partitions % index == partition_id:
                    outfile.write(f"{line}\n")
                index = number_of_partitions % (index + 1)

def read_file_properties():
    try:
        with open(TEST_PLAN_PATH, "r") as test_plan:
            file_properties = json.load(test_plan)["file_properties"]
        return file_properties
    except Exception as e:
        print(f"Failed to load file properties for split, exception {e}")
        sys.exit(1)

def remove_file(filename):
    os.remove(filename)

if __name__ == "__main__":

    try:
        global_instance_id = int(os.environ["GLOBAL_INSTANCE_ID"])
        local_instance_id = int(os.environ["LOCAL_INSTANCE_ID"])
        global_instance_count = int(os.environ["GLOBAL_INSTANCE_COUNT"])
        local_instance_count = int(os.environ["LOCAL_INSTANCE_COUNT"])
        current_location = os.environ["CURRENT_LOCATION"]
    except ValueError:
        print("Missing environment variables to split the files, or the values are not numbers!")
        sys.exit(1)

    file_properties = read_file_properties()
    for file in file_properties:
        partition_scope = file["partition_scope"]
        if partition_scope == "REGIONAL" and file["region"] == current_location:
            splitFile(file["filename"], file["contains_headers", local_instance_id, local_instance_count - 1])
        elif partition_scope == "GLOBAL":
            splitFile(file["filename"], file["contains_headers"], global_instance_id, global_instance_count - 1)
        elif partition_scope == "UNIQUE_GLOBAL" and global_instance_id != 0:
            remove_file(file["filename"])
        elif partition_scope == "UNIQUE_LOCAL" and local_instance_id !=0:
            remove_file(file["filename"])