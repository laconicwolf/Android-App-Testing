#!/usr/bin/env python3

import sys

if not sys.version.startswith('3'):
    print('\n[-] This script will only work with Python3. Sorry!\n')
    exit()

import subprocess
import os
import shutil
import argparse
import urllib.request


__author__ = "Jake Miller (@LaconicWolf)"
__date__ = "20190705"
__version__ = "0.01"
__description__ = '''A script to repackage an APK file to allow a user-installed SSL certificate.'''


def check_for_tools(name):
    """Checks to see whether the tool name is in current directory or in the PATH"""
    if is_in_dir(name) or is_in_path(name):
        return True
    else:
        return False


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


def apktool_decompile(filename):
    """Uses APKTool to decompile an APK"""
    output = subprocess.getoutput("apktool d {} -o {}".format(filename, filename.replace('.apk', '_out')))
    if 'Exception in' in output:
        print('[-] An error occurred when decompiling the APK.')
        print(output)
        try:
            os.rmdir(filename.replace('.apk', '_out'))
        except:
            pass
        return False
    else:
        return True


def apktool_build(filepath):
    """Uses APKTool to create a new APK"""
    output = subprocess.getoutput("apktool b {}".format(filepath))
    try:
        os.listdir(filepath + os.sep + 'dist')
    except FileNotFoundError:
        print('[-] An error occurred when rebuilding the APK.')
        print(output)
        return False
    return True


def do_keytool(keystore_name):
    """Uses keytool to generate a key."""
    newline = os.linesep

    '''Ugly hack to get around answering interactive prompts
    The output would have been something like:
    Generating 2,048 bit RSA key pair and self-signed certificate (SHA256withRSA) with a validity of 10,000 days
        for: CN=Y, OU=Unknown, O=Y, L=Unknown, ST=Y, C=Unknown
    [Storing test.keystore]'''
    commands = ['Y', 'Y', 'Y', 'Y', 'Y', 'Y']
    FNULL = open(os.devnull, 'w')
    p = subprocess.Popen(['keytool', '-genkey', '-v', '-keystore',
                          keystore_name, '-storepass', 'password',
                          '-alias', 'android', '-keypass', 'password',
                          '-keyalg', 'RSA', '-keysize', '2048', '-validity',
                          '10000'],
                          stdin=subprocess.PIPE, stderr=subprocess.STDOUT,
                          stdout=FNULL, universal_newlines=True)
    p.communicate(newline.join(commands))
    keystore_present = True


def do_jarsigner(filepath, keystore):
    """Uses APKTool to create a new APK"""
    output = subprocess.getoutput("jarsigner -verbose -keystore {} -storepass password -keypass password {} android".format(keystore, filepath))
    if 'jar signed.' not in output:
        print("[-] An error occurred during jarsigner: \n{}".format(output))
    else:
        print("[*] Signed!")

def add_network_security_config(basedir):
    """Adds a network security config file that allows user 
    certificates.
    """
    data = '''\
<network-security-config>  
    <base-config> 
        <trust-anchors> 
            <!-- Trust preinstalled CAs --> 
            <certificates src="system" /> 
            <!-- Trust user added CAs --> 
            <certificates src="user" />
            <!-- Trust any CA in this folder -->
            <certificates src="@raw/cacert"/>
        </trust-anchors> 
    </base-config> 
</network-security-config>'''
    with open(os.path.join(basedir, 'res', 'xml', 'network_security_config.xml'), 'w') as fh:
        fh.write(data)


def do_network_security_config(directory):
    """Checks for a network security config file in the project.
    If present, reads the file and adds a line to allow user certs.
    If not present, creates one to allow user certs.
    """
    # Still need to add the line if the file already exists
    if 'xml' in os.listdir(os.path.join(directory, 'res')):
        if 'network_security_config.xml' in os.listdir(os.path.join(directory, 'res', 'xml')):
            filepath = os.path.join(directory, 'res', 'xml', 'network_security_config.xml')
            with open(filepath) as fh:
                contents = fh.read()
            new_contents = contents.replace('<trust-anchors>', '<trust-anchors>\n            <certificates src="user" />\n            <certificates src="@raw/cacert"/>')
            with open(filepath, 'w') as fh:
                fh.write(new_contents)
            return True
        else:
            print('[*] Adding network_security_config.xml to {}.'.format(os.path.join(directory, 'res', 'xml')))
            add_network_security_config(directory)
    else:
        print('[*] Creating {} and adding network_security_config.xml.'.format(os.path.join(directory, 'res', 'xml')))
        os.mkdir(os.path.join(directory, 'res', 'xml'))
        add_network_security_config(directory)


def check_for_burp(host, port):
    """Checks to see if Burp is running."""
    url = ("http://{}:{}/".format(host, port))
    try:
        resp = urllib.request.urlopen(url)
    except Exception as e:
        return False
    if b"Burp Suite" in resp.read():
        return True
    else:
        return False


def download_burp_cert(host, port):
    """Downloads the Burp Suite certificate."""
    url = ("http://{}:{}/cert".format(host, port))
    file_name = 'cacert.der'
    # Download the file from url and save it locally under file_name:
    try:
        with urllib.request.urlopen(url) as response, open(file_name, 'wb') as out_file:
            data = response.read() # a bytes object
            out_file.write(data)
            cert_present = True
        return file_name
    except Exception as e:
        print('[-] An error occurred: {}'.format(e))
        exit()


