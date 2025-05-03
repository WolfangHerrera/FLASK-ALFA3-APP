import boto3
import os
from botocore.exceptions import ClientError


def getSession():
   return boto3.resource(
       'dynamodb',
       aws_access_key_id=os.environ.get('ACCESS_KEY', 'NOTHINGTOSEEHERE'),
       aws_secret_access_key=os.environ.get('ACCESS_SECRET_KEY', 'NOTHINGTOSEEHERE'),
       region_name='us-east-1'
   )

def createTable(tableName: str, keyName: str):
    dynamodb = getSession()
    table = dynamodb.create_table(
        TableName=tableName,
        KeySchema=[
            {
                'AttributeName': keyName,
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': keyName,
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    return table


def createTableGSI(tableName: str, keyName: str, gsiName: str, gsiKeyName: str):
    dynamodb = getSession()
    
    table = dynamodb.create_table(
        TableName=tableName,
        KeySchema=[
            {
                'AttributeName': keyName,
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': keyName,
                'AttributeType': 'S'
            },
            {
                'AttributeName': gsiKeyName,
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        },
        GlobalSecondaryIndexes=[
            {
                'IndexName': gsiName,
                'KeySchema': [
                    {
                        'AttributeName': gsiKeyName,
                        'KeyType': 'HASH'
                    }
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        ]
    )
    
    return table

