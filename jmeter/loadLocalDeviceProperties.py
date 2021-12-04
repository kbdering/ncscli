import os
import json

"""
Adds local properties to jmeter runtime. 
Props added to user.properties can be referenced directly by Jmeter script
with no need of a separate CSV File Reader, making the test localization seamless.

-- device location properties:
   - country name
   - country-code
   - area
   - locality
   - ...

-- Region-specific properties: 
   When adding a .properties file prefixed with the area, i.e {area}.properties the file would be appended to the devices only matching
   the area in the filename:
   Example :
       usa.properties would be appended only to the devices located in US.
       india.properties would be available only on devices in India
   Useful for a data-driven test scripts where users from different regions would hit different hosts
   
"""

jmeter_path = "/opt/apache-jmeter/bin/"
worker_dir_path = "jmeterWorker"
device_location_file = "'~/.neocortix/device-location.json'"


def get_device_info():
    device_info = {}
    with open(os.path.expanduser(device_location_file), "rt") as f:
        try:
            device_info = json.load(f)
        except Exception:
            print(f"Failed to load file {device_location_file} as JSON")
            print("Missing localization properties!")
    return device_info


def add_props_to_jmeter_properties(local_props):
    # appends the properties to user.properties
    with open(os.path.join(jmeter_path, "user.properties"), "a") as outfile:
        outfile.write("\n")

        for key, value in local_props.items():
            outfile.write(f"{key}={value}\n")

        # appending all the local properties, matching the device location
        # for more strict requirements, locality, country-code can be used, at defined hierarchy.
        for area_range in ["country", "country-code", "area", "locality"]:
            try:
                local_properties_file = os.path.join(worker_dir_path, f"{local_props[area_range]}.properties")
            except KeyError:
                print(f"{area_range} data not available on the device!")
                continue
            if os.path.isfile(local_properties_file):
                with open(local_properties_file, "r") as infile:
                    for line in infile.readlines():
                        outfile.write(line + "\n")


if __name__ == "__main__":
    localization_data = get_device_info()
    localization_data["country"] = os.environ["CURRENT_LOCATION "]
    add_props_to_jmeter_properties(localization_data)
