import os
import csv
import time
import boto3
import zipfile
import urllib.request
from datetime import datetime


def lambda_handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        print('bucket -> ', bucket)
        key = record['s3']['object']['key']
        print('key -> ', key)
        file_name = key.split('/')[1]
        print('file_name -> ', file_name)

    obj = MigrationManager()
    obj.start_function(bucket, file_name)


class MigrationManager:

    def __init__(self):     
        self.AWS_MIGRATION_PROJECT_ID = os.environ['AWS_MIGRATION_PROJECT_ID']
        self.S3_REGION = os.environ['S3_REGION']
        self.AWS_ACCOUNT_ID = os.environ['AWS_ACCOUNT_ID']
        self.INPUT_BUCKET_NAME = ""
        self.OUTPUT_BUCKET_NAME = ""        
        self.INPUT_FOLDER = "Upload-Your-Inventory-In-This-Folder"
        self.FORMATTED_FOLDER = "FormattedFiles"
        self.OUTPUT_FOLDER = "OutputFiles"
        
    def start_function(self, bucket, input_file=''): 
        self.INPUT_BUCKET_NAME = bucket
        self.OUTPUT_BUCKET_NAME = bucket
        try:
            status = self.update_input_file(input_file)
            if status == 'success':
                formatted_file_name = input_file.split('.')[0] + '_formated.csv'
                #url = 'https://eb-map-bucket.s3.amazonaws.com/Input/import_template_1.csv'
                file_url = 'https://{0}.s3.amazonaws.com/{1}'.format(self.OUTPUT_BUCKET_NAME, 
                                self.FORMATTED_FOLDER + '/' + formatted_file_name)
                import_name = 'import {0}'.format(datetime.now().strftime('%Y-%m-%d_%H:%M:%S'))

                client = boto3.client('migrationhub-config')
                try:
                    response = client.create_home_region_control(
                                    HomeRegion=self.S3_REGION,
                                    Target={
                                        'Type': 'ACCOUNT',
                                        'Id': self.AWS_ACCOUNT_ID
                                    }
                                )
                    print (response)
                except Exception as e:
                    print (e)
                    response = client.get_home_region()
                    print(response)

                client = boto3.client('discovery')

                # import
                self.call_import_task(client, file_url, import_name)
                time.sleep(20) # wait ....
                                
                # export
                export_id = self.call_export_task(client)
                
                # check export status and get exported file url
                exported_file_url = self.get_exported_file_url(client, export_id)                

                if exported_file_url:                                    
                    self.unzip_and_move_exported_file(exported_file_url, import_name)
                else:
                    print ("Some error occurred. Couldn't get the exported file url")
            else:
                print ("Some error occurred while formatting the input file")
        except Exception as e:
            error = "Error in start_function: {0}".format(e)
            print(error)

    def update_input_file(self, input_file):
        status = 'failure'
        try:                
            file_content = self.read_s3_file(input_file, self.INPUT_FOLDER, self.INPUT_BUCKET_NAME)
            file_content = file_content.decode("utf-8")
            file_content = file_content.split('\n')
            csv_data = csv.DictReader(file_content)
            with open('/tmp/temp.csv', 'w', newline='\n') as csvfile:
                fieldnames = file_content[0][:-1].split(',')
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in csv_data:
                    row['Tags'] = 'aws-migration-project-id:' + self.AWS_MIGRATION_PROJECT_ID
                    writer.writerow(row)
            csv_binary = open('/tmp/temp.csv', 'rb').read()
            
            s3 = boto3.resource('s3')
            bucket = s3.Bucket(self.OUTPUT_BUCKET_NAME)
            formatted_file_name = input_file.split('.')[0] + '_formated.csv'
            key = self.FORMATTED_FOLDER + '/' + formatted_file_name
            bucket.upload_file('/tmp/temp.csv', key)         
            
            status = 'success'
        except Exception as e:
            error = "Error in update_input_file: {0}".format(e)
            print (error)
        finally:
            return status

    def read_s3_file(self, file_name, key='', bucket=''):
        file_content = None
        try:
            s3 = boto3.resource('s3')
            if key:
                key = key + '/' + file_name
            else:
                key = file_name
            obj = s3.Object(bucket, key)
            file_content = obj.get()['Body'].read()
        except Exception as e:
            error = "Error in read_s3_file: {0}".format(e)
            print (error)
        finally:
            return file_content

    def call_import_task(self, client, file_url, import_name):
        try:
            response = client.start_import_task(
                            name=import_name,
                            importUrl=file_url
                        )
            print ('Import response:')
            print (response)
        except Exception as e:
            error = "Error in call_import_task: {0}".format(e)
            print (error)

    def call_export_task(self, client):
        export_id = None
        try:
            response = client.start_export_task(exportDataFormat=['CSV'])
            print ('Export response:')
            print (response)

            export_id = response.get('exportId')
            print ('export_id:')
            print (export_id)
        except Exception as e:
            error = "Error in call_export_task: {0}".format(e)
            print (error)  
        finally:
            return export_id   

    def get_exported_file_url(self, client, export_id):
        exported_file_url = None
        WAIT_TIME = 3 # seconds
        try:
            time.sleep(1) # wait 1 second
            export_ids = [export_id]            
            while True:
                # check export status
                response = client.describe_export_tasks(exportIds=export_ids)
                print ('Export status:')
                print (response)
                export_status = response.get('exportsInfo')[0]['exportStatus']
                if export_status == 'SUCCEEDED':
                    exported_file_url = response.get('exportsInfo')[0]['configurationsDownloadUrl']
                    break
                else:
                    print ('waiting {0} seconds..'.format(WAIT_TIME))
                    time.sleep(WAIT_TIME) # wait 3 seconds   
        except Exception as e:
            error = "Error in get_exported_file_url: {0}".format(e)
            print (error)  
        finally:
            print ('exported_file_url:')
            print (exported_file_url)
            return exported_file_url 

    def unzip_and_move_exported_file(self, exported_file_url, import_name):
        try:            
            s3_client = boto3.client('s3')
            temp_zip = '/tmp/file.zip'
            urllib.request.urlretrieve (exported_file_url, temp_zip)
            zfile = zipfile.ZipFile(temp_zip)
            print ('zfile:')
            print (zfile)

            file_list = [( name, 
                           '/tmp/' + os.path.basename(name),
                           self.OUTPUT_FOLDER + os.path.basename(name)) 
                            for name in zfile.namelist()]
            print ('file_list:')
            print (file_list)
            print("got names {}".format("; ".join([n for n,b,d in file_list])))

            for file_name, local_path, s3_key in file_list:
                data = zfile.read(file_name)
                with open(local_path, 'wb') as f:
                    f.write(data)
                    del(data) # free up some memory

                s3_client.upload_file(local_path, self.OUTPUT_BUCKET_NAME, self.OUTPUT_FOLDER+'/'+import_name+'/'+s3_key)
                os.remove(local_path)

            #result = {"files": ['s3://' + self.OUTPUT_BUCKET_NAME + '/' + s for f,l,s in file_list]}
            print ('''Successfully unzipped and moved exported files to {0}/{1}/{2}/
                '''.format(self.OUTPUT_BUCKET_NAME, self.OUTPUT_FOLDER, import_name))
        except Exception as e:
            error = "Error in unzip_and_move_exported_file: {0}".format(e)
            print (error)          
