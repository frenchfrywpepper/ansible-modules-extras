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

DOCUMENTATION = """
---
module: kinesis
short_description: Creates an AWS Kinesis stream
description:
  - Creates an AWS Kinesis stream
version_added: "2.0.0"
author: "Sarah Haskins (@sarahhaskins)"
options:
  name:
    description:
      - Name of the AWS Kinesis stream to be created
    required: true
  shard_count:
    description:
      - Number of shards
    required: true
extends_documentation_fragment: aws
"""

try:
    import boto3
    import botocore
    HAS_BOTO = True
except ImportError:
    HAS_BOTO = False


class KinesisManager:
    """Handles EC2 instance ELB registration and de-registration"""

    def __init__(self, module, name=None, shard_count=None, **aws_connect_params):
        self.module = module
        self.name = name
        self.shard_count = shard_count
        self.aws_connect_params = aws_connect_params
        self.changed = False
        self.kinesis = self._get_connection()

    def create(self):
        """Creates the Kinesis stream if it does not already exist"""
        if self.exists():
            self.changed = False
        else:
            try:
                self.kinesis.create_stream(StreamName=self.name, ShardCount=self.shard_count)
                self.changed = True
            except(botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError, StandardError), e:
                self.module.fail_json(msg=str(e))

    def exists(self):
        """Checks if the stream by that name already exists"""
        try:
            self.kinesis.describe_stream(StreamName=self.name)
            return True
        except(botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError, StandardError), e:
            self.module.fail_json(msg=str(e))

    def _get_connection(self):
        """Returns a boto3 service client instance"""
        try:
            return boto3.client('kinesis')
        except (botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError, StandardError), e:
            self.module.fail_json(msg=str(e))


def main():
    argument_spec = aws_common_argument_spec()
    argument_spec.update(dict(
        name={'required': True},
        shard_count={'required': True, 'type': 'int'}
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
    )

    if not HAS_BOTO:
        module.fail_json(msg='boto required for this module')

    region, ec2_url, aws_connect_params = get_aws_connection_info(module, boto3=True)

    name = module.params['name']
    shard_count = module.params['shard_count']

    kinesis_man = KinesisManager(module, name, shard_count,
                         **aws_connect_params)

    kinesis_man.create()
    ansible_facts = {'name': name}
    facts_result = dict(changed=kinesis_man.changed, ansible_facts=ansible_facts)

    module.exit_json(**facts_result)

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.ec2 import *

main()
