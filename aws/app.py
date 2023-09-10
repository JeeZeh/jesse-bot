#!/usr/bin/env python3
import aws_cdk as cdk
from common.constants import AWS_ACCOUNT

from aws.bot_stack import JesseBotStack

app = cdk.App()
JesseBotStack(
    app,
    "JesseBot",
    env=cdk.Environment(account=AWS_ACCOUNT, region="eu-west-1"),
)

app.synth()
