import json
import shutil
from utils import ( 
    copy_directory,
    find_jar,
    get_system_info,
    is_valid_system_requirements,
    download_file,
    extract_file,
    find_jdk_bin,
    clear_directory
)

import const as C
import os
import subprocess
from pathlib import Path

WORKING_DIR = Path(__file__).resolve().parent


#
# Check system requirements
#


if not is_valid_system_requirements():
    print("System requirements not met. Exiting.")
    exit(1)


#
# Download JDK
#


JDK_DIR = os.path.join(WORKING_DIR, "resources", "jdk")

system = get_system_info()["system"]
if system == "windows":
    JDK_URL = C.JDK_17_64_URL_WINDOWS
    JDK_ZIP_PATH = os.path.join(JDK_DIR, "jdk.zip")
else:
    JDK_URL = C.JDK_17_64_URL_LINUX
    JDK_ZIP_PATH = os.path.join(JDK_DIR, "jdk.tar.gz")

print(f"Downloading JDK from {JDK_URL} to {JDK_ZIP_PATH}")

download_file(JDK_URL, JDK_ZIP_PATH)
extract_file(JDK_ZIP_PATH, JDK_DIR, overwrite=False)


#
# Initialize paths
#


JDK_BIN = find_jdk_bin(JDK_DIR)
JAVA_ENTRY = os.path.join(JDK_BIN, "java")
BASE_RESOURCES_DIR = os.path.join(WORKING_DIR, "resources")
BE_SOURCE_DIR = os.path.join(BASE_RESOURCES_DIR, "be_source")
FE_SOURCE_DIR = os.path.join(BE_SOURCE_DIR, "frontend")
BE_BUILD_DIR = os.path.join(BE_SOURCE_DIR, "target")
FE_BUILD_DIR = os.path.join(BE_SOURCE_DIR, "frontend", "dist")

os.makedirs(BE_SOURCE_DIR, exist_ok=True)

subprocess.run([JAVA_ENTRY, "--version"], check=True)


#
# Download source code
#


print("Downloading BE source code...")
clear_directory(BE_SOURCE_DIR)
args = [
    "git", "clone",
    "--depth", "1",
    "--branch", C.SOURCE_GIT_BRANCH,
    C.SOURCE_GIT_URL,
    BE_SOURCE_DIR
]
subprocess.run(args, check=True)


#
# Build backend, frontend using maven
#


print("Installing, compiling resources...")
MVN_WRAPPER_ENTRY = os.path.join(BE_SOURCE_DIR, "mvnw.cmd" if system == "windows" else "mvnw")
if system == "linux" and not os.access(MVN_WRAPPER_ENTRY, os.X_OK):  # Check if executable
    print(f"Setting executable permission for {MVN_WRAPPER_ENTRY} ...")
    os.chmod(MVN_WRAPPER_ENTRY, 0o775)

args = [
    MVN_WRAPPER_ENTRY,
    "clean",
    "package",
    "-Dcheckstyle.skip=true",
    "-DskipTests",
    "-PwithFront",
]

SESSION_ENVIRONMENT = {
    "JAVA_HOME": os.path.dirname(os.path.dirname(JAVA_ENTRY)),
    **dict(subprocess.os.environ)
}

subprocess.run(args,
            env=SESSION_ENVIRONMENT,
            cwd=BE_SOURCE_DIR,
            check=True)


#
# Copy built jar file
#


jar_name = "backend.jar"

print("Copying BE jar file...")
jar_file_abs_path = find_jar(BE_BUILD_DIR)
jar_file_path_final = os.path.join(BASE_RESOURCES_DIR, jar_name)
shutil.copyfile(jar_file_abs_path, jar_file_path_final)


#
# Copy frontend built static resources 
#


print("Copying FE resources...")
fe_final_dir = os.path.join(BASE_RESOURCES_DIR, "frontend")
copy_directory(FE_BUILD_DIR, fe_final_dir)
fe_entry_file = os.path.join(fe_final_dir, "index.html")



#
# Make entries.json (relative paths)
#


print("Making entries.json...")
entries_json_path = os.path.join(BASE_RESOURCES_DIR, "entries.json")

jdk_bin_relative_path = JDK_BIN.split("resources" + os.path.sep)[1]
backend_jar_relative_path = jar_name
fe_entry_relative_path = fe_entry_file.split("resources" + os.path.sep)[1]

with open(entries_json_path, "w") as f:
    json.dump(
        {
            "jdk": jdk_bin_relative_path,
            "backend": backend_jar_relative_path,
            "frontend": fe_entry_relative_path
        },
        f,
        indent=2
    )


#
# Remove production unnecessary files
#

print("Cleaning up...")
shutil.rmtree(BE_SOURCE_DIR)
archived_files = [f for f in os.listdir(JDK_DIR) if f.endswith((".tar.gz", ".zip"))]
for archived_file in archived_files:
    os.remove(os.path.join(JDK_DIR, archived_file))

print("Build completed successfully.")