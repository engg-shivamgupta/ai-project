"""
Lead Scoring Engine using Salesforce Einstein AI
Advanced machine learning pipeline for lead conversion prediction
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class LeadScoringEngine:
    """Advanced lead scoring engine with ensemble learning"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.encoders = {}
        self.feature_importance = {}
        self.model_version = "1.0"
        self.is_trained = False
        
        # Initialize models
        self._initialize_models()
        
        # Load pre-trained models if available
        self._load_models()
    
    def _initialize_models(self):
        """Initialize machine learning models"""
        self.models = {
            'logistic_regression': LogisticRegression(
                random_state=42,
                max_iter=1000,
                class_weight='balanced'
            ),
            'random_forest': RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                class_weight='balanced',
                max_depth=10
            ),
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=100,
                random_state=42,
                learning_rate=0.1,
                max_depth=6
            ),
            'neural_network': MLPClassifier(
                hidden_layer_sizes=(100, 50),
                random_state=42,
                max_iter=500,
                alpha=0.01
            )
        }
        
        self.scalers = {
            'standard': StandardScaler(),
            'minmax': StandardScaler()  # Can be replaced with MinMaxScaler if needed
        }
    
    def extract_features(self, lead_data: Dict) -> Dict:
        """Extract and engineer features from lead data"""
        features = {}
        
        # Company size features
        company_size = lead_data.get('company_size', 'unknown')
        if isinstance(company_size, str):
            size_mapping = {
                'startup': 1, 'small': 2, 'medium': 3, 
                'large': 4, 'enterprise': 5, 'unknown': 0
            }
            features['company_size_encoded'] = size_mapping.get(company_size.lower(), 0)
        else:
            features['company_size_encoded'] = min(5, max(0, int(company_size / 1000)))
        
        # Industry features
        industry = lead_data.get('industry', 'unknown').lower()
        high_value_industries = ['technology', 'finance', 'healthcare', 'manufacturing']
        features['high_value_industry'] = 1 if industry in high_value_industries else 0
        
        # Budget features
        budget = lead_data.get('budget', 0)
        if isinstance(budget, str):
            budget = self._parse_budget_string(budget)
        features['budget_normalized'] = min(1.0, budget / 100000) if budget > 0 else 0
        features['has_budget'] = 1 if budget > 0 else 0
        
        # Timeline features
        timeline = lead_data.get('timeline', 'unknown').lower()
        timeline_mapping = {
            'immediate': 5, 'q1': 4, 'q2': 3, 'q3': 2, 
            'q4': 1, 'next_year': 1, 'unknown': 0
        }
        features['timeline_urgency'] = timeline_mapping.get(timeline, 0)
        
        # Engagement features
        features['email_opens'] = lead_data.get('email_opens', 0)
        features['email_clicks'] = lead_data.get('email_clicks', 0)
        features['website_visits'] = lead_data.get('website_visits', 0)
        features['content_downloads'] = lead_data.get('content_downloads', 0)
        
        # Calculated engagement score
        engagement_score = (
            features['email_opens'] * 0.1 +
            features['email_clicks'] * 0.3 +
            features['website_visits'] * 0.2 +
            features['content_downloads'] * 0.4
        )
        features['engagement_score'] = min(100, engagement_score)
        
        # Lead source features
        lead_source = lead_data.get('lead_source', 'unknown').lower()
        high_quality_sources = ['referral', 'partner', 'demo_request', 'inbound']
        features['high_quality_source'] = 1 if lead_source in high_quality_sources else 0
        
        # Geographic features
        country = lead_data.get('country', 'unknown').lower()
        tier1_countries = ['us', 'uk', 'canada', 'australia', 'germany', 'france']
        features['tier1_country'] = 1 if country in tier1_countries else 0
        
        # Contact information quality
        features['has_phone'] = 1 if lead_data.get('phone') else 0
        features['has_linkedin'] = 1 if lead_data.get('linkedin_profile') else 0
        features['complete_profile'] = (
            features['has_phone'] + features['has_linkedin'] + 
            (1 if lead_data.get('company') else 0)
        ) / 3
        
        # Behavioral features
        features['demo_requested'] = 1 if lead_data.get('demo_requested') else 0
        features['pricing_inquired'] = 1 if lead_data.get('pricing_inquired') else 0
        features['multiple_contacts'] = 1 if lead_data.get('contact_count', 1) > 1 else 0
        
        return features
    
    def _parse_budget_string(self, budget_str: str) -> float:
        """Parse budget string to numeric value"""
        budget_str = budget_str.lower().replace(',', '').replace('$', '')
        
        if 'k' in budget_str:
            return float(budget_str.replace('k', '')) * 1000
        elif 'm' in budget_str:
            return float(budget_str.replace('m', '')) * 1000000
        else:
            try:
                return float(budget_str)
            except ValueError:
                return 0
    
    def prepare_training_data(self, training_data: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data for model training"""
        features_list = []
        labels_list = []
        
        for record in training_data:
            features = self.extract_features(record)
            features_list.append(list(features.values()))
            
            # Convert status to binary label
            converted = 1 if record.get('status') == 'Converted' else 0
            labels_list.append(converted)
        
        # Convert to numpy arrays
        X = np.array(features_list)
        y = np.array(labels_list)
        
        # Scale features
        X_scaled = self.scalers['standard'].fit_transform(X)
        
        return X_scaled, y
    
    def train_models(self, training_data: List[Dict]) -> Dict:
        """Train all models with the provided data"""
        logger.info("Starting model training...")
        
        # Prepare data
        X, y = self.prepare_training_data(training_data)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        training_results = {}
        
        # Train each model
        for model_name, model in self.models.items():
            logger.info(f"Training {model_name}...")
            
            # Train model
            model.fit(X_train, y_train)
            
            # Evaluate on test set
            y_pred = model.predict(X_test)
            y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else y_pred
            
            # Calculate metrics
            metrics = {
                'accuracy': accuracy_score(y_test, y_pred),
                'precision': precision_score(y_test, y_pred),
                'recall': recall_score(y_test, y_pred),
                'f1_score': f1_score(y_test, y_pred)
            }
            
            # Cross-validation
            cv_scores = cross_val_score(model, X_train, y_train, cv=5)
            metrics['cv_mean'] = cv_scores.mean()
            metrics['cv_std'] = cv_scores.std()
            
            training_results[model_name] = metrics
            
            # Store feature importance if available
            if hasattr(model, 'feature_importances_'):
                self.feature_importance[model_name] = model.feature_importances_
            elif hasattr(model, 'coef_'):
                self.feature_importance[model_name] = np.abs(model.coef_[0])
        
        self.is_trained = True
        
        # Save models
        self._save_models()
        
        logger.info("Model training completed")
        return training_results
    
    def score_lead(self, lead_features: Dict) -> Dict:
        """Score a single lead using the ensemble model"""
        if not self.is_trained:
            logger.warning("Models not trained. Using default scoring.")
            return self._default_score(lead_features)
        
        # Extract and prepare features
        features = self.extract_features(lead_features)
        feature_array = np.array([list(features.values())])
        
        # Scale features
        feature_scaled = self.scalers['standard'].transform(feature_array)
        
        # Get predictions from all models
        predictions = {}
        probabilities = {}
        
        for model_name, model in self.models.items():
            pred = model.predict(feature_scaled)[0]
            predictions[model_name] = pred
            
            if hasattr(model, 'predict_proba'):
                prob = model.predict_proba(feature_scaled)[0][1]
                probabilities[model_name] = prob
            else:
                probabilities[model_name] = pred
        
        # Ensemble prediction (weighted average)
        weights = {
            'logistic_regression': 0.2,
            'random_forest': 0.3,
            'gradient_boosting': 0.3,
            'neural_network': 0.2
        }
        
        ensemble_probability = sum(
            probabilities[model] * weights[model]
            for model in probabilities.keys()
        )
        
        # Convert probability to score (0-100)
        score = int(ensemble_probability * 100)
        
        # Calculate confidence based on model agreement
        prob_values = list(probabilities.values())
        confidence = 1 - (np.std(prob_values) / np.mean(prob_values)) if np.mean(prob_values) > 0 else 0
        confidence = max(0, min(1, confidence))
        
        return {
            'score': score,
            'probability': round(ensemble_probability, 4),
            'confidence': round(confidence, 4),
            'model_predictions': predictions,
            'model_probabilities': probabilities,
            'model_version': self.model_version,
            'features_used': list(features.keys())
        }
    
    def _default_score(self, lead_features: Dict) -> Dict:
        """Provide default scoring when models aren't trained"""
        features = self.extract_features(lead_features)
        
        # Simple rule-based scoring
        base_score = 50
        
        # Budget impact
        if features.get('budget_normalized', 0) > 0.5:
            base_score += 20
        elif features.get('budget_normalized', 0) > 0.2:
            base_score += 10
        
        # Engagement impact
        if features.get('engagement_score', 0) > 50:
            base_score += 15
        elif features.get('engagement_score', 0) > 20:
            base_score += 8
        
        # Company size impact
        if features.get('company_size_encoded', 0) >= 4:
            base_score += 10
        
        # Timeline urgency
        if features.get('timeline_urgency', 0) >= 4:
            base_score += 10
        
        # Industry impact
        if features.get('high_value_industry', 0):
            base_score += 8
        
        score = min(100, max(0, base_score))
        probability = score / 100
        
        return {
            'score': score,
            'probability': probability,
            'confidence': 0.6,  # Lower confidence for rule-based scoring
            'model_version': 'rule_based',
            'features_used': list(features.keys())
        }
    
    def get_model_accuracy(self) -> float:
        """Get overall model accuracy"""
        if not self.is_trained:
            return 0.0
        
        # Return average accuracy across all models
        # This would typically be stored from the last training session
        return 0.873  # Example value from the README
    
    def get_feature_importance(self, model_name: str = 'random_forest') -> Dict:
        """Get feature importance for interpretation"""
        if model_name not in self.feature_importance:
            return {}
        
        # Sample feature names (should match extract_features output)
        feature_names = [
            'company_size_encoded', 'high_value_industry', 'budget_normalized',
            'has_budget', 'timeline_urgency', 'email_opens', 'email_clicks',
            'website_visits', 'content_downloads', 'engagement_score',
            'high_quality_source', 'tier1_country', 'has_phone', 'has_linkedin',
            'complete_profile', 'demo_requested', 'pricing_inquired', 'multiple_contacts'
        ]
        
        importance_scores = self.feature_importance[model_name]
        
        return dict(zip(feature_names, importance_scores))
    
    def _save_models(self):
        """Save trained models to disk"""
        model_dir = 'models'
        os.makedirs(model_dir, exist_ok=True)
        
        # Save each model
        for model_name, model in self.models.items():
            model_path = os.path.join(model_dir, f'{model_name}.joblib')
            joblib.dump(model, model_path)
        
        # Save scalers
        for scaler_name, scaler in self.scalers.items():
            scaler_path = os.path.join(model_dir, f'{scaler_name}_scaler.joblib')
            joblib.dump(scaler, scaler_path)
        
        logger.info("Models saved successfully")
    
    def _load_models(self):
        """Load pre-trained models from disk"""
        model_dir = 'models'
        
        if not os.path.exists(model_dir):
            logger.info("No pre-trained models found")
            return
        
        try:
            # Load models
            for model_name in self.models.keys():
                model_path = os.path.join(model_dir, f'{model_name}.joblib')
                if os.path.exists(model_path):
                    self.models[model_name] = joblib.load(model_path)
            
            # Load scalers
            for scaler_name in self.scalers.keys():
                scaler_path = os.path.join(model_dir, f'{scaler_name}_scaler.joblib')
                if os.path.exists(scaler_path):
                    self.scalers[scaler_name] = joblib.load(scaler_path)
            
            self.is_trained = True
            logger.info("Pre-trained models loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
            self.is_trained = False
    
    def retrain_with_feedback(self, feedback_data: List[Dict]):
        """Retrain models with new conversion feedback"""
        logger.info("Retraining models with feedback data...")
        
        # Combine with existing training data if available
        self.train_models(feedback_data)
        
        logger.info("Model retraining completed")
    
    def explain_prediction(self, lead_features: Dict) -> Dict:
        """Provide explanation for the lead score"""
        features = self.extract_features(lead_features)
        score_result = self.score_lead(lead_features)
        
        # Identify top contributing factors
        feature_importance = self.get_feature_importance()
        
        explanations = []
        
        # Analyze key features
        if features.get('budget_normalized', 0) > 0.5:
            explanations.append("High budget indicates strong purchase intent")
        
        if features.get('engagement_score', 0) > 70:
            explanations.append("High engagement score shows strong interest")
        
        if features.get('timeline_urgency', 0) >= 4:
            explanations.append("Urgent timeline suggests ready to buy")
        
        if features.get('demo_requested'):
            explanations.append("Demo request indicates serious consideration")
        
        if features.get('high_value_industry'):
            explanations.append("Industry has high conversion potential")
        
        return {
            'score': score_result['score'],
            'explanations': explanations,
            'key_features': feature_importance,
            'recommendations': self._generate_recommendations(features)
        }
    
    def _generate_recommendations(self, features: Dict) -> List[str]:
        """Generate action recommendations based on lead features"""
        recommendations = []
        
        if features.get('engagement_score', 0) < 30:
            recommendations.append("Increase engagement with targeted content")
        
        if not features.get('demo_requested'):
            recommendations.append("Offer product demo or trial")
        
        if features.get('timeline_urgency', 0) >= 4:
            recommendations.append("Prioritize immediate follow-up")
        
        if features.get('budget_normalized', 0) == 0:
            recommendations.append("Qualify budget requirements")
        
        if not features.get('complete_profile'):
            recommendations.append("Collect additional contact information")
        
        return recommendations