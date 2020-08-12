
This is the CodeInstitute fork of OpenEDX.

It contains a Dockerfile geared towards creating a simple image that can be deployed in a cluster.
It also contains some extra apps written by CodeInstitute.


Developer Setup
---------------


Build docker image

Deploy locally using docker-compose
 - add www.myopenedx.com to /etc/hosts

Run tests

Debug local cluster

Development against local cluster


Cleaning up local data directories (./edxdata)


Breakdown of local dev services
-------------------------------

 - LMS
 - CMS
 - LMS Worker
 - CMS Worker
 - Nginx
 - MySql
 - MongoDB
 - Memcached
 - Elasticsearch
 - RabbitMQ
 - SMTP (Mailhog)
 - LMS DB Setup / Migrate task


