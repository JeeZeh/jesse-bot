from aws_cdk import Stack
from aws_cdk import aws_dynamodb as ddb
from aws_cdk import aws_iam as iam
from constructs import Construct


class JesseBotStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        db = ddb.Table(
            self,
            "JesseBotDB",
            read_capacity=2,
            write_capacity=2,
            table_name="jesse-bot-db",
            partition_key=ddb.Attribute(name="id", type=ddb.AttributeType.STRING),
            deletion_protection=True,
        )

        dev_db = ddb.Table(
            self,
            "JesseBotDB-Dev",
            read_capacity=1,
            write_capacity=1,
            table_name="jesse-bot-db-dev",
            partition_key=ddb.Attribute(name="id", type=ddb.AttributeType.STRING),
            deletion_protection=True,
        )

        jesse_bot_user = iam.User(self, "JesseBotUser", user_name="jesse-bot-user")

        db.grant_read_write_data(jesse_bot_user)
        dev_db.grant_read_write_data(jesse_bot_user)
