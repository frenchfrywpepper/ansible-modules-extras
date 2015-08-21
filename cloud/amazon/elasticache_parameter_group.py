#!/usr/bin/python
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: elasticache_parameter_group
version_added: "2.0"
short_description: manage Elasticache parameter groups
description:
     - Creates, modifies, and deletes Elasticache parameter groups. This module has a dependency on python-boto >= 2.5.
options:
  state:
    description:
      - Specifies whether the parameter group should be present or absent.
    required: true
    default: present
    choices: [ 'present' , 'absent' ]
  name:
    description:
      - Database parameter group identifier.
    required: true
  description:
    description:
      - Elasticache parameter group description. Only set when a new group is added.
    required: false
    default: null
  cache_parameter_group_family:
    description:
      - The name of the cache parameter group family the cache parameter group can be used with.
    required: false
    choices: [ 'memcached1.4, 'redis2.6', 'redis2.8' ]
  parameter_name_values:
    description:
      - An array of parameter names and values for the parameter update. You must supply at least one parameter name and value; subsequent arguments are optional. A maximum of 20 parameters may be modified per request.
    required: false
  region:
    description:
      - The AWS region to use. If not specified then the value of the AWS_REGION or EC2_REGION environment variable, if any, is used.
    required: true
    aliases: ['aws_region', 'ec2_region']
author: "Sarah Haskins (@sarahhaskins)"
extends_documentation_fragment: aws
'''

EXAMPLES = '''
# Add or change a parameter group
- elasticache_parameter_group
    state: present
    name: redis_2.8_lru
    description: My Fancy Parameter Group
    cache_parameter_group_family: redis2.8

# Remove a parameter group
- elasticache_parameter_group:
    state: absent
    name: redis_2.8_lru
    parameter_name_values:
        -
            - 'activerehashing'
            - 'yes'
'''

try:
    import boto
    from boto.elasticache.layer1 import ElastiCacheConnection
    from boto.regioninfo import RegionInfo
    from boto.exception import BotoServerError
    HAS_BOTO = True
except ImportError:
    HAS_BOTO = False

def main():
    argument_spec = ec2_argument_spec()
    argument_spec.update(dict(
        state=dict(required=True, choices=['present', 'absent'], type='str'),
        name=dict(required=True, type='str'),
        description=dict(required=False, type='str'),
        cache_parameter_group_family=dict(required=False, choices=["memcached1.4", "redis2.6", "redis2.8"], type='str'),
        parameter_name_values=dict(required=False, type='list')
        )
    )
    module = AnsibleModule(argument_spec=argument_spec)

    if not HAS_BOTO:
        module.fail_json(msg='boto required for this module')

    state = module.params.get('state')
    group_name = module.params.get('name').lower()
    group_description = module.params.get('description')
    cache_parameter_group_family = module.params.get('cache_parameter_group_family')
    parameter_name_values = module.params.get('parameter_name_values')

    # when present, the group will be created or modified
    if state == 'present':
        for required in ['name', 'description']:
            if not module.params.get(required):
                module.fail_json(msg=str("Parameter %s required for state='present'" % required))
    # when absent, the group will be deleted
    else:
        for not_allowed in ['description', 'cache_parameter_group_family', 'parameter_name_values']:
            if module.params.get(not_allowed):
                module.fail_json(msg=str("Parameter %s not allowed for state='absent'" % not_allowed))

    # Retrieve any AWS settings from the environment.
    region, ec2_url, aws_connect_kwargs = get_aws_connection_info(module)

    if not region:
        module.fail_json(msg=str("Either region or AWS_REGION or EC2_REGION environment variable or boto config aws_region or ec2_region must be set."))

    """Get an elasticache connection"""
    try:
        endpoint = "elasticache.%s.amazonaws.com" % region
        connect_region = RegionInfo(name=region, endpoint=endpoint)
        conn = ElastiCacheConnection(region=connect_region, **aws_connect_kwargs)
    except boto.exception.NoAuthHandlerFound, e:
        module.fail_json(msg=e.message)

    try:
        changed = False
        exists = False

        try:
            matching_groups = conn.describe_cache_parameter_groups(group_name, max_records=100)
            exists = len(matching_groups) > 0
        except BotoServerError, e:
            if e.error_code != 'CacheParameterGroupNotFound':
                module.fail_json(msg = e.error_message)

        if state == 'absent':
            if exists:
                conn.delete_cache_parameter_group(group_name)
                changed = True
        else:
            if not exists:
                # if creating, cache_parameter_group_family is required
                for required in ['cache_parameter_group_family']:
                    if not module.params.get(required):
                        module.fail_json(
                            msg=str("Parameter %s required for state='present' and does not exist" % required))

                conn.create_cache_parameter_group(group_name, cache_parameter_group_family, group_description)
                changed = True
            else:
                # if creating, cache_parameter_group_family is required
                for required in ['parameter_name_values']:
                    if not module.params.get(required):
                        module.fail_json(msg=str("Parameter %s required for state='present' and exists" % required))
                conn.modify_cache_parameter_group(group_name, parameter_name_values)
                changed = True

    except BotoServerError, e:
        if e.error_message != 'No modifications were requested.':
            module.fail_json(msg=e.error_message)
        else:
            changed = False

    module.exit_json(changed=changed)

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.ec2 import *

main()
