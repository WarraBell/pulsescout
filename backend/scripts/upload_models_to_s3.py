import os
import sys
import tempfile
import zipfile
import boto3
import spacy
from sentence_transformers import SentenceTransformer
from pathlib import Path
import logging
from dotenv import load_dotenv

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def upload_spacy_model(model_name, bucket_name, aws_access_key_id, aws_secret_access_key, aws_region):
    """Upload a spaCy model to S3."""
    s3 = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region
    )
    
    # Download the model
    logger.info(f"Downloading spaCy model: {model_name}")
    model = spacy.load(model_name)
    
    # Create a temporary directory to save the model
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        model_path = temp_dir_path / model_name
        
        # Save the model to disk
        logger.info(f"Saving model to {model_path}")
        model.to_disk(model_path)
        
        # Zip the model directory
        zip_path = temp_dir_path / f"{model_name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in model_path.glob('**/*'):
                if file.is_file():
                    zipf.write(file, file.relative_to(model_path))
        
        # Upload to S3
        s3_key = f"models/spacy/{model_name}.zip"
        logger.info(f"Uploading model to S3: {s3_key}")
        s3.upload_file(str(zip_path), bucket_name, s3_key)
        
        logger.info(f"Model uploaded successfully to {bucket_name}/{s3_key}")

def upload_sentence_transformer(model_name, bucket_name, aws_access_key_id, aws_secret_access_key, aws_region):
    """Upload a SentenceTransformer model to S3."""
    s3 = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region
    )
    
    # Download the model
    logger.info(f"Downloading SentenceTransformer model: {model_name}")
    model = SentenceTransformer(model_name)
    
    # Create a temporary directory to save the model
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        model_path = temp_dir_path / model_name
        
        # Save the model to disk
        logger.info(f"Saving model to {model_path}")
        model.save(str(model_path))
        
        # Create a zip file of the model directory
        zip_path = temp_dir_path / f"{model_name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in model_path.glob('**/*'):
                if file.is_file():
                    zipf.write(file, file.relative_to(model_path))
        
        # Upload to S3
        s3_key = f"models/sentence_transformers/{model_name}"
        logger.info(f"Uploading model to S3: {s3_key}")
        s3.upload_file(str(zip_path), bucket_name, s3_key)
        
        logger.info(f"Model uploaded successfully to {bucket_name}/{s3_key}")


def main():
    # Get AWS credentials
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_REGION')
    bucket_name = os.getenv('S3_MODEL_BUCKET')
    
    if not aws_access_key_id or not aws_secret_access_key:
        logger.error("AWS credentials not provided. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")
        sys.exit(1)
    
    # Models to upload
    spacy_models = ['en_core_web_sm']
    sentence_transformer_models = ['all-MiniLM-L6-v2']
    
    # Upload spaCy models
    for model_name in spacy_models:
        try:
            upload_spacy_model(model_name, bucket_name, aws_access_key_id, aws_secret_access_key, aws_region)
        except Exception as e:
            logger.error(f"Failed to upload spaCy model {model_name}: {str(e)}")
    
    # Upload SentenceTransformer models
    for model_name in sentence_transformer_models:
        try:
            upload_sentence_transformer(model_name, bucket_name, aws_access_key_id, aws_secret_access_key, aws_region)
        except Exception as e:
            logger.error(f"Failed to upload SentenceTransformer model {model_name}: {str(e)}")
    

if __name__ == "__main__":
    main()
