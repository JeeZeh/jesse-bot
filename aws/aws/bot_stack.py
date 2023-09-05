from aws_cdk import (
    RemovalPolicy,
    Stack,
    aws_s3 as s3,
    aws_iam as iam,
    aws_dynamodb as ddb,
)
from constructs import Construct
from common.constants import AWS_ACCOUNT


class JesseBotStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        storage_bucket = s3.Bucket(
            self,
            "Storage",
            bucket_name=f"jesse-bot-storage-{AWS_ACCOUNT}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            auto_delete_objects=False,
            removal_policy=RemovalPolicy.RETAIN,
        )

        db = ddb.Table(
            self,
            "JesseBotDB",
            read_capacity=5,
            write_capacity=5,
            table_name="jesse-bot-db",
            partition_key=ddb.Attribute(name="entry_type", type=ddb.AttributeType.STRING),
            deletion_protection=True,
        )

        jesse_bot_role = iam.Role(
            self, "AccessRole", role_name="jesse-bot-role", assumed_by=iam.AccountPrincipal(AWS_ACCOUNT)
        )
        jesse_bot_user = iam.User(self, "User", user_name="jesse-bot-user")

        jesse_bot_role.grant_assume_role(jesse_bot_user)

        storage_bucket.grant_read_write(jesse_bot_role)
        db.grant_read_write_data(jesse_bot_role)
