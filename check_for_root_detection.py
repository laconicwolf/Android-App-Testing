#!/usr/bin/env python3

__author__ = "Jake Miller (@LaconicWolf)"
__date__ = "20190726"
__version__ = "0.01"
__description__ = '''\
A script that recursively searches smali files for the presence of root detection strings.
First, decode an APK with apktool "apktool d example.apk". Next, move to the newly created 
directory and run this script.
'''

import sys

if not sys.version.startswith('3'):
    print('\n[-] This script will only work with Python3. Sorry!\n')
    exit()

import os
import re
from multiprocessing import Pool, cpu_count


def find_smali_files(root_dir):
    """Recursively looks for *.smali files and returns
    a list containing the full file path.
    """
    smali_files = []
    for root, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.smali'):
                smali_files.append(os.path.join(root, filename))
    return smali_files


def search_text_for_root_detection_strings(textfile):
    """Reads and searches a specified textfile for presence 
    of root detection strings. Returns the name
    of the text file and matches if a match is found. Based on:
    https://stackoverflow.com/questions/1101380/determine-if-running-on-a-rooted-device
    and:
    https://stackoverflow.com/questions/12286928/fastest-way-in-python-to-search-for-multiple-items-in-a-body-of-text
    """
    root_detection_strings = [
                "/system/app/Superuser.apk", "/sbin/su",
                "/system/bin/su", "/system/xbin/su", "/data/local/xbin/su",
                "/data/local/bin/su", "/system/sd/xbin/su", 
                "/system/bin/failsafe/su", "/data/local/su", "/su/bin/su",
                "test-keys", '"/system/xbin/which", "su"', "'/system/xbin/which', 'su'",
            ]
    with open(textfile) as fh:
        contents = fh.read()
    regex = re.compile('|'.join(re.escape(x) for x in root_detection_strings))
    found = regex.findall(contents)
    if found:
        print("{} : {}".format(textfile, found))


def main():
    root_dir = '.'
    smali_file_list = find_smali_files(root_dir)
    with Pool(int(cpu_count()/2)) as p:
        p.map(search_text_for_root_detection_strings, smali_file_list)


if __name__ == '__main__':
    main()