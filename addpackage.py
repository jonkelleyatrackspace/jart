#!/usr/bin/python

#  Add a package curl -XPOST -H "Content-Type: application/json" -d '{"signed" : "False", "file": "/epel-release-5-4.noarch.rpm"}'  'http://localhost:9090/scripts/example' | python -m json.tool

# Reload jojo server    curl -XPOST  'http://localhost:9090/reload' -v
# -- jojo --
# description: Upload a file with fabric
# param: file  - File you wish to upload
# param: arch - What type of architecture, x86, x86_64, noarch
# param: release - What release, el6, el7, etc....
# param: environment - The environment or service stack, i.e. signup, identity
# param: datacenter - The datacenter if relevant
# param: tier - Dev, staging, prod, etc.
# param: signed - Put false if you do not want to verify package signing.
# http_method: post
# lock: False
# -- jojo -- 

verbose=True

import sys
import os
import yaml
from fabric.api import local, put, run, settings
from fabric.tasks import execute

var_file = os.environ.get('FILE',None)
var_environment = os.environ.get('ENVIRONMENT',None)
var_datacenter = os.environ.get('DATACENTER',None)
var_tier = os.environ.get('TIER',None)
var_signed = os.environ.get('SIGNED','True')

def execution_report(message="Null",status=0):
    if status >0:
        print "jojo_return_value" + "message="+message
        print "jojo_return_value" + "execution_success=False"
        sys.exit(status)
    else:
        print "jojo_return_value" + "message="+message
        print "jojo_return_value" + "execution_success=True"
        sys.exit(0)

def display(text):
    """ Prints some informational messages that are preformatted."""
    comment_seperator="---------------------->>\n                          "
    print comment_seperator+text

def upload_rpm():
    """ Checks a file to see if it is a valid RPM and if it is, uploads it."""
    display("Attempting to put file into /srv/repo on file server")

    # Use the `file` command to determine filetype of the file we're handling.
    display("INFO:: Attempting to validate if the LOCAL file is a valid rpm.")

    testfiletype=local('file '+var_file,capture=True)

    if "RPM" in testfiletype:
        display("INFO:: FILE is of type RPM...")
    else:
        execution_report("ERROR:: Your package is not an RPM",1)

    if "v3.0" in testfiletype:
        display("INFO:: FILE is of type RPM v3.0...")
    else:
        execution_report("ERROR:: Your package is not a v3.0 RPM",1)

    if "pgp" not in testfiletype:
        if var_signed != "False":
            display("ERROR:: Your package has no PGP signature.")
            execution_report("We enforce PGP signed RPMs. Your RPM is not signed!",1)
        else:
            display("WARN:: Your package has no PGP signature.")
    # Now make sure the RPM's md5sum matches inside of the .rpm file using `rpm` command.
    display("Attempting to validate RPM files md5sum...")
    rpmchecksig=local('/bin/rpm --nosignature --checksig '+var_file,capture=True)
    print rpmchecksig
    if "md5 OK" in rpmchecksig:
        display("FILE md5sum OK...")
    else:
        execution_report("File reference fails RPM md5sum check.",1)


    # Upload the file
    display(" Attempting transmit of file to file server.")
    put(var_file,'/srv/repo/')

    # List remote directory contents
    display(" Looking at remote file list.")
    run('ls -la /srv/repo/')

execute(upload_rpm, hosts=["root@104.130.162.166"])

execution_report("File upload success!",0)

