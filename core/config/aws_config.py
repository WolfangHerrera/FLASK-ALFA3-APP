import boto3
from botocore.exceptions import ClientError


def getSession():
   return boto3.resource(
       'dynamodb',
       aws_access_key_id='',
       aws_secret_access_key='',
       region_name='us-east-1'
   )


def createTable():
    dynamodb = getSession()
    table = dynamodb.create_table(
        TableName='items',
        KeySchema=[
            {
                'AttributeName': 'item_id',
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'item_id',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    return table
