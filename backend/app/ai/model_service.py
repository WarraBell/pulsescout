# backend/app/ai/model_service.py
import os
from pathlib import Path
import logging
from app.utils.model_loader.s3_model_loader import S3ModelLoader

logger = logging.getLogger(__name__)

class ModelService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelService, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        if self.initialized:
            return
        
        self.initialized = True
        self.s3_bucket = os.getenv('S3_MODEL_BUCKET', 'pulsescout-models')
        self.model_loader = S3ModelLoader(
            bucket_name=self.s3_bucket,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        
        # Initialize model placeholders
        self.spacy_ner_model = None
        self.sentence_transformer = None
        self.lead_scoring_model = None
    
    def load_models(self):
        """Load all required models for the application."""
        logger.info("Loading AI models...")
        self.load_spacy_model()
        self.load_sentence_transformer()
        # The LightGBM model will be loaded once trained or acquired
        
        logger.info("All models loaded successfully.")
    
    def load_spacy_model(self, model_name='en_core_web_sm'):
        """Load the spaCy NER model."""
        logger.info(f"Loading spaCy model: {model_name}")
        self.spacy_ner_model = self.model_loader.load_spacy_model(model_name)
        return self.spacy_ner_model
    
    def load_sentence_transformer(self, model_name='all-MiniLM-L6-v2'):
        """Load the SentenceTransformer model."""
        logger.info(f"Loading SentenceTransformer model: {model_name}")
        self.sentence_transformer = self.model_loader.load_sentence_transformer(model_name)
        return self.sentence_transformer
    
    def load_lead_scoring_model(self, model_path):
        """Load the lead scoring LightGBM model."""
        logger.info(f"Loading LightGBM model: {model_path}")
        self.lead_scoring_model = self.model_loader.load_lightgbm_model(model_path)
        return self.lead_scoring_model
    
    # Methods to get models (load if not already loaded)
    def get_spacy_model(self):
        if self.spacy_ner_model is None:
            self.load_spacy_model()
        return self.spacy_ner_model
    
    def get_sentence_transformer(self):
        if self.sentence_transformer is None:
            self.load_sentence_transformer()
        return self.sentence_transformer
    
    def get_lead_scoring_model(self):
        if self.lead_scoring_model is None:
            raise ValueError("Lead scoring model has not been loaded. Call load_lead_scoring_model first.")
        return self.lead_scoring_model