#!/usr/bin/env python3
import os

import aws_cdk as cdk

from aws.aws_stack import AwsStack

app = cdk.App()
AwsStack(
    app,
    "JesseBot",
    env=cdk.Environment(account=AWS_ACCOUNT, region="eu-west-1"),
)

app.synth()
