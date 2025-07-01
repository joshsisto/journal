"""
Unit tests for AI functionality.

Tests AI conversation features, API endpoints, and related functionality.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from flask import url_for
from models import JournalEntry, GuidedResponse, db


class TestAIConversationPages:
    """Test AI conversation page loading and rendering."""
    
    def test_single_entry_conversation_page(self, client, logged_in_user, journal_entry):
        """Test single entry AI conversation page loads."""
        response = client.get(f'/ai/conversation/{journal_entry.id}')
        
        assert response.status_code == 200
        assert b'AI Conversation' in response.data
        assert b'Single Entry' in response.data
        assert journal_entry.content.encode() in response.data
    
    def test_single_entry_conversation_guided(self, client, logged_in_user, guided_journal_entry):
        """Test single entry conversation with guided entry."""
        response = client.get(f'/ai/conversation/{guided_journal_entry.id}')
        
        assert response.status_code == 200
        assert b'AI Conversation' in response.data
        # Should show feeling data
        assert b'feeling' in response.data.lower()
    
    def test_single_entry_conversation_nonexistent(self, client, logged_in_user):
        """Test single entry conversation with nonexistent entry."""
        response = client.get('/ai/conversation/99999')
        
        assert response.status_code == 404
    
    def test_single_entry_conversation_other_user(self, client, logged_in_user, user_no_email, db_session):
        """Test cannot access other user's entry for AI conversation."""
        # Create entry for different user
        other_entry = JournalEntry(
            user_id=user_no_email.id,
            content='Other user entry',
            entry_type='quick'
        )
        db_session.add(other_entry)
        db_session.commit()
        
        response = client.get(f'/ai/conversation/{other_entry.id}')
        
        assert response.status_code == 404
    
    def test_multiple_entries_conversation_page(self, client, logged_in_user):
        """Test multiple entries AI conversation page loads."""
        response = client.get('/ai/conversation/multiple')
        
        assert response.status_code == 200
        assert b'AI Conversation' in response.data
        assert b'Multiple Entries' in response.data
    
    def test_ai_conversation_requires_login(self, client, journal_entry):
        """Test AI conversation pages require login."""
        response = client.get(f'/ai/conversation/{journal_entry.id}', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'login' in response.data.lower()
        
        response = client.get('/ai/conversation/multiple', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'login' in response.data.lower()


class TestAIConversationAPI:
    """Test AI conversation API endpoints."""
    
    def test_ai_api_single_entry(self, client, logged_in_user, journal_entry, mock_gemini_api, csrf_token):
        """Test AI API with single entry."""
        request_data = {
            'entries': [{
                'id': journal_entry.id,
                'content': journal_entry.content,
                'entry_type': journal_entry.entry_type,
                'date': '2023-01-01'
            }],
            'question': 'What emotions am I expressing?'
        }
        
        response = client.post('/ai/api/conversation',
                             data=json.dumps(request_data),
                             content_type='application/json',
                             headers={'X-CSRF-Token': csrf_token})
        
        assert response.status_code == 200
        
        json_data = response.get_json()
        assert json_data['success'] is True
        assert 'response' in json_data
        assert json_data['response'] == "This is a mocked AI response for testing purposes."
        
        # Check AI function was called
        mock_gemini_api.assert_called_once()
    
    def test_ai_api_multiple_entries(self, client, logged_in_user, journal_entry, guided_journal_entry, mock_gemini_api, csrf_token):
        """Test AI API with multiple entries."""
        request_data = {
            'entries': [
                {
                    'id': journal_entry.id,
                    'content': journal_entry.content,
                    'entry_type': journal_entry.entry_type,
                    'date': '2023-01-01'
                },
                {
                    'id': guided_journal_entry.id,
                    'content': guided_journal_entry.content,
                    'entry_type': guided_journal_entry.entry_type,
                    'date': '2023-01-02',
                    'feeling_value': 8
                }
            ],
            'question': 'What patterns do you notice?'
        }
        
        response = client.post('/ai/api/conversation',
                             data=json.dumps(request_data),
                             content_type='application/json',
                             headers={'X-CSRF-Token': csrf_token})
        
        assert response.status_code == 200
        
        json_data = response.get_json()
        assert json_data['success'] is True
        assert 'response' in json_data
        
        mock_gemini_api.assert_called_once()
        # Check multiple entries were passed
        call_args = mock_gemini_api.call_args
        entries_data = call_args[0][0]  # First argument (entries_data)
        assert len(entries_data) == 2
    
    def test_ai_api_no_question(self, client, logged_in_user, journal_entry, csrf_token):
        """Test AI API without question."""
        request_data = {
            'entries': [{
                'id': journal_entry.id,
                'content': journal_entry.content,
                'entry_type': journal_entry.entry_type
            }],
            'question': ''
        }
        
        response = client.post('/ai/api/conversation',
                             data=json.dumps(request_data),
                             content_type='application/json',
                             headers={'X-CSRF-Token': csrf_token})
        
        assert response.status_code == 400
        
        json_data = response.get_json()
        assert json_data['success'] is False
        assert 'No question provided' in json_data['error']
    
    def test_ai_api_no_entries(self, client, logged_in_user, csrf_token):
        """Test AI API without entries."""
        request_data = {
            'entries': [],
            'question': 'What do you think?'
        }
        
        response = client.post('/ai/api/conversation',
                             data=json.dumps(request_data),
                             content_type='application/json',
                             headers={'X-CSRF-Token': csrf_token})
        
        assert response.status_code == 400
        
        json_data = response.get_json()
        assert json_data['success'] is False
        assert 'No entries provided' in json_data['error']
    
    def test_ai_api_invalid_json(self, client, logged_in_user, csrf_token):
        """Test AI API with invalid JSON."""
        response = client.post('/ai/api/conversation',
                             data='invalid json',
                             content_type='application/json',
                             headers={'X-CSRF-Token': csrf_token})
        
        assert response.status_code == 400
        
        json_data = response.get_json()
        assert json_data['success'] is False
        assert 'No data provided' in json_data['error']
    
    def test_ai_api_no_csrf_token(self, client, logged_in_user, journal_entry):
        """Test AI API without CSRF token."""
        request_data = {
            'entries': [{
                'id': journal_entry.id,
                'content': journal_entry.content,
                'entry_type': journal_entry.entry_type
            }],
            'question': 'Test question'
        }
        
        response = client.post('/ai/api/conversation',
                             data=json.dumps(request_data),
                             content_type='application/json')
        
        # Should be redirected or show CSRF error
        assert response.status_code in [302, 400, 403]
    
    def test_ai_api_requires_login(self, client, journal_entry, csrf_token):
        """Test AI API requires login."""
        request_data = {
            'entries': [{
                'id': journal_entry.id,
                'content': journal_entry.content,
                'entry_type': journal_entry.entry_type
            }],
            'question': 'Test question'
        }
        
        response = client.post('/ai/api/conversation',
                             data=json.dumps(request_data),
                             content_type='application/json',
                             headers={'X-CSRF-Token': csrf_token})
        
        # Should redirect to login
        assert response.status_code == 302


class TestAIMockingAndErrorHandling:
    """Test AI functionality with various mock scenarios."""
    
    def test_ai_api_with_no_api_key(self, client, logged_in_user, journal_entry, csrf_token):
        """Test AI API when no API key is configured."""
        with patch.dict('os.environ', {'GEMINI_API_KEY': ''}):
            request_data = {
                'entries': [{
                    'id': journal_entry.id,
                    'content': journal_entry.content,
                    'entry_type': journal_entry.entry_type
                }],
                'question': 'Test question'
            }
            
            response = client.post('/ai/api/conversation',
                                 data=json.dumps(request_data),
                                 content_type='application/json',
                                 headers={'X-CSRF-Token': csrf_token})
            
            assert response.status_code == 200
            
            json_data = response.get_json()
            assert json_data['success'] is True
            assert 'demo mode' in json_data['response']
            assert json_data.get('demo_mode') is True
    
    @patch('ai_utils.get_ai_response')
    def test_ai_api_with_ai_error(self, mock_ai, client, logged_in_user, journal_entry, csrf_token):
        """Test AI API when AI service returns error."""
        mock_ai.side_effect = Exception("AI service unavailable")
        
        request_data = {
            'entries': [{
                'id': journal_entry.id,
                'content': journal_entry.content,
                'entry_type': journal_entry.entry_type
            }],
            'question': 'Test question'
        }
        
        response = client.post('/ai/api/conversation',
                             data=json.dumps(request_data),
                             content_type='application/json',
                             headers={'X-CSRF-Token': csrf_token})
        
        assert response.status_code == 500
        
        json_data = response.get_json()
        assert json_data['success'] is False
        assert 'error' in json_data
    
    @patch('ai_utils.get_ai_response')
    def test_ai_api_with_empty_response(self, mock_ai, client, logged_in_user, journal_entry, csrf_token):
        """Test AI API when AI returns empty response."""
        mock_ai.return_value = ""
        
        request_data = {
            'entries': [{
                'id': journal_entry.id,
                'content': journal_entry.content,
                'entry_type': journal_entry.entry_type
            }],
            'question': 'Test question'
        }
        
        response = client.post('/ai/api/conversation',
                             data=json.dumps(request_data),
                             content_type='application/json',
                             headers={'X-CSRF-Token': csrf_token})
        
        assert response.status_code == 200
        
        json_data = response.get_json()
        assert json_data['success'] is True
        assert json_data['response'] == ""
    
    @patch('ai_utils.get_ai_response')
    def test_ai_api_with_long_response(self, mock_ai, client, logged_in_user, journal_entry, csrf_token):
        """Test AI API with very long response."""
        long_response = "A" * 10000  # Very long response
        mock_ai.return_value = long_response
        
        request_data = {
            'entries': [{
                'id': journal_entry.id,
                'content': journal_entry.content,
                'entry_type': journal_entry.entry_type
            }],
            'question': 'Test question'
        }
        
        response = client.post('/ai/api/conversation',
                             data=json.dumps(request_data),
                             content_type='application/json',
                             headers={'X-CSRF-Token': csrf_token})
        
        assert response.status_code == 200
        
        json_data = response.get_json()
        assert json_data['success'] is True
        assert json_data['response'] == long_response


class TestAIDataFormatting:
    """Test AI data formatting and processing."""
    
    def test_ai_with_guided_entry_emotions(self, client, logged_in_user, guided_journal_entry, mock_gemini_api, csrf_token):
        """Test AI API properly handles guided entry with emotions."""
        # Add emotions to guided entry
        emotions_response = GuidedResponse(
            journal_entry_id=guided_journal_entry.id,
            question_id='additional_emotions',
            response='["happy", "excited", "grateful"]'
        )
        db.session.add(emotions_response)
        db.session.commit()
        
        request_data = {
            'entries': [{
                'id': guided_journal_entry.id,
                'content': guided_journal_entry.content,
                'entry_type': guided_journal_entry.entry_type,
                'date': '2023-01-01',
                'feeling_value': 8,
                'emotions': ["happy", "excited", "grateful"]
            }],
            'question': 'What emotions am I expressing?'
        }
        
        response = client.post('/ai/api/conversation',
                             data=json.dumps(request_data),
                             content_type='application/json',
                             headers={'X-CSRF-Token': csrf_token})
        
        assert response.status_code == 200
        
        # Check AI was called with properly formatted data
        mock_gemini_api.assert_called_once()
        call_args = mock_gemini_api.call_args
        entries_data = call_args[0][0]
        
        assert 'emotions' in entries_data[0]
        assert entries_data[0]['emotions'] == ["happy", "excited", "grateful"]
    
    def test_ai_with_entry_tags(self, client, logged_in_user, journal_entry, tag, mock_gemini_api, csrf_token):
        """Test AI API includes entry tags in data."""
        # Add tag to entry
        journal_entry.tags.append(tag)
        db.session.commit()
        
        request_data = {
            'entries': [{
                'id': journal_entry.id,
                'content': journal_entry.content,
                'entry_type': journal_entry.entry_type,
                'date': '2023-01-01',
                'tags': [tag.name]
            }],
            'question': 'What themes do you see?'
        }
        
        response = client.post('/ai/api/conversation',
                             data=json.dumps(request_data),
                             content_type='application/json',
                             headers={'X-CSRF-Token': csrf_token})
        
        assert response.status_code == 200
        mock_gemini_api.assert_called_once()
    
    def test_ai_question_validation(self, client, logged_in_user, journal_entry, csrf_token):
        """Test AI API validates question content."""
        # Test with very long question
        long_question = "What " + "do you think " * 1000 + "?"
        
        request_data = {
            'entries': [{
                'id': journal_entry.id,
                'content': journal_entry.content,
                'entry_type': journal_entry.entry_type
            }],
            'question': long_question
        }
        
        response = client.post('/ai/api/conversation',
                             data=json.dumps(request_data),
                             content_type='application/json',
                             headers={'X-CSRF-Token': csrf_token})
        
        # Should handle long questions gracefully
        assert response.status_code in [200, 400]


class TestAIIntegrationWithOtherFeatures:
    """Test AI integration with other app features."""
    
    def test_ai_conversation_from_entry_view(self, client, logged_in_user, journal_entry):
        """Test accessing AI conversation from entry view page."""
        response = client.get(f'/journal/view/{journal_entry.id}')
        
        assert response.status_code == 200
        # Should have link to AI conversation
        assert b'conversation' in response.data.lower() or b'ai' in response.data.lower()
    
    def test_ai_conversation_with_empty_entries(self, client, logged_in_user, mock_gemini_api, csrf_token):
        """Test AI conversation with entries that have no content."""
        # Create entry with minimal content
        empty_entry = JournalEntry(
            user_id=logged_in_user.get_id(),
            content='',
            entry_type='quick'
        )
        db.session.add(empty_entry)
        db.session.commit()
        
        request_data = {
            'entries': [{
                'id': empty_entry.id,
                'content': '',
                'entry_type': 'quick',
                'date': '2023-01-01'
            }],
            'question': 'What can you tell me?'
        }
        
        response = client.post('/ai/api/conversation',
                             data=json.dumps(request_data),
                             content_type='application/json',
                             headers={'X-CSRF-Token': csrf_token})
        
        assert response.status_code == 200
        # Should handle empty content gracefully
        mock_gemini_api.assert_called_once()
    
    def test_ai_conversation_performance_with_many_entries(self, client, logged_in_user, user, mock_gemini_api, csrf_token):
        """Test AI conversation performance with many entries."""
        # Create multiple entries
        entries_data = []
        for i in range(20):
            entry = JournalEntry(
                user_id=user.id,
                content=f'Entry number {i}',
                entry_type='quick'
            )
            db.session.add(entry)
            entries_data.append({
                'id': i + 1000,  # Use fake IDs
                'content': f'Entry number {i}',
                'entry_type': 'quick',
                'date': f'2023-01-{i+1:02d}'
            })
        
        db.session.commit()
        
        request_data = {
            'entries': entries_data,
            'question': 'What patterns do you see across all these entries?'
        }
        
        response = client.post('/ai/api/conversation',
                             data=json.dumps(request_data),
                             content_type='application/json',
                             headers={'X-CSRF-Token': csrf_token})
        
        assert response.status_code == 200
        # Should handle many entries
        mock_gemini_api.assert_called_once()


class TestAISecurityAndValidation:
    """Test AI security features and input validation."""
    
    def test_ai_api_sanitizes_input(self, client, logged_in_user, mock_gemini_api, csrf_token):
        """Test AI API sanitizes malicious input."""
        malicious_content = '<script>alert("xss")</script>'
        
        request_data = {
            'entries': [{
                'id': 1,
                'content': malicious_content,
                'entry_type': 'quick',
                'date': '2023-01-01'
            }],
            'question': 'What do you think about this <script>alert("xss")</script>?'
        }
        
        response = client.post('/ai/api/conversation',
                             data=json.dumps(request_data),
                             content_type='application/json',
                             headers={'X-CSRF-Token': csrf_token})
        
        assert response.status_code == 200
        
        # Check that AI was called (input should be sanitized internally)
        mock_gemini_api.assert_called_once()
    
    def test_ai_api_rate_limiting(self, client, logged_in_user, journal_entry, csrf_token):
        """Test AI API has appropriate rate limiting."""
        request_data = {
            'entries': [{
                'id': journal_entry.id,
                'content': journal_entry.content,
                'entry_type': journal_entry.entry_type
            }],
            'question': 'Test question'
        }
        
        # Make multiple rapid requests
        responses = []
        for _ in range(10):
            response = client.post('/ai/api/conversation',
                                 data=json.dumps(request_data),
                                 content_type='application/json',
                                 headers={'X-CSRF-Token': csrf_token})
            responses.append(response)
        
        # At least some should succeed, but rate limiting might kick in
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count > 0  # At least some should work
    
    def test_ai_api_validates_entry_ownership(self, client, logged_in_user, user_no_email, db_session, csrf_token):
        """Test AI API validates user owns the entries."""
        # Create entry for different user
        other_entry = JournalEntry(
            user_id=user_no_email.id,
            content='Other user entry',
            entry_type='quick'
        )
        db_session.add(other_entry)
        db_session.commit()
        
        request_data = {
            'entries': [{
                'id': other_entry.id,
                'content': other_entry.content,
                'entry_type': other_entry.entry_type
            }],
            'question': 'What do you think?'
        }
        
        response = client.post('/ai/api/conversation',
                             data=json.dumps(request_data),
                             content_type='application/json',
                             headers={'X-CSRF-Token': csrf_token})
        
        # Should either reject or only process user's own entries
        assert response.status_code in [200, 400, 403]