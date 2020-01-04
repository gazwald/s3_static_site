#!/usr/bin/env python3
import os

from aws_cdk import core

from deploy.deploy_stack import DeployStack

env = {'account': os.getenv('AWS_ACCOUNT', os.getenv('CDK_DEFAULT_ACCOUNT', '')),
       'region': 'us-east-1'}

app = core.App()
DeployStack(app, "MelGazwaldCom", env=env)

app.synth()
