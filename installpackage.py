#!/usr/bin/python

# -- jojo --
# description: The purpose of this script is to retrieve a package from the artifact server and update the local repository.
# param: artifact  - The RPM artifact you wish to retrieve [myfile.rpm]. (REQUIRED)
# param: release - What Redhat release to put this file in [5,6,7] (REQUIRED)
# param: arch - The architecture you wish to put this file in [x86_64,noarch,x86] (REQUIRED)
# param: environment - What environment do you want to put this in [signup,atomhopper,shared] (REQUIRED)
# param: datacenter - The datacenter to contact [ord,dfw,all] (REQUIRED)
# param: tier - The tier of service to contact [dev,staging,test,prod,stable] (REQUIRED)
# param: signed - If the package should go in the signed or unsigned repository
# http_method: post
# lock: False
# -- jojo -- 

# Example repository file layout:
# /srv/repo/unsigned/7/x86_64/atomhopper/
# /srv/repo/unsigned/7/noarch/atomhopper/
# /srv/repo/unsigned/7/x86_64/shared/
# /srv/repo/unsigned/7/noarch/shared/

#####################################################
# Here should go an api client
#####################################################