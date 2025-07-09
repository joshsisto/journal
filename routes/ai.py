"""
AI conversation routes for journal application.
"""

from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from models import JournalEntry
from security import limiter
import ai_utils

# AI Blueprint
ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/chat', methods=['POST'])
@limiter.limit("10 per minute")
@login_required
def ai_chat():
    """Handle AI chat messages from dashboard and individual entries."""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'success': False, 'error': 'Message is required'}), 400
        
        message = data['message'].strip()
        if not message:
            return jsonify({'success': False, 'error': 'Message cannot be empty'}), 400
            
        # Validate message length to prevent abuse
        if len(message) > 1000:
            return jsonify({'success': False, 'error': 'Message too long (max 1000 characters)'}), 400
        
        conversation_history = data.get('conversation_history', [])
        entry_id = data.get('entry_id')  # For individual entry conversations
        
        # Get user's recent journal entries for context (changed from 10 to 20)
        recent_entries = JournalEntry.query.filter_by(user_id=current_user.id)\
            .order_by(JournalEntry.created_at.desc())\
            .limit(20).all()
        
        # Build context for AI
        context = {
            'user_id': current_user.id,
            'username': current_user.username,
            'recent_entries': [],
            'conversation_history': conversation_history,
            'specific_entry': None
        }
        
        # Add recent entries to context
        for entry in recent_entries:
            entry_data = {
                'id': entry.id,
                'content': entry.content,
                'created_at': entry.created_at.isoformat(),
                'entry_type': entry.entry_type
            }
            
            # Add guided responses if available
            if entry.entry_type == 'guided':
                entry_data['guided_responses'] = [
                    {
                        'question': response.question_text,
                        'answer': response.response
                    }
                    for response in entry.guided_responses
                ]
            
            context['recent_entries'].append(entry_data)
        
        # If this is about a specific entry, add more details
        if entry_id:
            specific_entry = JournalEntry.query.filter_by(
                id=entry_id, 
                user_id=current_user.id
            ).first()
            
            if specific_entry:
                context['specific_entry'] = {
                    'id': specific_entry.id,
                    'content': specific_entry.content,
                    'created_at': specific_entry.created_at.isoformat(),
                    'entry_type': specific_entry.entry_type,
                    'guided_responses': [
                        {
                            'question': response.question_text,
                            'answer': response.response
                        }
                        for response in specific_entry.guided_responses
                    ] if specific_entry.entry_type == 'guided' else []
                }
        
        # Log the request for debugging
        current_app.logger.info(f'AI chat request from user {current_user.id}: {message[:50]}...')
        
        # Generate AI response using actual AI integration
        ai_response = generate_ai_response(message, context)
        
        # Validate response
        if not ai_response or not isinstance(ai_response, str):
            current_app.logger.error(f'Invalid AI response: {type(ai_response)}')
            return jsonify({'success': False, 'error': 'Failed to generate response'}), 500
        
        return jsonify({
            'success': True,
            'response': ai_response
        })
        
    except Exception as e:
        current_app.logger.error(f"AI chat error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your message'
        }), 500


def generate_ai_response(message, context):
    """Generate AI response using actual AI model integration."""
    try:
        # Convert context entries to format expected by ai_utils
        entries_data = []
        
        # Process recent entries
        for entry in context['recent_entries']:
            entry_dict = {
                'id': entry['id'],
                'content': entry['content'],
                'entry_type': entry['entry_type'],
                'date': datetime.fromisoformat(entry['created_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
            }
            
            # Add guided responses if available
            if entry.get('guided_responses'):
                guided_dict = {}
                for response in entry['guided_responses']:
                    guided_dict[response['question']] = response['answer']
                entry_dict['guided_responses'] = guided_dict
            
            entries_data.append(entry_dict)
        
        # If this is about a specific entry, prioritize it
        if context['specific_entry']:
            specific_entry = context['specific_entry']
            specific_dict = {
                'id': specific_entry['id'],
                'content': specific_entry['content'],
                'entry_type': specific_entry['entry_type'],
                'date': datetime.fromisoformat(specific_entry['created_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
            }
            
            # Add guided responses if available
            if specific_entry.get('guided_responses'):
                guided_dict = {}
                for response in specific_entry['guided_responses']:
                    guided_dict[response['question']] = response['answer']
                specific_dict['guided_responses'] = guided_dict
            
            # Put specific entry at the front
            entries_data.insert(0, specific_dict)
        
        # Use ai_utils to generate response
        response = ai_utils.get_ai_response(entries_data, message)
        return response
        
    except Exception as e:
        current_app.logger.error(f"AI response generation error: {str(e)}")
        # Fallback response
        user_entries_count = len(context['recent_entries'])
        return f"I'm here to help you reflect on your {user_entries_count} recent journal entries. I can discuss themes, emotions, patterns, or provide insights. What would you like to explore?"