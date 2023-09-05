from aws_cdk import (
    # Duration,
    RemovalPolicy,
    Stack,
    aws_s3 as s3,
)
from constructs import Construct
from common.constants import AWS_ACCOUNT


class AwsStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        s3.Bucket(
            self,
            "JesseBotStorage",
            bucket_name=f"jesse-bot-storage-{AWS_ACCOUNT}",
            block_public_access=True,
            auto_delete_objects=False,
            removal_policy=RemovalPolicy.RETAIN,
        )
