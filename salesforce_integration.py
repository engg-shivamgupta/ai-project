"""
Salesforce Integration Module
Handles all Salesforce API interactions for lead scoring system
"""

import os
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class SalesforceClient:
    """Salesforce API client for lead management and Einstein AI integration"""
    
    def __init__(self):
        self.client_id = os.getenv('SALESFORCE_CLIENT_ID')
        self.client_secret = os.getenv('SALESFORCE_CLIENT_SECRET')
        self.username = os.getenv('SALESFORCE_USERNAME')
        self.password = os.getenv('SALESFORCE_PASSWORD')
        self.security_token = os.getenv('SALESFORCE_SECURITY_TOKEN')
        self.sandbox = os.getenv('SALESFORCE_SANDBOX', 'True').lower() == 'true'
        
        self.base_url = 'https://test.salesforce.com' if self.sandbox else 'https://login.salesforce.com'
        self.access_token = None
        self.instance_url = None
        
        # Authenticate on initialization
        self.authenticate()
    
    def authenticate(self) -> bool:
        """Authenticate with Salesforce using OAuth 2.0"""
        try:
            auth_url = f"{self.base_url}/services/oauth2/token"
            
            auth_data = {
                'grant_type': 'password',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'username': self.username,
                'password': f"{self.password}{self.security_token}"
            }
            
            response = requests.post(auth_url, data=auth_data)
            response.raise_for_status()
            
            auth_result = response.json()
            self.access_token = auth_result['access_token']
            self.instance_url = auth_result['instance_url']
            
            logger.info("Successfully authenticated with Salesforce")
            return True
            
        except Exception as e:
            logger.error(f"Salesforce authentication failed: {str(e)}")
            return False
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make authenticated request to Salesforce API"""
        if not self.access_token:
            self.authenticate()
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.instance_url}/services/data/v55.0/{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == 'PATCH':
                response = requests.patch(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                # Token expired, re-authenticate
                self.authenticate()
                headers['Authorization'] = f'Bearer {self.access_token}'
                response = requests.request(method, url, headers=headers, json=data)
                response.raise_for_status()
                return response.json()
            else:
                raise e
    
    def get_lead(self, lead_id: str) -> Optional[Dict]:
        """Retrieve lead information from Salesforce"""
        try:
            endpoint = f"sobjects/Lead/{lead_id}"
            return self._make_request('GET', endpoint)
        except Exception as e:
            logger.error(f"Error retrieving lead {lead_id}: {str(e)}")
            return None
    
    def get_recent_leads(self, days: int = 7) -> List[Dict]:
        """Get leads created in the last N days"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')
            
            query = f"""
                SELECT Id, Email, Company, Status, FirstName, LastName, 
                       Industry, AnnualRevenue, NumberOfEmployees, LeadSource,
                       CreatedDate, LastModifiedDate
                FROM Lead 
                WHERE CreatedDate >= {cutoff_date}
                ORDER BY CreatedDate DESC
            """
            
            endpoint = f"query/?q={requests.utils.quote(query)}"
            result = self._make_request('GET', endpoint)
            
            return result.get('records', [])
            
        except Exception as e:
            logger.error(f"Error retrieving recent leads: {str(e)}")
            return []
    
    def update_lead_score(self, lead_id: str, score_data: Dict) -> bool:
        """Update lead with AI-generated score"""
        try:
            # Custom fields for lead scoring (these need to be created in Salesforce)
            update_data = {
                'AI_Score__c': score_data['score'],
                'Conversion_Probability__c': score_data['probability'],
                'Score_Confidence__c': score_data['confidence'],
                'Last_Scored__c': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                'Model_Version__c': score_data.get('model_version', '1.0')
            }
            
            endpoint = f"sobjects/Lead/{lead_id}"
            self._make_request('PATCH', endpoint, update_data)
            
            logger.info(f"Updated lead {lead_id} with score {score_data['score']}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating lead score for {lead_id}: {str(e)}")
            return False
    
    def create_lead_activity(self, lead_id: str, activity_type: str, description: str) -> bool:
        """Create activity record for lead scoring event"""
        try:
            activity_data = {
                'WhoId': lead_id,
                'Subject': f'AI Lead Scoring - {activity_type}',
                'Description': description,
                'Status': 'Completed',
                'ActivityDate': datetime.utcnow().strftime('%Y-%m-%d'),
                'Type': 'Lead Scoring'
            }
            
            endpoint = "sobjects/Task"
            self._make_request('POST', endpoint, activity_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating activity for lead {lead_id}: {str(e)}")
            return False
    
    def get_lead_activities(self, lead_id: str) -> List[Dict]:
        """Get all activities for a lead"""
        try:
            query = f"""
                SELECT Id, Subject, Description, Status, ActivityDate, CreatedDate
                FROM Task 
                WHERE WhoId = '{lead_id}'
                ORDER BY CreatedDate DESC
            """
            
            endpoint = f"query/?q={requests.utils.quote(query)}"
            result = self._make_request('GET', endpoint)
            
            return result.get('records', [])
            
        except Exception as e:
            logger.error(f"Error retrieving activities for lead {lead_id}: {str(e)}")
            return []
    
    def get_lead_conversion_data(self) -> List[Dict]:
        """Get conversion data for model training"""
        try:
            query = """
                SELECT Id, Email, Company, Status, Industry, AnnualRevenue, 
                       NumberOfEmployees, LeadSource, ConvertedDate,
                       AI_Score__c, Conversion_Probability__c
                FROM Lead 
                WHERE Status IN ('Converted', 'Closed - Not Converted')
                AND AI_Score__c != null
                ORDER BY LastModifiedDate DESC
            """
            
            endpoint = f"query/?q={requests.utils.quote(query)}"
            result = self._make_request('GET', endpoint)
            
            return result.get('records', [])
            
        except Exception as e:
            logger.error(f"Error retrieving conversion data: {str(e)}")
            return []
    
    def execute_einstein_prediction(self, model_id: str, features: Dict) -> Dict:
        """Execute Einstein AI prediction"""
        try:
            prediction_url = f"{self.instance_url}/services/data/v55.0/einstein/prediction"
            
            prediction_data = {
                'modelId': model_id,
                'predictionData': features
            }
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(prediction_url, headers=headers, json=prediction_data)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error executing Einstein prediction: {str(e)}")
            return {'error': str(e)}
    
    def create_einstein_dataset(self, dataset_name: str, data: List[Dict]) -> str:
        """Create Einstein Analytics dataset"""
        try:
            dataset_url = f"{self.instance_url}/services/data/v55.0/einstein/datasets"
            
            dataset_data = {
                'name': dataset_name,
                'type': 'CSV',
                'data': data
            }
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(dataset_url, headers=headers, json=dataset_data)
            response.raise_for_status()
            
            result = response.json()
            return result.get('id')
            
        except Exception as e:
            logger.error(f"Error creating Einstein dataset: {str(e)}")
            return None
    
    def get_lead_engagement_metrics(self, lead_id: str) -> Dict:
        """Get lead engagement metrics from Salesforce"""
        try:
            # Query various engagement objects
            email_query = f"""
                SELECT Id, OpenCount, ClickCount, BounceCount
                FROM EmailMessage 
                WHERE RelatedToId = '{lead_id}'
            """
            
            web_query = f"""
                SELECT Id, PageViews, TimeOnSite, LastVisitDate
                FROM Website_Activity__c 
                WHERE Lead__c = '{lead_id}'
            """
            
            # Execute queries (custom objects may need adjustment)
            email_result = self._make_request('GET', f"query/?q={requests.utils.quote(email_query)}")
            
            # Calculate engagement score
            email_opens = sum(record.get('OpenCount', 0) for record in email_result.get('records', []))
            email_clicks = sum(record.get('ClickCount', 0) for record in email_result.get('records', []))
            
            engagement_score = min(100, (email_opens * 2 + email_clicks * 5))
            
            return {
                'email_opens': email_opens,
                'email_clicks': email_clicks,
                'engagement_score': engagement_score
            }
            
        except Exception as e:
            logger.error(f"Error getting engagement metrics for lead {lead_id}: {str(e)}")
            return {
                'email_opens': 0,
                'email_clicks': 0,
                'engagement_score': 0
            }
    
    def validate_connection(self) -> bool:
        """Validate Salesforce connection"""
        try:
            endpoint = "limits"
            result = self._make_request('GET', endpoint)
            logger.info("Salesforce connection validated successfully")
            return True
        except Exception as e:
            logger.error(f"Salesforce connection validation failed: {str(e)}")
            return False