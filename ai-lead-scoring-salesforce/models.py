"""
Database models for AI Lead Scoring System
SQLAlchemy models for lead data and scoring history
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Lead(db.Model):
    """Lead model representing prospects in the system"""
    __tablename__ = 'leads'
    
    id = db.Column(db.Integer, primary_key=True)
    salesforce_id = db.Column(db.String(18), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), nullable=True, index=True)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    company = db.Column(db.String(255), nullable=True, index=True)
    title = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(50), nullable=True, index=True)
    lead_source = db.Column(db.String(100), nullable=True, index=True)
    industry = db.Column(db.String(100), nullable=True, index=True)
    country = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    annual_revenue = db.Column(db.BigInteger, nullable=True)
    number_of_employees = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    scores = db.relationship('Score', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    activities = db.relationship('Activity', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Lead {self.email} - {self.company}>'
    
    @property
    def latest_score(self):
        """Get the most recent score for this lead"""
        return self.scores.order_by(Score.created_at.desc()).first()
    
    @property
    def full_name(self):
        """Get full name of the lead"""
        names = [self.first_name, self.last_name]
        return ' '.join(filter(None, names))
    
    def to_dict(self):
        """Convert lead to dictionary"""
        return {
            'id': self.id,
            'salesforce_id': self.salesforce_id,
            'email': self.email,
            'full_name': self.full_name,
            'company': self.company,
            'title': self.title,
            'phone': self.phone,
            'status': self.status,
            'lead_source': self.lead_source,
            'industry': self.industry,
            'country': self.country,
            'annual_revenue': self.annual_revenue,
            'number_of_employees': self.number_of_employees,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'latest_score': self.latest_score.score if self.latest_score else None
        }

class Score(db.Model):
    """Score model for storing lead scoring results"""
    __tablename__ = 'scores'
    
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, index=True)
    score = db.Column(db.Integer, nullable=False)  # 0-100 score
    probability = db.Column(db.Float, nullable=False)  # 0-1 conversion probability
    confidence = db.Column(db.Float, nullable=False)  # 0-1 confidence level
    model_version = db.Column(db.String(50), nullable=False)
    features = db.Column(db.Text, nullable=True)  # JSON string of features used
    model_predictions = db.Column(db.Text, nullable=True)  # JSON string of individual model predictions
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f'<Score {self.score} for Lead {self.lead_id}>'
    
    @property
    def features_dict(self):
        """Get features as dictionary"""
        if self.features:
            try:
                return json.loads(self.features)
            except json.JSONDecodeError:
                return {}
        return {}
    
    @features_dict.setter
    def features_dict(self, value):
        """Set features from dictionary"""
        self.features = json.dumps(value) if value else None
    
    @property
    def predictions_dict(self):
        """Get model predictions as dictionary"""
        if self.model_predictions:
            try:
                return json.loads(self.model_predictions)
            except json.JSONDecodeError:
                return {}
        return {}
    
    @predictions_dict.setter
    def predictions_dict(self, value):
        """Set model predictions from dictionary"""
        self.model_predictions = json.dumps(value) if value else None
    
    def to_dict(self):
        """Convert score to dictionary"""
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'score': self.score,
            'probability': self.probability,
            'confidence': self.confidence,
            'model_version': self.model_version,
            'features': self.features_dict,
            'model_predictions': self.predictions_dict,
            'created_at': self.created_at.isoformat()
        }

class Activity(db.Model):
    """Activity model for tracking lead interactions"""
    __tablename__ = 'activities'
    
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, index=True)
    activity_type = db.Column(db.String(100), nullable=False, index=True)
    subject = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    activity_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), nullable=True)
    salesforce_id = db.Column(db.String(18), nullable=True, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Activity {self.activity_type} for Lead {self.lead_id}>'
    
    def to_dict(self):
        """Convert activity to dictionary"""
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'activity_type': self.activity_type,
            'subject': self.subject,
            'description': self.description,
            'activity_date': self.activity_date.isoformat() if self.activity_date else None,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

class Analytics(db.Model):
    """Analytics model for storing performance metrics"""
    __tablename__ = 'analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    metric_name = db.Column(db.String(100), nullable=False, index=True)
    metric_value = db.Column(db.Float, nullable=False)
    metric_type = db.Column(db.String(50), nullable=False)  # 'accuracy', 'conversion_rate', etc.
    model_version = db.Column(db.String(50), nullable=True)
    date_recorded = db.Column(db.Date, nullable=False, index=True)
    metadata = db.Column(db.Text, nullable=True)  # JSON for additional context
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Analytics {self.metric_name}: {self.metric_value}>'
    
    @property
    def metadata_dict(self):
        """Get metadata as dictionary"""
        if self.metadata:
            try:
                return json.loads(self.metadata)
            except json.JSONDecodeError:
                return {}
        return {}
    
    @metadata_dict.setter
    def metadata_dict(self, value):
        """Set metadata from dictionary"""
        self.metadata = json.dumps(value) if value else None
    
    def to_dict(self):
        """Convert analytics to dictionary"""
        return {
            'id': self.id,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'metric_type': self.metric_type,
            'model_version': self.model_version,
            'date_recorded': self.date_recorded.isoformat(),
            'metadata': self.metadata_dict,
            'created_at': self.created_at.isoformat()
        }

class ModelTraining(db.Model):
    """Model training history and performance tracking"""
    __tablename__ = 'model_training'
    
    id = db.Column(db.Integer, primary_key=True)
    model_version = db.Column(db.String(50), nullable=False, index=True)
    training_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    training_samples = db.Column(db.Integer, nullable=False)
    test_accuracy = db.Column(db.Float, nullable=True)
    test_precision = db.Column(db.Float, nullable=True)
    test_recall = db.Column(db.Float, nullable=True)
    test_f1_score = db.Column(db.Float, nullable=True)
    cross_val_mean = db.Column(db.Float, nullable=True)
    cross_val_std = db.Column(db.Float, nullable=True)
    feature_importance = db.Column(db.Text, nullable=True)  # JSON string
    hyperparameters = db.Column(db.Text, nullable=True)  # JSON string
    training_duration = db.Column(db.Float, nullable=True)  # seconds
    notes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<ModelTraining {self.model_version} - {self.training_date}>'
    
    @property
    def feature_importance_dict(self):
        """Get feature importance as dictionary"""
        if self.feature_importance:
            try:
                return json.loads(self.feature_importance)
            except json.JSONDecodeError:
                return {}
        return {}
    
    @feature_importance_dict.setter
    def feature_importance_dict(self, value):
        """Set feature importance from dictionary"""
        self.feature_importance = json.dumps(value) if value else None
    
    @property
    def hyperparameters_dict(self):
        """Get hyperparameters as dictionary"""
        if self.hyperparameters:
            try:
                return json.loads(self.hyperparameters)
            except json.JSONDecodeError:
                return {}
        return {}
    
    @hyperparameters_dict.setter
    def hyperparameters_dict(self, value):
        """Set hyperparameters from dictionary"""
        self.hyperparameters = json.dumps(value) if value else None
    
    def to_dict(self):
        """Convert model training to dictionary"""
        return {
            'id': self.id,
            'model_version': self.model_version,
            'training_date': self.training_date.isoformat(),
            'training_samples': self.training_samples,
            'test_accuracy': self.test_accuracy,
            'test_precision': self.test_precision,
            'test_recall': self.test_recall,
            'test_f1_score': self.test_f1_score,
            'cross_val_mean': self.cross_val_mean,
            'cross_val_std': self.cross_val_std,
            'feature_importance': self.feature_importance_dict,
            'hyperparameters': self.hyperparameters_dict,
            'training_duration': self.training_duration,
            'notes': self.notes
        }

# Database utility functions
def init_db(app):
    """Initialize database with app context"""
    with app.app_context():
        db.create_all()
        print("Database tables created successfully")

def create_indexes():
    """Create additional database indexes for performance"""
    # Add custom indexes if needed
    pass

def get_lead_statistics():
    """Get basic lead statistics"""
    return {
        'total_leads': Lead.query.count(),
        'scored_leads': db.session.query(Lead.id).join(Score).distinct().count(),
        'converted_leads': Lead.query.filter_by(status='Converted').count(),
        'recent_leads': Lead.query.filter(
            Lead.created_at >= datetime.utcnow().replace(day=1)
        ).count()
    }

def get_score_distribution():
    """Get distribution of lead scores"""
    score_ranges = [
        (0, 20), (20, 40), (40, 60), (60, 80), (80, 100)
    ]
    
    distribution = {}
    for min_score, max_score in score_ranges:
        count = db.session.query(Score).filter(
            Score.score >= min_score,
            Score.score < max_score
        ).count()
        distribution[f"{min_score}-{max_score}"] = count
    
    return distribution