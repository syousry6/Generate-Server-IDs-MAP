# MAP-35
Terraform Module to Generate the Server IDs for MAP Project.


#### Terraform Resources

- 2 * IAM Policy Documents
- S3 Bucket
- 2 * Lambda

#### A top-level directory layout
    .
    ├── folder_creation_lambda_function_v2        
    |── lambda_function_v2
    ├── server-ids-automator.tf                
    ├── README.md    
    |__ terraform.tfvars
         


## Supported terraform resources

### aws_lambda_function
* map_lambda: Lambda function to be triggered by s3 once any csv has been uploade, It creates MAPLambdaFunction with lambda_function_v2 Handler.

There are 3 environment variables should passsed to this lambda functions:
1. AWS_MIGRATION_PROJECT_ID
2. S3_REGION
3. AWS_ACCOUNT_ID


### aws_lambda_function
* map_lambda_create_folder: Lambda function for the Input folder creation, It creates MAPLambdaFunctionCreate with folder_creation_lambda_function_v2 Handler.

There are 2 environment variables should passsed to this lambda functions:
1. INPUT_BUCKET_NAME
2. INPUT_FOLDER


### aws_s3_bucket
* migration-hub-inventory-bucket: s3 resource for invoking to lambda function where you will upload the CSV file with on-premises inventory.


### aws_s3_bucket_notification
* aws-lambda-trigger: Add S3 bucket as trigger to my lambda and giving the permissions.


## Terraform Versions

Terraform 0.13 and newer. Pin module version to ~> 4.x. Submit pull-requests to master branch.

Terraform 0.12. Pin module version to ~> 3.0. Submit pull-requests to terraform012 branch.

## Usage

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 0.12.7 |
| aws | >= 2.70 |
| template | >= 2.0 |

## Providers

| Name | Version |
|------|---------|
| aws | >= 2.70 |
| template | >= 2.0 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| INPUT\_BUCKET\_NAME |Prefix for the bucket name. Note that this is used for AWS Migration Hub| `string`  | `migration-hub-inventory-bucket` | yes |
| MPE | Contact your AWS account team, or check your MAP agreemen | `string`  | `MPE09872` | yes |
| S3Region | Select a region for inventroy upload to AWS Migration Hub. | `string`  | `us-east-1` | yes |

