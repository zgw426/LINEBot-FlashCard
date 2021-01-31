import boto3
import json

# jsonデータ読み込み
json_open = open('data.json', 'r')
json_load = json.load(json_open)

# DynamoDB接続
table_name = 'questions'
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(table_name)

def putdataToDynamoDB( item ):
    response = table.put_item(
        TableName=table_name,
        Item=item
    )


for quest in json_load["Items"]:
    item = {
        "Q": quest["Q"],
        "img": quest["img"],
        "put_date": quest["put_date"],
        "userid": quest["userid"],
        "category": quest["category"],
        "by_at": quest["by_at"],
        "NG1": quest["NG1"],
        "NG2": quest["NG2"],
        "OK": quest["OK"]
    }
    putdataToDynamoDB( item )
