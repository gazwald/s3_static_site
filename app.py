#!/usr/bin/env python3
import os
import sys
import yaml

from aws_cdk import core

from deploy.deploy_stack import DeployStack

path1 = os.path.join(os.getcwd(), "..", "config.yml")
path2 = os.path.join(os.getcwd(), "config.yml")

if os.path.isfile(path1):
    config_path = path1
elif os.path.isfile(path2):
    config_path = path2
else:
    print("Could not find config.yml")
    sys.exit(1)

config = dict()
with open(config_path) as f_config:
    config = yaml.load(f_config, Loader=yaml.FullLoader)

env = {"account": os.getenv("AWS_ACCOUNT", os.getenv("CDK_DEFAULT_ACCOUNT", "")),
       "region": config.get('region', 'us-east-1')}

app = core.App()
DeployStack(app, config.get("stack_name"), env=env, config=config)

app.synth()
