"""
Configuration settings for AI Lead Scoring System
"""

import os
from datetime import timedelta

class Config:
    """Base configuration"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:password@localhost/lead_scoring'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Salesforce settings
    SALESFORCE_CLIENT_ID = os.environ.get('SALESFORCE_CLIENT_ID')
    SALESFORCE_CLIENT_SECRET = os.environ.get('SALESFORCE_CLIENT_SECRET')
    SALESFORCE_USERNAME = os.environ.get('SALESFORCE_USERNAME')
    SALESFORCE_PASSWORD = os.environ.get('SALESFORCE_PASSWORD')
    SALESFORCE_SECURITY_TOKEN = os.environ.get('SALESFORCE_SECURITY_TOKEN')
    SALESFORCE_SANDBOX = os.environ.get('SALESFORCE_SANDBOX', 'True').lower() == 'true'
    
    # Einstein AI settings
    EINSTEIN_MODEL_ID = os.environ.get('EINSTEIN_MODEL_ID')
    EINSTEIN_API_VERSION = os.environ.get('EINSTEIN_API_VERSION', 'v55.0')
    
    # JWT settings
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # API settings
    API_RATE_LIMIT = os.environ.get('API_RATE_LIMIT', '1000 per hour')
    MAX_BATCH_SIZE = int(os.environ.get('MAX_BATCH_SIZE', 100))
    
    # Model settings
    MODEL_RETRAIN_THRESHOLD = int(os.environ.get('MODEL_RETRAIN_THRESHOLD', 1000))
    MODEL_BACKUP_PATH = os.environ.get('MODEL_BACKUP_PATH', './model_backups')
    
    # Logging settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'postgresql://postgres:password@localhost/lead_scoring_dev'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Production security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}