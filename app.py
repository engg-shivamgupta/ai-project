"""
AI-Powered Lead Scoring System with Salesforce Einstein AI
Main Flask application file
"""

from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import logging
from salesforce_integration import SalesforceClient
from lead_scoring_engine import LeadScoringEngine
from models import db, Lead, Score, Analytics

# Initialize Flask app
app = Flask(__name__)
app.config.from_object('config.Config')

# Initialize extensions
db.init_app(app)
CORS(app)

# Initialize clients
salesforce_client = SalesforceClient()
scoring_engine = LeadScoringEngine()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/leads/<lead_id>/score', methods=['GET'])
def get_lead_score(lead_id):
    """Get existing lead score"""
    try:
        lead = Lead.query.filter_by(salesforce_id=lead_id).first()
        if not lead:
            return jsonify({'error': 'Lead not found'}), 404
        
        latest_score = Score.query.filter_by(lead_id=lead.id)\
            .order_by(Score.created_at.desc()).first()
        
        if not latest_score:
            return jsonify({'error': 'No score available'}), 404
        
        return jsonify({
            'lead_id': lead_id,
            'score': latest_score.score,
            'probability': latest_score.probability,
            'confidence': latest_score.confidence,
            'features': latest_score.features,
            'created_at': latest_score.created_at.isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting lead score: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/leads/<lead_id>/score', methods=['POST'])
def update_lead_score(lead_id):
    """Update lead score with new features"""
    try:
        data = request.get_json()
        features = data.get('features', {})
        
        # Get or create lead
        lead = Lead.query.filter_by(salesforce_id=lead_id).first()
        if not lead:
            # Fetch lead data from Salesforce
            sf_lead = salesforce_client.get_lead(lead_id)
            if not sf_lead:
                return jsonify({'error': 'Lead not found in Salesforce'}), 404
            
            lead = Lead(
                salesforce_id=lead_id,
                email=sf_lead.get('Email'),
                company=sf_lead.get('Company'),
                status=sf_lead.get('Status')
            )
            db.session.add(lead)
            db.session.commit()
        
        # Generate score using Einstein AI
        score_result = scoring_engine.score_lead(features)
        
        # Save score to database
        score = Score(
            lead_id=lead.id,
            score=score_result['score'],
            probability=score_result['probability'],
            confidence=score_result['confidence'],
            features=features,
            model_version=score_result['model_version']
        )
        db.session.add(score)
        db.session.commit()
        
        # Update Salesforce with new score
        salesforce_client.update_lead_score(lead_id, score_result)
        
        return jsonify({
            'lead_id': lead_id,
            'score': score_result['score'],
            'probability': score_result['probability'],
            'confidence': score_result['confidence'],
            'status': 'updated'
        })
    
    except Exception as e:
        logger.error(f"Error updating lead score: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/leads/batch-score', methods=['POST'])
def batch_score_leads():
    """Score multiple leads in batch"""
    try:
        data = request.get_json()
        leads = data.get('leads', [])
        
        results = []
        for lead_data in leads:
            lead_id = lead_data['id']
            features = lead_data['features']
            
            # Score individual lead
            score_result = scoring_engine.score_lead(features)
            
            # Update Salesforce
            salesforce_client.update_lead_score(lead_id, score_result)
            
            results.append({
                'lead_id': lead_id,
                'score': score_result['score'],
                'probability': score_result['probability'],
                'status': 'processed'
            })
        
        return jsonify({
            'processed': len(results),
            'results': results
        })
    
    except Exception as e:
        logger.error(f"Error in batch scoring: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/analytics/metrics', methods=['GET'])
def get_analytics_metrics():
    """Get scoring metrics and performance data"""
    try:
        # Calculate metrics from database
        total_leads = Lead.query.count()
        scored_leads = db.session.query(Lead.id).join(Score).distinct().count()
        
        # Get conversion rates
        converted_leads = Lead.query.filter_by(status='Converted').count()
        conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0
        
        # Get average scores by conversion status
        avg_score_converted = db.session.query(db.func.avg(Score.score))\
            .join(Lead).filter(Lead.status == 'Converted').scalar() or 0
        
        avg_score_not_converted = db.session.query(db.func.avg(Score.score))\
            .join(Lead).filter(Lead.status != 'Converted').scalar() or 0
        
        return jsonify({
            'total_leads': total_leads,
            'scored_leads': scored_leads,
            'conversion_rate': round(conversion_rate, 2),
            'avg_score_converted': round(avg_score_converted, 2),
            'avg_score_not_converted': round(avg_score_not_converted, 2),
            'model_accuracy': scoring_engine.get_model_accuracy(),
            'last_updated': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/analytics/conversion-rates', methods=['GET'])
def get_conversion_rates():
    """Get conversion rates by score ranges"""
    try:
        score_ranges = [
            (0, 20, 'Very Low'),
            (20, 40, 'Low'),
            (40, 60, 'Medium'),
            (60, 80, 'High'),
            (80, 100, 'Very High')
        ]
        
        conversion_data = []
        for min_score, max_score, label in score_ranges:
            # Get leads in this score range
            leads_in_range = db.session.query(Lead.id)\
                .join(Score)\
                .filter(Score.score >= min_score, Score.score < max_score)\
                .distinct().count()
            
            # Get converted leads in this range
            converted_in_range = db.session.query(Lead.id)\
                .join(Score)\
                .filter(
                    Score.score >= min_score,
                    Score.score < max_score,
                    Lead.status == 'Converted'
                ).distinct().count()
            
            conversion_rate = (converted_in_range / leads_in_range * 100) \
                if leads_in_range > 0 else 0
            
            conversion_data.append({
                'range': f"{min_score}-{max_score}",
                'label': label,
                'total_leads': leads_in_range,
                'converted_leads': converted_in_range,
                'conversion_rate': round(conversion_rate, 2)
            })
        
        return jsonify(conversion_data)
    
    except Exception as e:
        logger.error(f"Error getting conversion rates: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/sync/salesforce', methods=['POST'])
def sync_salesforce():
    """Manual sync with Salesforce"""
    try:
        # Get recent leads from Salesforce
        recent_leads = salesforce_client.get_recent_leads()
        
        synced_count = 0
        for sf_lead in recent_leads:
            lead = Lead.query.filter_by(salesforce_id=sf_lead['Id']).first()
            if not lead:
                lead = Lead(
                    salesforce_id=sf_lead['Id'],
                    email=sf_lead.get('Email'),
                    company=sf_lead.get('Company'),
                    status=sf_lead.get('Status')
                )
                db.session.add(lead)
                synced_count += 1
            else:
                # Update existing lead
                lead.status = sf_lead.get('Status')
                lead.company = sf_lead.get('Company')
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'synced_leads': synced_count,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error syncing Salesforce: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=app.config['DEBUG']
    )