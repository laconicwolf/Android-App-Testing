#!/usr/bin/env python3

import sys

if not sys.version.startswith('3'):
    print('\n[-] This script will only work with Python3. Sorry!\n')
    exit()

import urllib.request
import subprocess
import os
import shutil
import argparse

try:
    import OpenSSL
except ImportError:
    print("[-] This script requires pyOpenSSL. Try 'python3 -m pip install pyopenssl' or consult the Internet for installation instructions.")
    exit()

__author__ = "Jake Miller (@LaconicWolf)"
__date__ = "20190705"
__version__ = "0.01"
__description__ = '''A script to help install a Burp proxy certificate on Android devices prior to Nougat.
Largely based on https://blog.ropnop.com/configuring-burp-suite-with-android-nougat/'''


def check_for_tools(name):
    """Checks to see whether the tool name is in current directory or in the PATH"""
    if is_in_dir(name) or is_in_path(name):
        return True
    else:
        return False


def check_for_burp(host, port):
    """Checks to see if Burp is running."""
    url = ("http://{}:{}/".format(host, port))
    try:
        resp = urllib.request.urlopen(url)
    except urllib.error.URLError as e:
        return False
    if b"Burp Suite" in resp.read():
        return True
    else:
        return False


def download_burp_cert(host, port):
    """Downloads the Burp Suite certificate."""
    url = ("http://{}:{}/cert".format(host, port))
    file_name = 'cacert.cer'
    # Download the file from url and save it locally under file_name:
    try:
        with urllib.request.urlopen(url) as response, open(file_name, 'wb') as out_file:
            data = response.read() # a bytes object
            out_file.write(data)
        return file_name
    except Exception as e:
        print('[-] An error occurred: {}'.format(e))
        exit()


def is_in_path(name):
    """Check whether name is on PATH and marked as executable.
    https://stackoverflow.com/questions/11210104/check-if-a-program-exists-from-a-python-script/34177358
    """
    return shutil.which(name) is not None


def is_in_dir(name, directory='.'):
    """Checks whether a file exists in a specified directory."""
    files = (os.listdir(directory))
    for file in files:
        if file.lower() == name.lower():
            if os.path.isfile(file):
                return True


def get_devices():
    """Uses adb to get a list of attached devices. The output string is formatted
    to a list, and returned.
    """
    devices = subprocess.getoutput("adb devices").split('List of devices attached\n')[1]
    if not devices:
        return False
    else:
        device_list = devices.split('\n')
    return device_list


def get_build_version_info(device_id):
    """Returns the build release as an integer"""
    ver = subprocess.getoutput("adb -s {} shell getprop ro.build.version.release".format(device_id))
    return int(ver[0])


def select_device(device_list):
    """Prompts a user to select a device from a list of devices."""
    print('[*] The following devices were found:')
    print('{}'.format('\n'.join(device_list)))
    while True:
        device = input('[*] Please enter the device you\'d like to use or type \'quit\' to exit:\n')
        if device.lower() == 'quit':
            exit()
        if device and device.lower() in [d.lower() for d in device_list]:
            return device
        else:
            print('[-] {} is not a valid choice. Type \'quit\' to exit, or select from the following options: \n{}'.format(device, '\n'.join(device_list)))


def check_for_root(device_id):
    """Uses ADB to see if we have root privileges."""
    uid = subprocess.getoutput("adb -s {} shell id".format(device_id))
    if "uid=0(root)" in uid:
        return True
    else:
        return False


def get_root(device_id):
    """Uses ADB to try to get root privileges."""
    output = subprocess.getoutput("adb -s {} root".format(device_id))


def convert_der_to_pem(filename):
    """Converts a der to a pem and writes to the filesystem."""
    with open(filename, 'rb') as fh:
        der = fh.read()
    cert = OpenSSL.crypto.load_certificate(type=OpenSSL.crypto.FILETYPE_ASN1, buffer=der)
    
    # OpenSSL and pyOpenSSL coming up with different hashes. Hardcoding it for now.
    pem_hash = '9a5ba575' # str(cert.subject_name_hash())
    pem_bytes = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
    pem_filename = pem_hash + ".0"
    with open(pem_filename, 'wb') as fh:
        fh.write(pem_bytes)
    return pem_filename


def remount_system(device_id):
    """Uses ADB to remount the /system as writable"""
    output = subprocess.getoutput("adb -s {} remount".format(device_id))
    if 'remount succeeded' in output:
        return True
    elif 'remount failed' in output:
        return False


