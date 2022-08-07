import json
import boto3
import json
from decimal import Decimal

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    json_file_name = event['Records'][0]['s3']['object']['key']
    json_object = s3_client.get_object(Bucket=bucket,Key=json_file_name)
    jsonDict = json.loads(json_object['Body'].read(),parse_float=Decimal)
    table = dynamodb.Table('yelp-restaurant')
    table.put_item(Item=jsonDict)
    
    
    #original 
    sns = boto3.client('sns')
    for rec in event["Records"]:
        payload = json.loads(rec["body"])
        print("Received:", payload)
        
        #sql to call from database
        
        cuisine = payload["Cuisine"]
        phone = payload["Phone"]
        snsResult = sns.publish(PhoneNumber=f"+1{phone}", Message=f"Dear customer, we have recommanded a restaurant for you. Try: {cuisine}")
        print("SNS:", snsResult)
    return True
