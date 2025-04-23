# backend/app/utils/model_loader/s3_model_loader.py
import os
import boto3
import tempfile
import logging
from pathlib import Path
import spacy
from sentence_transformers import SentenceTransformer
import pickle
import lightgbm as lgb

logger = logging.getLogger(__name__)

class S3ModelLoader:
    def __init__(self, bucket_name, aws_access_key_id=None, aws_secret_access_key=None, region_name=None):
        """
        Initialize the S3ModelLoader.
        
        Args:
            bucket_name (str): The S3 bucket name
            aws_access_key_id (str, optional): AWS access key ID. Defaults to None.
            aws_secret_access_key (str, optional): AWS secret access key. Defaults to None.
            region_name (str, optional): AWS region name. Defaults to None.
        """
        self.bucket_name = bucket_name
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id or os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=aws_secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=region_name or os.getenv('AWS_REGION', 'us-east-1')
        )
        self.model_cache_dir = Path(os.getenv('MODEL_CACHE_DIR', '/tmp/model_cache'))
        self.model_cache_dir.mkdir(exist_ok=True, parents=True)
        
    def _download_from_s3(self, s3_key, local_path):
        """Download a file from S3 to a local path."""
        try:
            logger.info(f"Downloading model from S3: {s3_key} to {local_path}")
            self.s3.download_file(self.bucket_name, s3_key, str(local_path))
            return True
        except Exception as e:
            logger.error(f"Failed to download model from S3: {e}")
            return False
    
    def _upload_to_s3(self, local_path, s3_key):
        """Upload a file to S3."""
        try:
            logger.info(f"Uploading model to S3: {local_path} to {s3_key}")
            self.s3.upload_file(str(local_path), self.bucket_name, s3_key)
            return True
        except Exception as e:
            logger.error(f"Failed to upload model to S3: {e}")
            return False
    
    def load_spacy_model(self, model_name, s3_key=None):
        """
        Load a spaCy model from S3 or download it if not available.
        
        Args:
            model_name (str): The name of the spaCy model (e.g., 'en_core_web_sm')
            s3_key (str, optional): The S3 key for the model. If None, defaults to 'models/spacy/{model_name}'
            
        Returns:
            spacy.Language: The loaded spaCy model
        """
        if s3_key is None:
            s3_key = f"models/spacy/{model_name}"
        
        # Check if model exists in cache
        cache_path = self.model_cache_dir / f"spacy_{model_name}"
        if cache_path.exists():
            logger.info(f"Loading spaCy model from cache: {cache_path}")
            return spacy.load(cache_path)
        
        # Try to download from S3
        if self._download_from_s3(s3_key, cache_path):
            try:
                return spacy.load(cache_path)
            except Exception as e:
                logger.error(f"Failed to load downloaded spaCy model: {e}")
                # If loading fails, the download might be corrupted or incomplete
                if cache_path.exists():
                    import shutil
                    shutil.rmtree(cache_path)
        
        # If we couldn't load from S3, download the model using spaCy
        logger.info(f"Downloading spaCy model using spacy.load: {model_name}")
        model = spacy.load(model_name)
        
        # Save to cache
        model.to_disk(cache_path)
        
        # Upload to S3 for future use
        self._upload_to_s3(cache_path, s3_key)
        
        return model
    
    def load_sentence_transformer(self, model_name, s3_key=None):
        """
        Load a SentenceTransformer model from S3 or download it if not available.
        
        Args:
            model_name (str): The name of the SentenceTransformer model
            s3_key (str, optional): The S3 key for the model. If None, defaults to 'models/sentence_transformers/{model_name}'
            
        Returns:
            SentenceTransformer: The loaded SentenceTransformer model
        """
        if s3_key is None:
            s3_key = f"models/sentence_transformers/{model_name}"
        
        # Check if model exists in cache
        cache_path = self.model_cache_dir / f"st_{model_name}"
        if cache_path.exists():
            logger.info(f"Loading SentenceTransformer model from cache: {cache_path}")
            return SentenceTransformer(str(cache_path))
        
        # Try to download from S3
        if cache_path.parent.exists():
            import shutil
            shutil.rmtree(cache_path.parent)
        
        cache_path.parent.mkdir(exist_ok=True, parents=True)
        
        try:
            # Create a temporary directory to extract the model
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_zip = Path(temp_dir) / "model.zip"
                
                if self._download_from_s3(s3_key, temp_zip):
                    try:
                        import zipfile
                        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                            zip_ref.extractall(cache_path)
                        return SentenceTransformer(str(cache_path))
                    except Exception as e:
                        logger.error(f"Failed to extract or load SentenceTransformer model: {e}")
        except Exception as e:
            logger.error(f"Failed to download SentenceTransformer model from S3: {e}")
        
        # If we couldn't load from S3, download the model using SentenceTransformer
        logger.info(f"Downloading SentenceTransformer model: {model_name}")
        model = SentenceTransformer(model_name)
        
        # Save to cache
        model.save(str(cache_path))
        
        # Create a zip file of the model directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_zip = Path(temp_dir) / "model.zip"
            
            import zipfile
            with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in cache_path.glob('**/*'):
                    if file.is_file():
                        zipf.write(file, file.relative_to(cache_path))
            
            # Upload to S3 for future use
            self._upload_to_s3(temp_zip, s3_key)
        
        return model
    
    def load_lightgbm_model(self, model_path, s3_key=None):
        """
        Load a LightGBM model from S3 or local path.
        
        Args:
            model_path (str): The local path or name of the LightGBM model
            s3_key (str, optional): The S3 key for the model. If None, defaults to 'models/lightgbm/{model_path.stem}'
            
        Returns:
            lgb.Booster: The loaded LightGBM model
        """
        model_path = Path(model_path)
        if s3_key is None:
            s3_key = f"models/lightgbm/{model_path.stem}.txt"
        
        # Check if model exists in cache
        cache_path = self.model_cache_dir / f"lgb_{model_path.stem}.txt"
        if cache_path.exists():
            logger.info(f"Loading LightGBM model from cache: {cache_path}")
            return lgb.Booster(model_file=str(cache_path))
        
        # Try to download from S3
        if self._download_from_s3(s3_key, cache_path):
            try:
                return lgb.Booster(model_file=str(cache_path))
            except Exception as e:
                logger.error(f"Failed to load downloaded LightGBM model: {e}")
                # If loading fails, the download might be corrupted
                if cache_path.exists():
                    cache_path.unlink()
        
        # If we couldn't load from S3, try to load from the provided path
        if model_path.exists():
            logger.info(f"Loading LightGBM model from provided path: {model_path}")
            model = lgb.Booster(model_file=str(model_path))
            
            # Save to cache
            model.save_model(str(cache_path))
            
            # Upload to S3 for future use
            self._upload_to_s3(cache_path, s3_key)
            
            return model
        
        raise FileNotFoundError(f"LightGBM model not found in S3 or local path: {model_path}")