import os
import boto3
from botocore.client import Config

AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
AWS_BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')

s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
)

def get_file(key):
    try:
        if (s3.head_object(Bucket=AWS_BUCKET_NAME, Key=key)):
            url = s3.generate_presigned_url('get_object',
                                        Params={'Bucket': AWS_BUCKET_NAME,
                                                'Key': key},
                                        ExpiresIn=86400)
            return url
        return None
    except Exception as e:
        print(e)
    return None

def upload_file(folder, filename, path):
    try:
        obj_name = f"{folder}/{filename}"

        s3.upload_file(path, AWS_BUCKET_NAME, obj_name)

        return obj_name
    except Exception as e:
        print(e)
    return None
