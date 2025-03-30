import platform
import os
import shutil
import const as C
import json
import requests
import hashlib
import zipfile
import tarfile


def get_system_info():
    """
    Return system basic information.
    """
    return {
        "system": platform.system().lower(),
        "architecture": platform.architecture()[0],
        "machine": platform.machine().lower(),
    }

def is_valid_system_requirements():
    """
    Checks if the current system meets the requirements for compiling & running the application.
    """
    is_valid = True
    
    system_info = get_system_info()
    system = system_info["system"]
    architecture = system_info["architecture"]
    machine = system_info["machine"]
    
    print(f"Current System: {system}, {architecture}, {machine}")
    
    if system not in C.SUPPORTED_OS:
        is_valid = False

    if machine not in C.SUPPORTED_MACHINES:
        is_valid = False
    
    if architecture not in C.SUPPORTED_ARCHS:
        is_valid = False
    
    return is_valid

def download_file(url, destination):
    """
    Download a file from a URL and save it to the specified destination.
    """
    if os.path.exists(destination):
        return
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(destination, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"Downloaded {url} to {destination}")
    else:
        raise Exception(f"Failed to download {url}. Status code: {response.status_code}")

def extract_file(archive_path, output_dir, overwrite=False):
    """
    Extracts a .zip or .tar.gz file conditionally.

    :param archive_path: Path to the archive file.
    :param output_dir: Directory to extract contents to.
    :param overwrite: If True, overwrite existing files. If False, skip existing files.
    """
    if not os.path.exists(archive_path):
        raise FileNotFoundError(f"File not found: {archive_path}")

    os.makedirs(output_dir, exist_ok=True)  # Ensure output directory exists

    if archive_path.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            for file in zip_ref.namelist():
                target_path = os.path.join(output_dir, file)
                if not overwrite and os.path.exists(target_path):
                    # print(f"Skipping {file}, already exists.")
                    continue
                zip_ref.extract(file, output_dir)

    elif archive_path.endswith((".tar.gz", ".tgz")):
        with tarfile.open(archive_path, "r:gz") as tar_ref:
            for member in tar_ref.getmembers():
                target_path = os.path.join(output_dir, member.name)
                if not overwrite and os.path.exists(target_path):
                    # print(f"Skipping {member.name}, already exists.")
                    continue
                tar_ref.extract(member, output_dir)

    else:
        raise ValueError("Unsupported archive format. Only .zip and .tar.gz are supported.")

    print(f"Extraction completed: {output_dir}")


def find_jdk_bin(parent_dir):
    """
    Finds the JDK bin directory given a parent directory.

    :param parent_dir: The directory where JDK installations may exist.
    :return: The path to the JDK bin directory if found, else None.
    """
    if not os.path.exists(parent_dir):
        raise FileNotFoundError(f"Parent directory not found: {parent_dir}")

    for root, dirs, _ in os.walk(parent_dir):
        if "bin" in dirs and any(f.startswith("java") for f in os.listdir(os.path.join(root, "bin"))):
            return os.path.join(root, "bin")

    raise FileNotFoundError("JDK bin directory not found in the specified path.")

def clear_directory(directory):
    """
    Deletes all files and subdirectories inside the given directory, including hidden ones.

    :param directory: Path to the directory to be cleared.
    """
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Directory not found: {directory}")

    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):  # File or symlink
                os.unlink(item_path)
            elif os.path.isdir(item_path):  # Directory
                shutil.rmtree(item_path)
        except Exception as e:
            print(f"Failed to delete {item_path}: {e}")
            raise e


def find_jar(target_dir):
    """Finds the first JAR file in the target directory."""
    if not os.path.isdir(target_dir):
        raise NotADirectoryError(f"Target path is not a directory: {target_dir}")

    # List files and filter for .jar files
    jar_files = [f for f in os.listdir(target_dir) if f.endswith(".jar")]

    if not jar_files:
        raise FileNotFoundError(f"No JAR files found in the directory: {target_dir}")

    # Return the first found JAR file
    return os.path.join(target_dir, jar_files[0])


def copy_directory(src, dst):
    """
    Copies the entire directory from src to dst.
    If dst exists, it will be replaced.
    """
    if not os.path.exists(src):
        print(f"❌ Source directory does not exist: {src}")
        return

    if os.path.exists(dst):
        print(f"⚠️ Destination already exists. Removing: {dst}")
        shutil.rmtree(dst)  # Remove existing directory

    shutil.copytree(src, dst)