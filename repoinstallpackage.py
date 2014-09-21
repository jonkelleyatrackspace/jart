#!/usr/bin/python

# -- jojo --
# description: The purpose of this script is to retrieve a package from the artifact server and update the local repository.
# param: artifact  - The RPM artifact you wish to retrieve [myfile.rpm]. (REQUIRED)
# param: release - What Redhat release to put this file in [5,6,7] (REQUIRED)
# param: arch - The architecture you wish to put this file in [x86_64,noarch,x86] (REQUIRED)
# param: environment - Input validate check they know what producty they mean to update.
# param: datacenter - Input validate check what datacenter they want to use.
# param: tier - Input validate check what tier they are using.
# param: signed - Determine if strict sign checking should be used for the package. Default assume TRUE.
# http_method: post
# lock: False
# -- jojo -- 

# Example repository file layout:
# /srv/repo/unsigned/7/x86_64/atomhopper/
# /srv/repo/unsigned/7/noarch/atomhopper/
# /srv/repo/unsigned/7/x86_64/shared/
# /srv/repo/unsigned/7/noarch/shared/

import sys, os, yaml, traceback
from fabric.api import env, local, get, run, settings
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
    print "************  >>" + err + "<< " + text

def return_repository_settings():
    """ Retrieves the artifact repository settings from YaML configuration. """
    stream = open(configfile, 'r')
    try:
        config = yaml.load(stream)['repo_server_settings']
        add_yaml_key_if_not_exists = config['environment']
        add_yaml_key_if_not_exists = config['tier']
        add_yaml_key_if_not_exists = config['datacenter']
        add_yaml_key_if_not_exists = config['artifact_server']
        return config
    except KeyError:
        sys.stdout.write('jojo_return_value ERROR_MESSAGE=Missing repo_server_settings key value, an exception will reveal soon.\n')
        sys.stdout.write('jojo_return_value JOB_STATUS=fail\n')
        traceback.print_exc(file=sys.stderr)
        sys.exit(253)
    stream.close()

settings = return_repository_settings()

# Get parameters.
var_file        = bash_real_escape_string(os.environ.get('ARTIFACT'))
var_arch        = bash_real_escape_string(os.environ.get('ARCH'))
var_environment = bash_real_escape_string(os.environ.get('ENVIRONMENT'))
var_datacenter  = bash_real_escape_string(os.environ.get('DATACENTER'))
var_tier        = bash_real_escape_string(os.environ.get('TIER'))
var_release        = bash_real_escape_string(os.environ.get('RELEASE'))

var_signed      = bash_real_escape_string(os.environ.get('SIGNED'))
if settings['only_allow_signed_packages'] == "True": var_signed = "True" # Force package sign override.

# Don't let script continue without these parameters.
halt_if_value_empty(var_file,'artifact')
halt_if_value_empty(var_environment,'environment')
halt_if_value_empty(var_datacenter,'datacenter')
halt_if_value_empty(var_tier,'tier')
halt_if_value_empty(var_file,'arch')
halt_if_value_empty(var_file,'release')
secure_designator = "unsigned"

""" Checks user to make sure they know what they are talking to """
if var_environment != settings['environment']:
    execution_report("WRONG ENVIRONMENT. You provided: "+var_environment+" This is:" + settings['environment'],99)
if var_datacenter != settings['datacenter']:
    execution_report("WRONG DATACENTER. You provided: "+var_datacenter+" This is:" + settings['datacenter'],99)
if var_tier != settings['tier']:
    execution_report("WRONG TIER. You provided: "+var_tier+" This is:" + settings['tier'],99)


def get_artifact():
    """ Retrieves an artifact from the artifact server. """
    target_hostname = run('hostname -f')
    display(err.INFO,"------------------------------------------")
    display(err.INFO,"STARTING artifact download from host " + target_hostname + " ("+env.host +")")
    get(remote_path='/srv/incoming/'+var_file,local_path='/srv/repo/'+secure_designator+'/'+var_release+'/'+var_arch+'/'+var_environment+'/'+var_file)



execute(get_artifact, hosts=["root@"+settings['artifact_server'] ])
#execution_report("File transfer to "+str(servers)+" success!",0)

