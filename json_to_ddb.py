import json

from boto3.dynamodb.types import TypeSerializer

serializer = TypeSerializer()
data = json.load(open("to_ddb.json", encoding="utf-8"))
json.dump({k: serializer.serialize(v) for k, v in data.items()}, open("as_ddb.json", "w+"))
