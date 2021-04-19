import os
import time
import json
import boto3
import cfnresponse


def lambda_handler(event, context):
    obj = LambdaManager()
    obj.start_function()
    try:
        responseData = {}
        cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData)
    except Exception as e:
        print (e)


class LambdaManager:

    def __init__(self):
        self.INPUT_BUCKET_NAME = os.environ['INPUT_BUCKET_NAME']
        self.INPUT_FOLDER = os.environ['INPUT_FOLDER']
        
    def start_function(self):
        try:
            time.sleep(30)
            s3 = boto3.client('s3')
            s3.put_object(Bucket=self.INPUT_BUCKET_NAME, Key=(self.INPUT_FOLDER+'/'))
        except Exception as e:
            error = "Error in start_function: {0}".format(e)
            print(error)      