# Android-App-Testing
Scripts to help test Android apps

## install_burp_cert.py
Automates the process of installing a Burp Suite certificate on a rooted Android device prior to Android Nougat. Installs a cert as a system trusted CA. I noticed a few intermittent SSL error on certain sites when testing on Marshmallow, but works perfect on an emulated KitKat. I only have tested this on emulated devices. Requires PyOpenSSL, as well as having ADB installed in your path and Burp running, and a connected device reachable with ADB.

## repackage_apk_for_burp.py
Automates the process of making apps work with Burp Suite in Android devices from Nougat forward. Decompiles an APK, adds a network-security-config and Burp's CA cert to the project and recompiles. Only tested on emulated Nougat. Requires [apktool](https://ibotpeaches.github.io/Apktool/install/), keytool and jarsigner (available in the JDK), to be in your path, and requires Burp to be running (or you can supply a path to the cacert.der).
