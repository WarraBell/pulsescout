# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.ai.model_service import ModelService
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PulseScout API",
    description="API for discovering targeted email leads using advanced AI-enhanced search tools",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize models on startup
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up PulseScout API...")
    # Start loading models in the background
    # For production, we would want to use a more sophisticated approach
    # such as loading models in a separate process or using a model server
    import asyncio
    asyncio.create_task(load_models_async())

async def load_models_async():
    """Load models asynchronously to not block startup."""
    import time
    from concurrent.futures import ThreadPoolExecutor
    from functools import partial
    
    # Using a thread to not block the event loop
    with ThreadPoolExecutor() as executor:
        await asyncio.get_event_loop().run_in_executor(
            executor,
            partial(ModelService().load_models)
        )

@app.get("/")
async def root():
    return {"message": "Welcome to PulseScout API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Add a route to check model status
@app.get("/models/status")
async def models_status():
    model_service = ModelService()
    return {
        "spacy_model_loaded": model_service.spacy_ner_model is not None,
        "sentence_transformer_loaded": model_service.sentence_transformer is not None,
        "lead_scoring_model_loaded": model_service.lead_scoring_model is not None
    }

# Import and include routers
# This will be uncommented as you create the API endpoints
# from app.api.endpoints import auth, leads, plans, crm
# app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
# app.include_router(leads.router, prefix="/api/leads", tags=["Leads"])
# app.include_router(plans.router, prefix="/api/plans", tags=["Plans"])
# app.include_router(crm.router, prefix="/api/crm", tags=["CRM"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)