def move_pem_to_device(pem_file, device_id):
    output = subprocess.getoutput("adb -s {} push {} /sdcard/".format(device_id, pem_file))
    output = subprocess.getoutput("adb -s {} shell mv /sdcard/{} /system/etc/security/cacerts/".format(device_id, pem_file))
    if 'Read-only file system' in output:
        return False
    elif 'failed on' in output:
        cpout = subprocess.getoutput("adb -s {} shell cp /sdcard/{} /system/etc/security/cacerts/".format(device_id, pem_file))
        if 'failed' in cpout or 'Read-only' in cpout:
            return False
        else:
            return True
    else:
        return True


def change_perms(filename, device_id):
    """Changes perms to 644 for cert file name."""
    output = subprocess.getoutput("adb -s {} shell chmod 644 /system/etc/security/cacerts/{}".format(device_id, filename))


def reboot_device(device_id):
    """Reboots a device."""
    output = subprocess.getoutput("adb -s {} shell reboot".format(device_id))


def main():
    """Checks for tools and burp, determines information about any devices,
    and attempts to convert and install the Burp cert on a specific device.
    """

    # Check for adb and burp. May check for openssl in the future...
    required_tools = ("adb",)
    missing_tools = []
    for tool in required_tools:
        if not check_for_tools(tool):
            missing_tools.append(tool)
    burp = check_for_burp(burp_host, burp_port)

    if not burp or missing_tools:
        if not burp:
            print('[-] Unable to connect to Burp at {}:{}. Please ensure the Burp web UI is running and available.'.format(burp_host, burp_port))
        for tool in missing_tools:
            print("[-] {} could not be found in the current directory or in your PATH. Please ensure either of these conditions are met.".format(tool))

    # Check for connected devices
    print('[*] Checking for connected devices')
    connected_devices = get_devices()
    if not connected_devices:
        print("[-] No devices/emulators found. Make sure adb is running and that a device is connected.")
        exit()
    connected_devices = [d.split('\t')[0] for d in connected_devices]
    connected_devices = list(filter(None, connected_devices))
    if not connected_devices:
        print("[-] No devices/emulators found. Make sure adb is running and that a device is connected.")
    if len(connected_devices) > 1:
        device = select_device(connected_devices)
    else:
        device = ''.join(connected_devices)

    # Checks to see if the device is at the API level where the cert
    # installation will even matter. After Marshmallow, this won't matter,
    # we can just exit if it is build 7 or later.
    print("[*] Checking API level.")
    rel = get_build_version_info(device)
    if rel >= 7:
        print("[-] The build version on this device will not respect a user installed certificate. Try repackaging the APK.")
        exit()

    # Checks for root. This also requires a rooted device. Otherwise exit.
    print("[*] Checking for root privileges.")
    is_rooted = check_for_root(device)
    if is_rooted:
        print('[*] Root privileges verified.')
    else:
        get_root(device)
        is_rooted = check_for_root(device)
        if is_rooted:
            print("[+] Device rooted using 'adb -s {} root'.".format(device))
        else:
            print("[-] Unable to use 'adb -s {} root' to root the device.".format(device))
            print('[-] Root is required for this method. Exiting.')
            exit()

    # Attempt to download and convert the cert from der to pem
    print("[*] Attempting to add the Burp CA cert to the device")
    print("[*] Downloading cert from http://{}:{}".format(burp_host, burp_port))
    certname = download_burp_cert(burp_host, burp_port)
    print("[*] Converting Burp Cert to pem")
    pem_file = convert_der_to_pem(certname)
    print("[*] PEM file written to {}".format(pem_file))

    # Adds the cert. Have to make /system writable first. Requires
    # an emulated device to be started with -writable-system.
    print("[*] Attempting to add cert to device")
    print("[*] Remounting /system")
    if not remount_system(device):
        print('[-] Unable to mount /system as read write. If running an emulator, please include -writable-system in the command line arguments (emulator -avd <avd_name> -writable-system)')
        exit()
    print('[*] Moving {} to the device'.format(pem_file))
    if not move_pem_to_device(pem_file, device):
        print('[-] Unable to mount /system as read write. If running an emulator, please include -writable-system in the command line arguments (emulator -avd <avd_name> -writable-system)')
        exit()

    # Change permissions on the file to 644, and then restart.
    print('[*] Changing permissions on the file.')
    change_perms(pem_file, device)
    print('[+] Success. Rebooting device. The cert should work without error after reboot.')
    reboot_device(device)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-pr", "--proxy",
                        nargs='?',
                        const="127.0.0.1:8080",
                        default="127.0.0.1:8080",
                        help="Specify a proxy to use (default 127.0.0.1:8080)")
    args = parser.parse_args()

    if args.proxy.startswith('http'):
        if '://' not in args.proxy:
            print("[-] Unknown format for proxy. Please specify only a host and port (-pr 127.0.0.1:8080")
            exit()
        args.proxy = ''.join(args.proxy.split("//")[1:])
    burp_host = args.proxy.split(":")[0] 
    burp_port = int(args.proxy.split(":")[1])
    main()