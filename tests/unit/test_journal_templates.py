"""
Unit tests for journal template functionality.

Tests template CRUD operations, question management, and template-based journal entries.
"""

import pytest
import json
from flask import url_for
from models import JournalTemplate, TemplateQuestion, JournalEntry, GuidedResponse, QuestionManager, db


class TestJournalTemplateCRUD:
    """Test journal template CRUD operations."""
    
    def test_templates_page_loads(self, client, logged_in_user):
        """Test templates page loads correctly."""
        response = client.get('/templates')
        
        assert response.status_code == 200
        assert b'template' in response.data.lower()
        assert b'system' in response.data.lower()
    
    def test_create_template_page_loads(self, client, logged_in_user):
        """Test create template page loads."""
        response = client.get('/templates/create')
        
        assert response.status_code == 200
        assert b'create' in response.data.lower()
        assert b'template' in response.data.lower()
    
    def test_create_basic_template(self, client, logged_in_user, user):
        """Test creating a basic template."""
        data = {
            'name': 'My Custom Template',
            'description': 'A template for daily reflection'
        }
        
        response = client.post('/templates/create', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'successfully' in response.data.lower()
        
        # Check template was created
        template = JournalTemplate.query.filter_by(
            name='My Custom Template',
            user_id=user.id
        ).first()
        assert template is not None
        assert template.description == 'A template for daily reflection'
        assert template.is_system is False
        assert template.user_id == user.id
    
    def test_create_template_empty_name(self, client, logged_in_user):
        """Test creating template with empty name fails."""
        data = {
            'name': '',
            'description': 'Description'
        }
        
        response = client.post('/templates/create', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'required' in response.data.lower()
    
    def test_create_template_long_name(self, client, logged_in_user, user):
        """Test creating template with very long name."""
        long_name = 'A' * 300  # Very long name
        data = {
            'name': long_name,
            'description': 'Test description'
        }
        
        response = client.post('/templates/create', data=data, follow_redirects=True)
        
        # Should handle gracefully (either truncate or show error)
        assert response.status_code == 200
    
    def test_edit_template_page_loads(self, client, logged_in_user, custom_template):
        """Test edit template page loads."""
        response = client.get(f'/templates/{custom_template.id}/edit')
        
        assert response.status_code == 200
        assert custom_template.name.encode() in response.data
        assert b'edit' in response.data.lower()
    
    def test_edit_template_basic(self, client, logged_in_user, custom_template):
        """Test editing a template."""
        new_name = 'Updated Template Name'
        new_description = 'Updated description'
        
        data = {
            'name': new_name,
            'description': new_description
        }
        
        response = client.post(f'/templates/{custom_template.id}/edit', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'updated' in response.data.lower()
        
        # Check template was updated
        db.session.refresh(custom_template)
        assert custom_template.name == new_name
        assert custom_template.description == new_description
    
    def test_edit_other_users_template(self, client, logged_in_user, user_no_email, db_session):
        """Test cannot edit other user's templates."""
        # Create template for different user
        other_template = JournalTemplate(
            name='Other User Template',
            description='Not mine',
            user_id=user_no_email.id,
            is_system=False
        )
        db_session.add(other_template)
        db_session.commit()
        
        response = client.get(f'/templates/{other_template.id}/edit')
        assert response.status_code == 404
        
        # Test POST as well
        response = client.post(f'/templates/{other_template.id}/edit', data={
            'name': 'Hacked',
            'description': 'Hacked'
        })
        assert response.status_code == 404
    
    def test_edit_system_template_forbidden(self, client, logged_in_user, system_template):
        """Test cannot edit system templates."""
        response = client.get(f'/templates/{system_template.id}/edit')
        
        # Should redirect or show error
        assert response.status_code in [403, 404] or b'system' in response.data.lower()
    
    def test_delete_template(self, client, logged_in_user, custom_template):
        """Test deleting a template."""
        template_id = custom_template.id
        
        response = client.post(f'/templates/{template_id}/delete', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'deleted' in response.data.lower()
        
        # Check template was deleted
        deleted_template = JournalTemplate.query.get(template_id)
        assert deleted_template is None
    
    def test_delete_system_template_forbidden(self, client, logged_in_user, system_template):
        """Test cannot delete system templates."""
        template_id = system_template.id
        
        response = client.post(f'/templates/{template_id}/delete')
        
        # Should be forbidden
        assert response.status_code in [403, 404]
        
        # Template should still exist
        existing_template = JournalTemplate.query.get(template_id)
        assert existing_template is not None
    
    def test_delete_other_users_template(self, client, logged_in_user, user_no_email, db_session):
        """Test cannot delete other user's templates."""
        # Create template for different user
        other_template = JournalTemplate(
            name='Other User Template',
            description='Not mine',
            user_id=user_no_email.id,
            is_system=False
        )
        db_session.add(other_template)
        db_session.commit()
        template_id = other_template.id
        
        response = client.post(f'/templates/{template_id}/delete')
        
        assert response.status_code == 404
        
        # Template should still exist
        existing_template = JournalTemplate.query.get(template_id)
        assert existing_template is not None


class TestTemplateQuestionManagement:
    """Test template question management functionality."""
    
    def test_add_text_question(self, client, logged_in_user, custom_template):
        """Test adding a text question to template."""
        data = {
            'text': 'What was the highlight of your day?',
            'type': 'text',
            'required': 'true'
        }
        
        response = client.post(f'/templates/{custom_template.id}/questions/add', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'added' in response.data.lower()
        
        # Check question was created
        question = TemplateQuestion.query.filter_by(
            template_id=custom_template.id,
            text='What was the highlight of your day?'
        ).first()
        assert question is not None
        assert question.question_type == 'text'
        assert question.required is True
    
    def test_add_number_question(self, client, logged_in_user, custom_template):
        """Test adding a number question with min/max values."""
        data = {
            'text': 'Rate your energy level (1-10)',
            'type': 'number',
            'min_value': '1',
            'max_value': '10',
            'required': 'false'
        }
        
        response = client.post(f'/templates/{custom_template.id}/questions/add', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        # Debug: Print response content and question count
        print(f"Response status: {response.status_code}")
        print(f"Response content snippet: {response.data.decode()[:500]}")
        print(f"Question count: {TemplateQuestion.query.filter_by(template_id=custom_template.id).count()}")
        
        # Check question was created with correct values
        question = TemplateQuestion.query.filter_by(
            template_id=custom_template.id,
            question_type='number'
        ).first()
        assert question is not None
        properties = question.get_properties()
        assert properties.get('min') == 1
        assert properties.get('max') == 10
        assert question.required is False
    
    def test_add_boolean_question(self, client, logged_in_user, custom_template):
        """Test adding a boolean question."""
        data = {
            'text': 'Did you exercise today?',
            'type': 'boolean',
            'required': 'true'
        }
        
        response = client.post(f'/templates/{custom_template.id}/questions/add', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Check question was created
        question = TemplateQuestion.query.filter_by(
            template_id=custom_template.id,
            question_type='boolean'
        ).first()
        assert question is not None
        assert question.question_text == 'Did you exercise today?'
    
    def test_add_emotions_question(self, client, logged_in_user, custom_template):
        """Test adding an emotions question."""
        data = {
            'text': 'How are you feeling today?',
            'type': 'emotions',
            'required': 'false'
        }
        
        response = client.post(f'/templates/{custom_template.id}/questions/add', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Check question was created
        question = TemplateQuestion.query.filter_by(
            template_id=custom_template.id,
            question_type='emotions'
        ).first()
        assert question is not None
    
    def test_add_question_with_condition(self, client, logged_in_user, custom_template):
        """Test adding a question with conditional logic."""
        data = {
            'text': 'What type of exercise did you do?',
            'type': 'text',
            'required': 'false',
            'condition_expression': 'exercised_today == true'
        }
        
        response = client.post(f'/templates/{custom_template.id}/questions/add', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Check question was created with condition
        question = TemplateQuestion.query.filter_by(
            template_id=custom_template.id,
            condition_expression='exercised_today == true'
        ).first()
        assert question is not None
    
    def test_add_question_empty_text(self, client, logged_in_user, custom_template):
        """Test adding question with empty text fails."""
        data = {
            'text': '',
            'type': 'text',
            'required': 'true'
        }
        
        response = client.post(f'/templates/{custom_template.id}/questions/add', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'required' in response.data.lower() or b'error' in response.data.lower()
    
    def test_add_question_invalid_number_range(self, client, logged_in_user, custom_template):
        """Test adding number question with invalid min/max."""
        data = {
            'text': 'Invalid range question',
            'type': 'number',
            'min_value': '10',
            'max_value': '5',  # Max less than min
            'required': 'true'
        }
        
        response = client.post(f'/templates/{custom_template.id}/questions/add', data=data, follow_redirects=True)
        
        # Should handle gracefully
        assert response.status_code == 200
    
    def test_delete_question(self, client, logged_in_user, custom_template, template_question):
        """Test deleting a template question."""
        question_id = template_question.id
        
        response = client.post(f'/templates/{custom_template.id}/questions/{question_id}/delete', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'deleted' in response.data.lower()
        
        # Check question was deleted
        deleted_question = TemplateQuestion.query.get(question_id)
        assert deleted_question is None
    
    def test_delete_question_other_template(self, client, logged_in_user, custom_template, user_no_email, db_session):
        """Test cannot delete question from other user's template."""
        # Create template and question for different user
        other_template = JournalTemplate(
            name='Other Template',
            user_id=user_no_email.id,
            is_system=False
        )
        db_session.add(other_template)
        db_session.flush()
        
        other_question = TemplateQuestion(
            template_id=other_template.id,
            text='Other question',
            question_type='text',
            question_order=1
        )
        db_session.add(other_question)
        db_session.commit()
        
        response = client.post(f'/templates/{other_template.id}/questions/{other_question.id}/delete')
        
        assert response.status_code == 404
        
        # Question should still exist
        existing_question = TemplateQuestion.query.get(other_question.id)
        assert existing_question is not None
    
    def test_question_ordering(self, client, logged_in_user, custom_template):
        """Test that questions are ordered correctly."""
        # Add multiple questions
        questions_data = [
            {'text': 'First question', 'type': 'text'},
            {'text': 'Second question', 'type': 'text'},
            {'text': 'Third question', 'type': 'text'}
        ]
        
        for data in questions_data:
            data['required'] = 'false'
            client.post(f'/templates/{custom_template.id}/questions/add', data=data, follow_redirects=True)
        
        # Check questions are ordered correctly
        questions = TemplateQuestion.query.filter_by(
            template_id=custom_template.id
        ).order_by(TemplateQuestion.question_order).all()
        
        assert len(questions) == 3
        assert questions[0].text == 'First question'
        assert questions[1].text == 'Second question'
        assert questions[2].text == 'Third question'
        
        # Check order values
        assert questions[0].question_order == 1
        assert questions[1].question_order == 2
        assert questions[2].question_order == 3


class TestTemplateGuidedJournalEntries:
    """Test creating guided journal entries with templates."""
    
    def test_guided_journal_with_template_loads(self, client, logged_in_user, custom_template_with_questions):
        """Test guided journal page loads with template."""
        response = client.get(f'/journal/guided?template_id={custom_template_with_questions.id}')
        
        assert response.status_code == 200
        assert b'template' in response.data.lower()
        assert custom_template_with_questions.name.encode() in response.data
    
    def test_guided_journal_invalid_template(self, client, logged_in_user):
        """Test guided journal with invalid template ID."""
        response = client.get('/journal/guided?template_id=99999')
        
        # Should fallback to default questions
        assert response.status_code == 200
        assert b'guided' in response.data.lower()
    
    def test_create_guided_entry_with_template(self, client, logged_in_user, user, custom_template_with_questions):
        """Test creating guided entry using custom template."""
        # Get the template questions to build form data
        questions = TemplateQuestion.query.filter_by(
            template_id=custom_template_with_questions.id
        ).all()
        
        # Build form data based on template questions
        data = {
            'template_id': str(custom_template_with_questions.id),
            'tags': [],
            'new_tags': '[]'
        }
        
        # Add responses for each question
        for question in questions:
            question_key = f'question_{question.id}'
            if question.question_type == 'text':
                data[question_key] = f'Response to: {question.question_text}'
            elif question.question_type == 'number':
                data[question_key] = '7'
            elif question.question_type == 'boolean':
                data[question_key] = 'Yes'
            elif question.question_type == 'emotions':
                data[question_key] = '["happy", "excited"]'
        
        response = client.post('/journal/guided', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'successfully' in response.data.lower()
        
        # Check entry was created with template_id
        entry = JournalEntry.query.filter_by(user_id=user.id).first()
        assert entry is not None
        assert entry.entry_type == 'guided'
        assert entry.template_id == custom_template_with_questions.id
        
        # Check guided responses were created with question text
        responses = GuidedResponse.query.filter_by(journal_entry_id=entry.id).all()
        assert len(responses) == len(questions)
        
        # Verify question text was stored
        for response in responses:
            assert response.question_text is not None
            assert response.question_text != ''
            # Should match one of the template questions
            matching_question = next((q for q in questions if str(q.id) == response.question_id), None)
            assert matching_question is not None
            assert response.question_text == matching_question.question_text
    
    def test_view_template_entry_shows_custom_questions(self, client, logged_in_user, template_journal_entry):
        """Test viewing template-based entry shows custom questions."""
        response = client.get(f'/journal/view/{template_journal_entry.id}')
        
        assert response.status_code == 200
        
        # Should show the custom question text that was stored
        guided_responses = GuidedResponse.query.filter_by(
            journal_entry_id=template_journal_entry.id
        ).all()
        
        for guided_response in guided_responses:
            if guided_response.question_text:
                assert guided_response.question_text.encode() in response.data
    
    def test_template_question_conditions_work(self, client, logged_in_user, user):
        """Test template questions with conditions are properly evaluated."""
        # Create template with conditional question
        template = JournalTemplate(
            name='Conditional Template',
            description='Template with conditions',
            user_id=user.id,
            is_system=False
        )
        db.session.add(template)
        db.session.flush()
        
        # Add base question
        base_question = TemplateQuestion(
            template_id=template.id,
            text='Did you exercise today?',
            question_type='boolean',
            question_order=1,
            required=True
        )
        db.session.add(base_question)
        
        # Add conditional question
        conditional_question = TemplateQuestion(
            template_id=template.id,
            text='What type of exercise did you do?',
            question_type='text',
            question_order=2,
            required=False,
            condition_expression='exercised_today == true'
        )
        db.session.add(conditional_question)
        db.session.commit()
        
        # Test that conditional question appears when condition is met
        response = client.get(f'/journal/guided?template_id={template.id}')
        
        assert response.status_code == 200
        # Both questions should be present in the form (condition evaluation happens client-side)
        assert base_question.question_text.encode() in response.data
        assert conditional_question.question_text.encode() in response.data


class TestQuestionManagerIntegration:
    """Test QuestionManager class with template integration."""
    
    def test_get_questions_default(self):
        """Test getting default hardcoded questions."""
        questions = QuestionManager.get_questions()
        
        assert len(questions) > 0
        assert any(q['id'] == 'feeling_scale' for q in questions)
        assert any(q['type'] == 'number' for q in questions)
    
    def test_get_questions_with_template(self, custom_template_with_questions):
        """Test getting questions from template."""
        questions = QuestionManager.get_questions(custom_template_with_questions.id)
        
        assert len(questions) > 0
        # Should return template questions, not hardcoded ones
        template_questions = TemplateQuestion.query.filter_by(
            template_id=custom_template_with_questions.id
        ).all()
        assert len(questions) == len(template_questions)
    
    def test_get_questions_invalid_template(self):
        """Test getting questions with invalid template ID."""
        questions = QuestionManager.get_questions(99999)
        
        # Should fallback to hardcoded questions
        assert len(questions) > 0
        assert any(q['id'] == 'feeling_scale' for q in questions)
    
    def test_template_question_to_dict(self, template_question):
        """Test converting template question to dictionary format."""
        question_dict = template_question.to_dict()
        
        assert 'id' in question_dict
        assert 'text' in question_dict
        assert 'type' in question_dict
        assert 'required' in question_dict
        assert 'condition' in question_dict
        
        assert question_dict['text'] == template_question.question_text
        assert question_dict['type'] == template_question.question_type
        assert question_dict['required'] == template_question.required


class TestTemplateBackwardCompatibility:
    """Test backward compatibility with existing entries."""
    
    def test_view_old_entry_without_question_text(self, client, logged_in_user, guided_journal_entry):
        """Test viewing old guided entry without stored question text."""
        # Ensure the old entry doesn't have question_text
        responses = GuidedResponse.query.filter_by(journal_entry_id=guided_journal_entry.id).all()
        for response in responses:
            response.question_text = None
        db.session.commit()
        
        response = client.get(f'/journal/view/{guided_journal_entry.id}')
        
        assert response.status_code == 200
        # Should still display the entry with fallback question text
        assert b'feeling' in response.data.lower()
    
    def test_old_entries_get_fallback_questions(self, client, logged_in_user, guided_journal_entry):
        """Test that old entries get fallback question text."""
        # Clear question_text to simulate old entry
        responses = GuidedResponse.query.filter_by(journal_entry_id=guided_journal_entry.id).all()
        for response in responses:
            response.question_text = None
        db.session.commit()
        
        response = client.get(f'/journal/view/{guided_journal_entry.id}')
        
        assert response.status_code == 200
        
        # The view should have populated question_text from hardcoded questions
        # Check that the response actually loaded some question text
        assert b'scale' in response.data.lower() or b'feeling' in response.data.lower()