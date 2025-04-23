# app/api/models/user.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Float, Text, ARRAY, UUID, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    company_size = Column(Integer, nullable=True)
    job_title = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    saved_leads = relationship("SavedLead", back_populates="user")
    api_keys = relationship("ApiKey", back_populates="user")
    search_history = relationship("SearchHistory", back_populates="user")
    team_members = relationship("TeamMember", back_populates="owner")
    
    def __repr__(self):
        return f"<User {self.email}>"


class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="active")  # active, cancelled, past_due
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    leads_used_this_month = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscription")
    plan = relationship("Plan", back_populates="subscriptions")
    
    def __repr__(self):
        return f"<Subscription {self.user_id} - {self.plan_id}>"


class Plan(Base):
    __tablename__ = "plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    billing_interval = Column(String, default="month")  # month, year
    stripe_price_id = Column(String, nullable=True)
    features = Column(ARRAY(String), nullable=True)
    leads_per_month = Column(Integer, nullable=False)
    allows_csv_export = Column(Boolean, default=False)
    allows_crm_sync = Column(Boolean, default=False)
    allows_team_access = Column(Boolean, default=False)
    max_team_members = Column(Integer, default=0)
    allows_api_access = Column(Boolean, default=False)
    allows_white_labeling = Column(Boolean, default=False)
    allows_enrichment = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan")
    
    def __repr__(self):
        return f"<Plan {self.name} - ${self.price}>"


class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    email_status = Column(String, CheckConstraint("email_status IN ('verified', 'pattern_estimate', 'unverified')"))
    job_title = Column(String, nullable=True)
    company = Column(String, nullable=True)
    company_size = Column(Integer, nullable=True)
    industry = Column(String, nullable=True)
    tech_stack = Column(ARRAY(String), nullable=True)
    location = Column(String, nullable=True)
    source = Column(String, nullable=True)
    ai_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    saved_by = relationship("SavedLead", back_populates="lead")
    
    def __repr__(self):
        return f"<Lead {self.full_name} - {self.email}>"


class SavedLead(Base):
    __tablename__ = "saved_leads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    tags = Column(ARRAY(String), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String, default="new")  # new, contacted, qualified, disqualified
    exported_to_crm = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="saved_leads")
    lead = relationship("Lead", back_populates="saved_by")
    
    def __repr__(self):
        return f"<SavedLead {self.user_id} - {self.lead_id}>"


class SearchHistory(Base):
    __tablename__ = "search_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    search_query = Column(Text, nullable=False)
    filters = Column(Text, nullable=True)  # JSON stored as text
    results_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="search_history")
    
    def __repr__(self):
        return f"<SearchHistory {self.user_id} - {self.created_at}>"


class ApiKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    key = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    def __repr__(self):
        return f"<ApiKey {self.name} - {self.user_id}>"


class TeamMember(Base):
    __tablename__ = "team_members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    member_email = Column(String, nullable=False)
    role = Column(String, default="member")  # member, admin
    invitation_token = Column(String, nullable=True)
    invitation_accepted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="team_members")
    
    def __repr__(self):
        return f"<TeamMember {self.member_email} - {self.owner_id}>"


class CrmIntegration(Base):
    __tablename__ = "crm_integrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    crm_type = Column(String, nullable=False)  # hubspot, salesforce, etc.
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    settings = Column(Text, nullable=True)  # JSON stored as text
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<CrmIntegration {self.crm_type} - {self.user_id}>"


class LeadExport(Base):
    __tablename__ = "lead_exports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    export_type = Column(String, nullable=False)  # csv, crm
    lead_count = Column(Integer, nullable=False)
    status = Column(String, default="pending")  # pending, completed, failed
    file_url = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<LeadExport {self.export_type} - {self.user_id}>"


class EmailVerificationLog(Base):
    __tablename__ = "email_verification_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    provider = Column(String, nullable=False)  # zerobounce, neverbounce, etc.
    result = Column(String, nullable=False)
    response_data = Column(Text, nullable=True)  # JSON stored as text
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<EmailVerificationLog {self.lead_id} - {self.result}>"


class PaymentHistory(Base):
    __tablename__ = "payment_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    stripe_payment_id = Column(String, nullable=True)
    amount = Column(Float, nullable=False)
    status = Column(String, nullable=False)  # succeeded, failed, pending
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<PaymentHistory {self.user_id} - {self.amount}>"


class UsageLog(Base):
    __tablename__ = "usage_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)  # search, export, verify, etc.
    details = Column(Text, nullable=True)  # JSON stored as text
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<UsageLog {self.user_id} - {self.action}>"