#!/usr/bin/python

# -- jojo --
# description: The purpose of this script is to send artifact to the artifact storage server.
# param: artifact  - The RPM artifact you wish to include [myfile.rpm]. (REQUIRED)
# param: arch - The architecture you wish to put this file in [x86_64,noarch,x86] (REQUIRED)
# param: release - What Redhat release to put this file in [5,6,7] (REQUIRED)
# param: environment - What environment do you want to put this in [signup,atomhopper,shared] (REQUIRED)
# param: datacenter - The datacenter to contact [ord,dfw,all] (REQUIRED)
# param: tier - The tier of service to contact [dev,staging,test,prod,stable] (REQUIRED)
# param: signed - Override the requirement for package signing and upload an unsigned package.
# http_method: post
# lock: False
# -- jojo -- 

import sys, os, yaml, traceback
from fabric.api import local, put, run, settings
from fabric.tasks import execute
from pipes import quote as bash_real_escape_string

verbose=True
configfile="/srv/scripts/config.yaml"

# Binary paths
bin_md5sum="/usr/bin/md5sum"
bin_rpm="/bin/rpm"
bin_file="/usr/bin/file"

# curl -XPOST -H "Content-Type: application/json" -d '{"tier":"production","datacenter": "ord", "environment" : "example_netwrk", "signed" : "False", "artifact": "/epel-release-5-4.noarch.rpm"}'  'http://localhost:9090/scripts/example' | python -m json.tool
# This script in a nutshell
# 1) Takes a local RPM and validates it is acceptable to upload.
# 2) Uploads the .rpm to the RECIEVING directory account on yum repo of choice.

class err(object):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warn"
    WARN = "warn"
    ERROR = "error"

def execution_report(message="Null",status=0):
    """ Used to handle exit points within the program based on execution status """
    if status >0:
        print "jojo_return_value" + "execution_message="+message
        print "jojo_return_value" + "execution_success=False"
        sys.exit(status)
    else:
        print "jojo_return_value" + "execution_message="+message
        print "jojo_return_value" + "execution_success=True"
        sys.exit(0)

def halt_if_value_empty(variable,name):
    """ Have this script bail if missing POST values. """
    if variable == "":
        sys.stdout.write('jojo_return_value ERROR_MESSAGE=Undefined key `'+name+'` in JSON POST request (required) \n')
        sys.stdout.write('jojo_return_value JOB_STATUS=fail\n')
        sys.stdout.write('jojo_return_value ERROR_META_MISSING_KEY='+name+'\n')
        sys.exit(254)
    else:
        if verbose: print "DEBUG:: " + name + "=" + str(variable)

def display(err, text):
    """ Prints some informational messages that are preformatted."""
    print "LOGLINE ::::::::::: \n     >>" + err + "<< " + text

# Get parameters.
var_file        = bash_real_escape_string(os.environ.get('ARTIFACT'))
var_environment = bash_real_escape_string(os.environ.get('ENVIRONMENT'))
var_datacenter  = bash_real_escape_string(os.environ.get('DATACENTER'))
var_tier        = bash_real_escape_string(os.environ.get('TIER'))

var_signed      = bash_real_escape_string(os.environ.get('SIGNED'))
# Don't let script continue without these parameters.
halt_if_value_empty(var_file,'artifact')
halt_if_value_empty(var_environment,'environment')
halt_if_value_empty(var_datacenter,'datacenter')
halt_if_value_empty(var_tier,'tier')


def return_artifact_servers():
    stream = open(configfile, 'r')
    try:
        return yaml.load(stream)['artifact_servers'][var_environment][var_tier][var_datacenter]
    except KeyError:
        sys.stdout.write('jojo_return_value ERROR_MESSAGE=Missing ARTIFACTSERVER key lookup in yaml file. Look for keyerror in STDERR.\n')
        sys.stdout.write('jojo_return_value JOB_STATUS=fail\n')
        traceback.print_exc(file=sys.stderr)
        sys.exit(253)
    stream.close()

def send_artifact():
    """ Sends an artifact out to the yum server of choice. """
    display(err.DEBUG,"Topfile.")

    # Use the `file` command to determine filetype of the file we're handling.
    display(err.INFO,"Attempting to validate if the LOCAL file is a valid rpm.")

    testfiletype=local(bin_file+' '+var_file,capture=True)

    # Enforce only RPM's be transmitted.
    if not "RPM" in testfiletype:
        execution_report("Your artifact is not an RPM.",252)

    # Enforce modern RPM format.
    if not "v3.0" in testfiletype:
        display(err.ERROR,"Your artifact is not a v3.0 RPM.",251)

    # Fail if pgp enforce is not skipped by parameter.
    if "pgp" not in testfiletype:
        if var_signed != "False":
            execution_report("We enforce PGP signed RPMs. Your artifact is not signed! To bypass supply signed : False as a JSON POST parameter.",250)
        else:
            display(err.WARN,"RPM artifact is missing a PGP signature.")

    # Make sure md5sum inside package is valid without gpg checking.
    rpmchecksig=local(bin_rpm+' --nosignature --checksig '+var_file,capture=True)
    if not "md5 OK" in rpmchecksig:
        execution_report("RPM artifact metadata md5sum FAIL!",249)

    # UPLOAD
    # To the artifact server
    display(err.INFO,"Transmitting artifact to artifact server...")
    put(var_file,'/srv/incoming/')

    # MD5SUM
    # Validate remote file matches local file.
    testfilemd5=local(bin_md5sum+" "+var_file,capture=True).split(' ')[1]
    remotefilemd5=run(bin_md5sum+' /srv/incoming/'+os.path.basename(var_file)).split(' ')[1]
    if remotefilemd5 != testfilemd5:
        execution_report("Remote md5sum on artifact server did not match local!",1)

servers = return_artifact_servers()
for server in servers:
    execute(send_artifact, hosts=["root@"+server])
execution_report("File transfer to "+str(servers)+" success!",0)
