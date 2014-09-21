#!/usr/bin/python


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

verbose=True
configfile="/srv/scripts/config.yaml"

# curl -XPOST -H "Content-Type: application/json" -d '{"tier":"production","datacenter": "ord", "environment" : "example_netwrk", "signed" : "False", "artifact": "/epel-release-5-4.noarch.rpm"}'  'http://localhost:9090/scripts/example' | python -m json.tool
# This script in a nutshell
# 1) Takes a local RPM and validates it is acceptable to upload.
# 2) Uploads the .rpm to the RECIEVING directory account on yum repo of choice.

import sys, os, yaml, traceback
from fabric.api import local, put, run, settings
from fabric.tasks import execute
from pipes import quote as bash_real_escape_string

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
    comment_seperator="---------------------->>\n                          "
    print comment_seperator+err+" :: "+text+comment_seperator

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

def return_repo_servers():
    """ Locates the server we need to perform operations on. Presents itself as a LIST object.

        It expects the following yaml format:
        reposervers:
            production:
                ord:
                    "cloud_signup":
                        - "https://10.x.x.x"
     """
    stream = open(configfile, 'r')
    try:
        return yaml.load(stream)['reposervers'][var_tier][var_datacenter][var_environment]
    except KeyError:
        sys.stdout.write('jojo_return_value ERROR_MESSAGE=Missing REPOSERVER key lookup in yaml file. Look for keyerror in STDERR.\n')
        sys.stdout.write('jojo_return_value JOB_STATUS=fail\n')
        traceback.print_exc(file=sys.stderr)
        sys.exit(253)
    stream.close()

def return_artifact_servers():
    stream = open(configfile, 'r')
    try:
        return yaml.load(stream)['artifactservers'][var_environment]
    except KeyError:
        sys.stdout.write('jojo_return_value ERROR_MESSAGE=Missing ARTIFACTSERVER key lookup in yaml file. Look for keyerror in STDERR.\n')
        sys.stdout.write('jojo_return_value JOB_STATUS=fail\n')
        traceback.print_exc(file=sys.stderr)
        sys.exit(253)
    stream.close()


def send_artifact():
    """ Sends a file to the yum server of choice. """
    display(err.DEBUG,"Topfile.")

    # Use the `file` command to determine filetype of the file we're handling.
    display(err.INFO+"Attempting to validate if the LOCAL file is a valid rpm.")

    testfiletype=local('file '+var_file,capture=True)

    if "RPM" in testfiletype:
        display(err.INFO,"FILE is of type RPM...")
    else:
        execution_report("ERROR:: Your package is not an RPM",252)

    if "v3.0" in testfiletype:
        display(err.INFO,"FILE is of type RPM v3.0...")
    else:
        display(err.ERROR,"Your package is not a v3.0 RPM",251)

    if "pgp" not in testfiletype:
        if var_signed != "False":
            display(err.ERROR," Your package has no PGP signature.")
            execution_report("We enforce PGP signed RPMs. Your RPM is not signed!",250)
        else:
            display(err.WARN,"Your package has no PGP signature.")

    # Now make sure the RPM's md5sum matches inside of the .rpm file using `rpm` command.
    display(err.INFO,"Attempting to validate RPM files md5sum...")
    rpmchecksig=local('/bin/rpm --nosignature --checksig '+var_file,capture=True)
    print rpmchecksig
    if "md5 OK" in rpmchecksig:
        display(err.INFO,"FILE md5sum OK...")
    else:
        execution_report("File reference fails RPM md5sum check.",249)

    # Upload the file
    display(err.INFO,"Attempting transmit of file to file server.")
    put(var_file,'/srv/repo/')

    # List remote directory contents
    display(err.INFO,"Looking at remote file list.")
    run('ls -la /srv/repo/')

    execution_report("File transfer to <hostname> success!",0)

print "repo_servers" + str(return_repo_servers())
print "artifact_servers" + str(return_artifact_servers())

for server in return_artifact_servers():
    execute(send_artifact, hosts=["root@"+server])