def edit_manifest(filepath):
    '''Adds android:networkSecurityConfig="@xml/network_security_config" 
    to the manifest'''
    with open(filepath) as fh:
        contents = fh.read()
    new_contents = contents.replace("<application ", '<application android:networkSecurityConfig="@xml/network_security_config" ')
    with open(filepath, 'w') as fh:
        fh.write(new_contents)


def main():
    """Checks for tools, and repackages an APK to allow
    a user-installed SSL certificate.
    """

    # Check for required tools
    print('[*] Checking for required tools...')
    required_tools = ("apktool", "keytool", "jarsigner")
    missing_tools = []
    for tool in required_tools:
        if not check_for_tools(tool):
            missing_tools.append(tool)
    if missing_tools:
        for tool in missing_tools:
            print("[-] {} could not be found in the current directory or in your PATH. Please ensure either of these conditions are met.".format(tool))
            exit()

    # Checks for Burp and adds the cert to the project

    # Not sure why certname needs to be global. Kept getting an
    # error saying I was referencing before defining it (shrug)
    global certname
    if not cert_present:
        burp = check_for_burp(burp_host, burp_port)
        if not burp:
            print("[-] Burp not found on {}:{}. Please start Burp and specify ".format(burp_host, burp_port),
                  "the proxy host and port (-pr 127.0.0.1:8080), or specify the ",
                  "path to the self-signed burp cert (-c path/to/cacert.der).")
            exit()

        # Download the burp cert
        print("[*] Downloading Burp cert from http://{}:{}".format(burp_host, burp_port))
        certname = download_burp_cert(burp_host, burp_port)

    # Iterate through the APKs
    for file in args.apk_input_file:

        # Decompile the app with APKTool
        print("[*] Decompiling {}...".format(file))
        if not apktool_decompile(file):
            continue
        project_dir = file.replace('.apk', '_out') 

        # Create or add to network_security_config.xml
        config_exists = do_network_security_config(project_dir)

        # Add the certificate to the project
        print("[*] Adding the cert to {}".format(project_dir))
        cert_dest_path = os.path.join(project_dir, 'res', 'raw', certname)
        os.makedirs(os.path.join(project_dir, 'res', 'raw'), exist_ok=True)
        shutil.copy2(certname, cert_dest_path)
        print("[*] {} copied to {}".format(certname, cert_dest_path))

        # Edit the manifest if there wasn't already a config
        if not config_exists:
            print('[*] Changing the manifest...')
            manifest_filepath = project_dir + os.sep + 'AndroidManifest.xml'
            edit_manifest(manifest_filepath)

        # Repackage the APK
        print('[*] Rebuilding the APK...')
        if not apktool_build(project_dir):
            exit()
        new_apk = os.path.join(project_dir, 'dist', os.listdir(project_dir + os.sep + 'dist')[0])

        # Sign the APK
        print("[*] Signing the APK...")
        if not keystore_present:
            print("[*] Generating keystore...")
            do_keytool(keystore_filename)
        do_jarsigner(new_apk, keystore_filename)
        print('[+] Repackaging complete. Install using "adb install {}"'.format(new_apk))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('apk_input_file',
                        nargs='+',
                        help='Specify the APK file(s) to repackage.')
    parser.add_argument('-c', '--cert_path',
                        help='Specify the path to either a PEM or DER formatted file.')
    parser.add_argument('-k', '--keystore_path',
                        help='Specify the path to an existing keystore.')
    parser.add_argument("-pr", "--proxy",
                        nargs='?',
                        const="127.0.0.1:8080",
                        default="127.0.0.1:8080",
                        help="Specify the host and port where burp is listening (default 127.0.0.1:8080)")
    args = parser.parse_args()

    keystore_present = False
    if args.keystore_path:
        if not os.path.exists(args.keystore_path):
            print("[-] The file, {}, cannot be found, or you do not have permission to open the file. Please check the file path and try again.".format(file))
            exit()
        keystore_filename = args.keystore_path
        keystore_present = True
    else:
        keystore_filename = "my_keystore.keystore"

    cert_present = False
    if args.cert_path:
        if not os.path.exists(args.cert_path):
            print("[-] The file, {}, cannot be found, or you do not have permission to open the file. Please check the file path and try again.".format(file))
            exit()
        certname = args.cert_path
        cert_present = True
    else:
        certname = ''

    for file in args.apk_input_file:
        if not os.path.exists(file):
            print("[-] The file, {}, cannot be found, or you do not have permission to open the file. Please check the file path and try again.".format(file))
            exit()
        if not file.endswith('.apk'):
            print("[-] Please verify that the file, {}, is in apk file. If it is, just add .apk to the filename.".format(file))
            exit()

    if args.proxy.startswith('http'):
        if '://' not in args.proxy:
            print("[-] Unknown format for proxy. Please specify only a host and port (-pr 127.0.0.1:8080")
            exit()
        args.proxy = ''.join(args.proxy.split("//")[1:])

    burp_host = args.proxy.split(":")[0] 
    burp_port = int(args.proxy.split(":")[1])
    main()