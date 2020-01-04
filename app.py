#!/usr/bin/env python3
import os
import yaml

from aws_cdk import core

from deploy.deploy_stack import DeployStack

if os.path.isfile(os.path.join(os.getcwd(), '..', 'config.yml'):
    config_path = os.path.join(os.getcwd(), '..', 'config.yml')
elif os.path.isfile(os.path.join(os.getcwd(), 'config.yml'):
    config_path = os.path.join(os.getcwd(), 'config.yml')
else:
    print("Could not find config.yml")
    os.exit(1)

config = dict()
with open(config_path) as f_config:
    config = yaml.load(config_file_handle, Loader=yaml.FullLoader)

env = {'account': os.getenv('AWS_ACCOUNT', os.getenv('CDK_DEFAULT_ACCOUNT', '')),
       'region': 'us-east-1'}

app = core.App()
DeployStack(app, config.get("stack_name"), env=env, config=config)

app.synth()