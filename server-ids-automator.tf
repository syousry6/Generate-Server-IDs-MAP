###################################################################################################################
# Filename   : main.tf
# Description    : Terraform Module to Generate the Server IDs for MAP| MAP-35
# Author     : Sherif ElTammimy
###################################################################################################################


################################################
# Creating resource variable
################################################

provider "aws" {
  region     = "us-east-1"
}

variable "function_name" {
    default = ""
}
variable "handler_name" {
    default = ""
}
variable "runtime" {
    default = ""
 }
variable "timeout" {
   default = ""
}

variable "handler_name_2" {
    default = ""
}

variable "function_create_name" {
    default = ""
}

variable "INPUT_BUCKET_NAME" {
  description = "Prefix for the bucket name. Note that this is used for AWS Migration Hub."
  default = "migration-hub-inventory-bucket"
}

variable "MPE" {
  type        = string
  description = "Contact your AWS account team, or check your MAP agreement."
  default = "MPE09872"
}

variable "S3Region" {
  type        = string
  description = "Select a region for inventroy upload to AWS Migration Hub."
  default = "us-east-1"
}


###############################################
# fetching current account id
###############################################

data "aws_caller_identity" "current" {}



###############################################
# defining data blocks
###############################################

data "archive_file" "zipit" {
  type        = "zip"
  source_file = "${var.handler_name}/${var.handler_name}.py"
  output_path = "${var.handler_name}.zip"
}


data "archive_file" "zipit_create" {
  type        = "zip"
  output_path = "${var.handler_name_2}.zip"
  source_dir  = "${path.module}/folder_creation_lambda_function_v2"
}

#
#  user_data                 = data.template_file.user_data.rendered
#}
#
#data "template_file" "user_data" {
#emplate = "${file("${path.module}/folder_creation_lambda_function_v2/folder_creation_lambda_function_v2.py")}"
#}

data "aws_lambda_invocation" "example" {
  function_name = aws_lambda_function.map_lambda_create_folder.function_name
  input = <<JSON
{
  "key1": "value1",
  "key2": "value2"
}
JSON
}

resource "aws_lambda_permission" "test" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.map_lambda.function_name}"
  principal = "s3.amazonaws.com"
  source_arn = aws_s3_bucket.migration-hub-inventory-bucket.arn
}


###############################################
# Creating Lambda resource 
###############################################

###############################################
# 1. Lambda function to be triggered by s3 once any csv has been uploaded
###############################################
resource "aws_lambda_function" "map_lambda" {
  function_name    = "${var.function_name}"
  role             = "${aws_iam_role.iam_for_lambda.arn}"
  handler          = "${var.handler_name}.lambda_handler"
  runtime          = "${var.runtime}"
  timeout          = "${var.timeout}"
  filename         = "${var.handler_name}.zip"
  source_code_hash = "${data.archive_file.zipit.output_base64sha256}"
  environment {
    variables = {
      AWS_MIGRATION_PROJECT_ID = "${var.MPE}"
      S3_REGION = "${var.S3Region}"
      AWS_ACCOUNT_ID = "${data.aws_caller_identity.current.account_id}"
    }
  }
}


###############################################
# 2. Lambda function to create Lambda function for Input folder creation
###############################################
resource "aws_lambda_function" "map_lambda_create_folder" {
  function_name    = "${var.function_create_name}"
  role             = "${aws_iam_role.iam_for_lambda.arn}"
  handler          = "${var.handler_name_2}.lambda_handler"
  runtime          = "${var.runtime}"
  timeout          = "${var.timeout}"
  filename         = "${var.handler_name_2}.zip"
  source_code_hash = "${data.archive_file.zipit_create.output_base64sha256}"
  environment {
    variables = {
      INPUT_BUCKET_NAME = "${var.INPUT_BUCKET_NAME}-${data.aws_caller_identity.current.account_id}"
      INPUT_FOLDER = "Upload-Your-Inventory-In-This-Folder"
    }
  }
}


##############################################################################################
#Create policy documents for assume role and s3 permissions
##############################################################################################
data "aws_iam_policy_document" "iam_for_lambda" {
  statement {
    actions = [
      "sts:AssumeRole",
    ]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}


data "aws_iam_policy_document" "s3_lambda" {
  statement {
    actions = [
      "s3:*"
    ]

    resources = [
      "${aws_s3_bucket.migration-hub-inventory-bucket.arn}/*", 
      "${aws_s3_bucket.migration-hub-inventory-bucket.arn}"
    ]
  }
}

#Create a role
resource "aws_iam_role" "iam_for_lambda" {
  name               = "role_for_lambda"
  assume_role_policy = data.aws_iam_policy_document.iam_for_lambda.json
}




#Create an IAM policy
resource "aws_iam_policy" "iam_policy_for_lambda_s3" {
 name = "s3_lambda_policy"
 description = "s3 lambda policy"
 policy      = data.aws_iam_policy_document.s3_lambda.json
}


#Attach IAM Role and the new created Policy
resource "aws_iam_role_policy_attachment" "s3-lambda-attach" {
  role       = "${aws_iam_role.iam_for_lambda.name}"
  policy_arn = "${aws_iam_policy.iam_policy_for_lambda_s3.arn}"
}


resource "aws_iam_policy" "lambda_logging" {
  name        = "lambda_logging"
  path        = "/"
  description = "IAM policy for logging from a lambda"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*",
      "Effect": "Allow"
    }
  ]
}
EOF
}



#Attach IAM Role and the new created Policy for cloudwatch
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = "${aws_iam_role.iam_for_lambda.name}"
  policy_arn = "${aws_iam_policy.lambda_logging.arn}"
}

#New_policies
resource "aws_iam_role_policy_attachment" "lambda_role_1" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.iam_for_lambda.name
}
resource "aws_iam_role_policy_attachment" "lambda_role_2" {
  policy_arn = "arn:aws:iam::aws:policy/AWSCodeDeployDeployerAccess"
  role       = aws_iam_role.iam_for_lambda.name
}
resource "aws_iam_role_policy_attachment" "lambda_role_3" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonSNSFullAccess"
  role       = aws_iam_role.iam_for_lambda.name
}


################################################################
# Creating s3 resource for invoking to lambda function
################################################################
resource "aws_s3_bucket" "migration-hub-inventory-bucket" {
  bucket = "${var.INPUT_BUCKET_NAME}-${data.aws_caller_identity.current.account_id}"
  acl    = "private"

  versioning {
    enabled = true
  }
}


##################################################################################
# Adding S3 bucket as trigger to my lambda and giving the permissions
##################################################################################
resource "aws_s3_bucket_notification" "aws-lambda-trigger" {
  bucket = "${aws_s3_bucket.migration-hub-inventory-bucket.id}"
  lambda_function {
    lambda_function_arn = "${aws_lambda_function.map_lambda.arn}"
    events              = ["s3:ObjectCreated:*"]
}
  depends_on = [aws_lambda_permission.test]
}


###########################################################################
# output of lambda arn
###########################################################################
output "arn" {

value = "${aws_lambda_function.map_lambda.arn}"

}


data "aws_region" "current" {
}
