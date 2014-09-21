#!/usr/bin/python
# curl -XPOST -H "Content-Type: application/json" -d '{"tier":"production","datacenter": "ord", "environment" : "example_netwrk", "signed" : "False", "artifact": "/epel-release-5-4.noarch.rpm"}'  'http://localhost:9090/scripts/example' | python -m json.tool


# -- jojo --
# description: The purpose of this script is to take a local RPM artifact and drop it on to the yum repository of choice.
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


# This script in a nutshell
# 1) Takes a local RPM and validates it is acceptable to upload.
# 2) Uploads the .rpm to the RECIEVING directory account on yum repo of choice.

verbose=True

import sys, os, yaml, traceback
from fabric.api import local, put, run, settings
from fabric.tasks import execute
from pipes import quote # Escapes bash control chars.

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
        sys.exit(1)
    else:
        if verbose: print "DEBUG:: " + name + "=" + str(variable)

def display(text):
    """ Prints some informational messages that are preformatted."""
    comment_seperator="---------------------->>\n                          "
    print comment_seperator+text

var_file = quote(os.environ.get('ARTIFACT'));           halt_if_value_empty(var_file,'artifact')
var_environment = quote(os.environ.get('ENVIRONMENT')); halt_if_value_empty(var_environment,'environment')
var_datacenter = quote(os.environ.get('DATACENTER'));   halt_if_value_empty(var_datacenter,'datacenter')
var_tier = quote(os.environ.get('TIER'));               halt_if_value_empty(var_tier,'tier')

var_signed = quote(os.environ.get('SIGNED'))

def locate_server():
    """ Locates the server we need to perform operations on. It looks in CWD for a reposervers.yml file.
        It expects the following yaml format:
        reposervers:
            production:
                ord:
                    "cloud_signup":
                        - "https://10.x.x.x"
     """
    stream = open("/srv/scripts/config.yaml", 'r')
    try:
        print yaml.load(stream)['reposervers'][var_tier][var_datacenter][var_environment]
    except KeyError:
        sys.stdout.write('jojo_return_value ERROR_MESSAGE=Missing key lookup in yaml file. Look for keyerror in STDERR.\n')
        sys.stdout.write('jojo_return_value JOB_STATUS=fail\n')
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


def sendfile():
    """ Sends a file to the yum server of choice. """
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

    execution_report("File transfer to <hostname> success!",0)
locate_server()
execute(sendfile, hosts=["root@104.130.162.166"])

