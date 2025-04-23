# app/db/init_db.py
from sqlalchemy.orm import Session
from app.api.models.user import Base, Plan
import uuid
from datetime import datetime

def init_db(db: Session) -> None:
    """
    Initialize the database with default data
    """
    # Create plans
    create_default_plans(db)

def create_default_plans(db: Session) -> None:
    """
    Create default subscription plans
    """
    # Check if plans already exist
    existing_plans = db.query(Plan).all()
    if existing_plans:
        return
    
    # Create plans
    plans = [
        Plan(
            id=uuid.uuid4(),
            name="Free Trial",
            description="Limited to 25 leads/month with basic filters only",
            price=0.0,
            billing_interval="month",
            features=["Basic filters", "25 leads/month"],
            leads_per_month=25,
            allows_csv_export=False,
            allows_crm_sync=False,
            allows_team_access=False,
            max_team_members=0,
            allows_api_access=False,
            allows_white_labeling=False,
            allows_enrichment=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        Plan(
            id=uuid.uuid4(),
            name="Starter",
            description="For freelancers and early testers",
            price=39.0,
            billing_interval="month",
            stripe_price_id="price_starter_monthly",
            features=["250 leads/month", "Email generation", "Email verification", "Export to CSV"],
            leads_per_month=250,
            allows_csv_export=True,
            allows_crm_sync=False,
            allows_team_access=False,
            max_team_members=0,
            allows_api_access=False,
            allows_white_labeling=False,
            allows_enrichment=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        Plan(
            id=uuid.uuid4(),
            name="Growth",
            description="For solo founders and small businesses",
            price=79.0,
            billing_interval="month",
            stripe_price_id="price_growth_monthly",
            features=["1,000 leads/month", "Email generation", "Email verification", 
                     "Export to CSV", "Basic integrations", "Light data enrichment", "Priority email support"],
            leads_per_month=1000,
            allows_csv_export=True,
            allows_crm_sync=False,
            allows_team_access=False,
            max_team_members=0,
            allows_api_access=False,
            allows_white_labeling=False,
            allows_enrichment=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        Plan(
            id=uuid.uuid4(),
            name="Scale",
            description="For small sales teams",
            price=169.0,
            billing_interval="month",
            stripe_price_id="price_scale_monthly",
            features=["5,000 leads/month", "Email generation", "Email verification", 
                     "Export to CSV", "CRM sync", "Lead tagging & organization", 
                     "Team access (up to 2 users)", "API access"],
            leads_per_month=5000,
            allows_csv_export=True,
            allows_crm_sync=True,
            allows_team_access=True,
            max_team_members=2,
            allows_api_access=True,
            allows_white_labeling=False,
            allows_enrichment=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        Plan(
            id=uuid.uuid4(),
            name="Pro+",
            description="For agencies and high-volume teams",
            price=399.0,
            billing_interval="month",
            stripe_price_id="price_proplus_monthly",
            features=["20,000 leads/month", "Email generation", "Email verification", 
                     "Export to CSV", "CRM sync", "Lead tagging & organization", 
                     "Unlimited team members", "API access", "White labeling", 
                     "SLA-backed support", "AI-powered enrichment"],
            leads_per_month=20000,
            allows_csv_export=True,
            allows_crm_sync=True,
            allows_team_access=True,
            max_team_members=999,  # Unlimited
            allows_api_access=True,
            allows_white_labeling=True,
            allows_enrichment=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
    ]
    
    for plan in plans:
        db.add(plan)
    
    db.commit()