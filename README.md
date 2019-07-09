# Android-App-Testing
Scripts to help test Android apps

## install_burp_cert.py
Automates the process of installing a Burp Suite certificate on a rooted Android device prior to Android Nougat. Works perfect on an emaulated KitKat. I noticed a few intermittent SSL error on certain sites when testing on Marshmallow. I only have tested this on emulated devices. Requires PyOpenSSL, as well as having ADB installed in your path and Burp running, and a connected device reachable with ADB.
