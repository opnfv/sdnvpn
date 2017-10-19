#!/bin/python
#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#

import logging
import os

from keystoneauth1 import loading
from keystoneauth1 import session
from novaclient import client as novaclient
from neutronclient.neutron import client as neutronclient

logger = logging.getLogger(__name__)

DEFAULT_API_VERSION = '2'

# *********************************************
#   CREDENTIALS
# *********************************************


class MissingEnvVar(Exception):

    def __init__(self, var):
        self.var = var

    def __str__(self):
        return str.format("Please set the mandatory env var: {}", self.var)


def is_keystone_v3():
    keystone_api_version = os.getenv('OS_IDENTITY_API_VERSION')
    if (keystone_api_version is None or
            keystone_api_version == '2'):
        return False
    else:
        return True


def get_rc_env_vars():
    env_vars = ['OS_AUTH_URL', 'OS_USERNAME', 'OS_PASSWORD']
    if is_keystone_v3():
        env_vars.extend(['OS_PROJECT_NAME',
                         'OS_USER_DOMAIN_NAME',
                         'OS_PROJECT_DOMAIN_NAME'])
    else:
        env_vars.extend(['OS_TENANT_NAME'])
    return env_vars


def check_credentials():
    """
    Check if the OpenStack credentials (openrc) are sourced
    """
    env_vars = get_rc_env_vars()
    return all(map(lambda v: v in os.environ and os.environ[v], env_vars))


def get_env_cred_dict():
    env_cred_dict = {
        'OS_USERNAME': 'username',
        'OS_PASSWORD': 'password',
        'OS_AUTH_URL': 'auth_url',
        'OS_TENANT_NAME': 'tenant_name',
        'OS_USER_DOMAIN_NAME': 'user_domain_name',
        'OS_PROJECT_DOMAIN_NAME': 'project_domain_name',
        'OS_PROJECT_NAME': 'project_name',
        'OS_ENDPOINT_TYPE': 'endpoint_type',
        'OS_REGION_NAME': 'region_name',
        'OS_CACERT': 'https_cacert',
        'OS_INSECURE': 'https_insecure'
    }
    return env_cred_dict


def get_credentials(other_creds={}):
    """Returns a creds dictionary filled with parsed from env
    """
    creds = {}
    env_vars = get_rc_env_vars()
    env_cred_dict = get_env_cred_dict()

    for envvar in env_vars:
        if os.getenv(envvar) is None:
            raise MissingEnvVar(envvar)
        else:
            creds_key = env_cred_dict.get(envvar)
            creds.update({creds_key: os.getenv(envvar)})

    if 'tenant' in other_creds.keys():
        if is_keystone_v3():
            tenant = 'project_name'
        else:
            tenant = 'tenant_name'
        other_creds[tenant] = other_creds.pop('tenant')

    creds.update(other_creds)

    return creds


def get_session_auth(other_creds={}):
    loader = loading.get_plugin_loader('password')
    creds = get_credentials(other_creds)
    auth = loader.load_from_options(**creds)
    return auth


def get_session(other_creds={}):
    auth = get_session_auth(other_creds)
    https_cacert = os.getenv('OS_CACERT', '')
    https_insecure = os.getenv('OS_INSECURE', '').lower() == 'true'
    return session.Session(auth=auth,
                           verify=(https_cacert or not https_insecure))


def get_nova_client_version():
    api_version = os.getenv('OS_COMPUTE_API_VERSION')
    if api_version is not None:
        logger.info("OS_COMPUTE_API_VERSION is set in env as '%s'",
                    api_version)
        return api_version
    return DEFAULT_API_VERSION


def get_neutron_client_version():
    api_version = os.getenv('OS_NETWORK_API_VERSION')
    if api_version is not None:
        logger.info("OS_NETWORK_API_VERSION is set in env as '%s'",
                    api_version)
        return api_version
    return DEFAULT_API_VERSION


def get_nova_client(other_creds={}):
    sess = get_session(other_creds)
    return novaclient.Client(get_nova_client_version(), session=sess)


def get_neutron_client(other_creds={}):
    sess = get_session(other_creds)
    return neutronclient.Client(get_neutron_client_version(), session=sess)


def update_nw_subnet_port_quota(nw_quota, subnet_quota,
                                port_quota, tenant_id=None):
    json_body = {"quota": {
        "network": nw_quota,
        "subnet": subnet_quota,
        "port": port_quota
    }}

    try:
        get_neutron_client().update_quota(tenant_id=tenant_id,
                                          body=json_body)
        return True
    except Exception as e:
        logger.error("Error [update_nw_subnet_port_quota(neutron_client,"
                     " '%s', '%s', '%s', '%s')]: %s" %
                     (tenant_id, nw_quota, subnet_quota, port_quota, e))
        return False


def update_instance_quota_class(instances_quota):
    json_body = {"quota_class_set": {
        "instances": instances_quota
    }}

    try:
        get_nova_client().quota_classes.update("default", body=json_body)
        return True
    except Exception as e:
        logger.error("Error [update_instance_quota_class(nova_client,"
                     " '%s' )]: %s" % (instances_quota, e))
        return False
