"""
Unit tests for journal entry functionality.

Tests quick journal entries, guided journal entries, and related features.
"""

import pytest
import json
import tempfile
from unittest.mock import patch
from flask import url_for
from models import JournalEntry, GuidedResponse, Tag, Photo, db


class TestQuickJournalEntry:
    """Test quick journal entry functionality."""
    
    def test_quick_journal_page_loads(self, client, logged_in_user):
        """Test quick journal page loads correctly."""
        response = client.get('/journal/quick')
        
        assert response.status_code == 200
        assert b'quick' in response.data.lower()
        assert b'content' in response.data.lower()
    
    def test_create_quick_entry_basic(self, client, logged_in_user, user, journal_entry_data):
        """Test creating a basic quick journal entry."""
        response = client.post('/journal/quick', data=journal_entry_data, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'successfully' in response.data.lower()
        
        # Check entry was created
        entry = JournalEntry.query.filter_by(user_id=user.id).first()
        assert entry is not None
        assert entry.content == journal_entry_data['content']
        assert entry.entry_type == 'quick'
        assert entry.user_id == user.id
    
    def test_create_quick_entry_with_tags(self, client, logged_in_user, user, tag):
        """Test creating quick entry with existing tags."""
        data = {
            'content': 'Entry with tags',
            'tags': [str(tag.id)],
            'new_tags': '[]'
        }
        
        response = client.post('/journal/quick', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Check entry was created with tags
        entry = JournalEntry.query.filter_by(user_id=user.id).first()
        assert entry is not None
        assert tag in entry.tags
    
    def test_create_quick_entry_with_new_tags(self, client, logged_in_user, user):
        """Test creating quick entry with new tags."""
        new_tags = ['new-tag-1', 'new-tag-2']
        data = {
            'content': 'Entry with new tags',
            'tags': [],
            'new_tags': json.dumps(new_tags)
        }
        
        response = client.post('/journal/quick', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Check entry was created
        entry = JournalEntry.query.filter_by(user_id=user.id).first()
        assert entry is not None
        
        # Check new tags were created and associated
        assert len(entry.tags) == 2
        tag_names = [tag.name for tag in entry.tags]
        assert 'new-tag-1' in tag_names
        assert 'new-tag-2' in tag_names
    
    def test_create_quick_entry_with_photo(self, client, logged_in_user, user, mock_file_upload):
        """Test creating quick entry with photo upload."""
        test_file = mock_file_upload('test.jpg')
        
        data = {
            'content': 'Entry with photo',
            'tags': [],
            'new_tags': '[]',
            'photos': [test_file]
        }
        
        response = client.post('/journal/quick', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Check entry was created
        entry = JournalEntry.query.filter_by(user_id=user.id).first()
        assert entry is not None
        
        # Check photo was associated
        assert len(entry.photos) == 1
        assert entry.photos[0].filename.endswith('.jpg')
    
    def test_create_quick_entry_empty_content(self, client, logged_in_user):
        """Test creating quick entry with empty content."""
        data = {
            'content': '',
            'tags': [],
            'new_tags': '[]'
        }
        
        response = client.post('/journal/quick', data=data, follow_redirects=True)
        
        # Should handle gracefully - either create empty entry or show error
        assert response.status_code == 200
    
    def test_create_quick_entry_long_content(self, client, logged_in_user, user):
        """Test creating quick entry with very long content."""
        long_content = 'A' * 10000  # Very long content
        data = {
            'content': long_content,
            'tags': [],
            'new_tags': '[]'
        }
        
        response = client.post('/journal/quick', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Check entry was created
        entry = JournalEntry.query.filter_by(user_id=user.id).first()
        assert entry is not None
        assert entry.content == long_content
    
    def test_quick_journal_requires_login(self, client):
        """Test quick journal requires user to be logged in."""
        response = client.get('/journal/quick', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'login' in response.data.lower()
        
        # Test POST also requires login
        response = client.post('/journal/quick', data={'content': 'test'}, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'login' in response.data.lower()
    
    def test_quick_entry_invalid_file_upload(self, client, logged_in_user):
        """Test quick entry with invalid file type."""
        from io import BytesIO
        from werkzeug.datastructures import FileStorage
        
        # Create invalid file type
        invalid_file = FileStorage(
            stream=BytesIO(b'fake content'),
            filename='test.txt',
            content_type='text/plain'
        )
        
        data = {
            'content': 'Entry with invalid file',
            'tags': [],
            'new_tags': '[]',
            'photos': [invalid_file]
        }
        
        response = client.post('/journal/quick', data=data, follow_redirects=True)
        
        # Should show error for invalid file type
        assert response.status_code == 200
        assert b'invalid' in response.data.lower() or b'not allowed' in response.data.lower()


class TestGuidedJournalEntry:
    """Test guided journal entry functionality."""
    
    def test_guided_journal_page_loads(self, client, logged_in_user):
        """Test guided journal page loads correctly."""
        response = client.get('/journal/guided')
        
        assert response.status_code == 200
        assert b'guided' in response.data.lower()
        assert b'feeling' in response.data.lower()
    
    def test_create_guided_entry_basic(self, client, logged_in_user, user, guided_entry_data):
        """Test creating a basic guided journal entry."""
        response = client.post('/journal/guided', data=guided_entry_data, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'successfully' in response.data.lower()
        
        # Check entry was created
        entry = JournalEntry.query.filter_by(user_id=user.id).first()
        assert entry is not None
        assert entry.entry_type == 'guided'
        assert entry.user_id == user.id
        
        # Check guided responses were created
        responses = GuidedResponse.query.filter_by(journal_entry_id=entry.id).all()
        assert len(responses) > 0
        
        # Check specific responses
        feeling_response = next((r for r in responses if r.question_id == 'feeling_scale'), None)
        assert feeling_response is not None
        assert feeling_response.response == guided_entry_data['feeling_scale']
    
    def test_create_guided_entry_all_fields(self, client, logged_in_user, user):
        """Test creating guided entry with all possible fields."""
        data = {
            'feeling_scale': '8',
            'feeling_reason': 'Great day at work',
            'additional_emotions': '["happy", "accomplished", "grateful"]',
            'grateful_for': 'My family and friends',
            'challenge_overcome': 'Finished a difficult project',
            'tomorrow_goal': 'Start learning something new',
            'exercise_activity': 'Running',
            'exercise_duration': '30',
            'tags': [],
            'new_tags': '[]'
        }
        
        response = client.post('/journal/guided', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Check entry was created
        entry = JournalEntry.query.filter_by(user_id=user.id).first()
        assert entry is not None
        
        # Check all responses were saved
        responses = GuidedResponse.query.filter_by(journal_entry_id=entry.id).all()
        response_dict = {r.question_id: r.response for r in responses}
        
        assert response_dict['feeling_scale'] == '8'
        assert response_dict['feeling_reason'] == 'Great day at work'
        assert response_dict['grateful_for'] == 'My family and friends'
    
    def test_create_guided_entry_minimal_fields(self, client, logged_in_user, user):
        """Test creating guided entry with only required fields."""
        data = {
            'feeling_scale': '5',
            'tags': [],
            'new_tags': '[]'
        }
        
        response = client.post('/journal/guided', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Check entry was created
        entry = JournalEntry.query.filter_by(user_id=user.id).first()
        assert entry is not None
        
        # Check at least feeling scale was saved
        feeling_response = GuidedResponse.query.filter_by(
            journal_entry_id=entry.id,
            question_id='feeling_scale'
        ).first()
        assert feeling_response is not None
        assert feeling_response.response == '5'
    
    def test_create_guided_entry_with_tags(self, client, logged_in_user, user, tag):
        """Test creating guided entry with tags."""
        data = {
            'feeling_scale': '7',
            'tags': [str(tag.id)],
            'new_tags': '[]'
        }
        
        response = client.post('/journal/guided', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Check entry has tags
        entry = JournalEntry.query.filter_by(user_id=user.id).first()
        assert entry is not None
        assert tag in entry.tags
    
    def test_create_guided_entry_invalid_feeling_scale(self, client, logged_in_user):
        """Test creating guided entry with invalid feeling scale."""
        data = {
            'feeling_scale': '15',  # Invalid (should be 1-10)
            'tags': [],
            'new_tags': '[]'
        }
        
        response = client.post('/journal/guided', data=data, follow_redirects=True)
        
        # Should handle gracefully
        assert response.status_code == 200
    
    def test_create_guided_entry_with_emotions_json(self, client, logged_in_user, user):
        """Test creating guided entry with emotions as JSON array."""
        emotions = ["happy", "excited", "proud"]
        data = {
            'feeling_scale': '9',
            'additional_emotions': json.dumps(emotions),
            'tags': [],
            'new_tags': '[]'
        }
        
        response = client.post('/journal/guided', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Check emotions were saved correctly
        entry = JournalEntry.query.filter_by(user_id=user.id).first()
        emotions_response = GuidedResponse.query.filter_by(
            journal_entry_id=entry.id,
            question_id='additional_emotions'
        ).first()
        
        assert emotions_response is not None
        saved_emotions = json.loads(emotions_response.response)
        assert saved_emotions == emotions
    
    def test_guided_journal_requires_login(self, client):
        """Test guided journal requires user to be logged in."""
        response = client.get('/journal/guided', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'login' in response.data.lower()


class TestJournalEntryViewing:
    """Test viewing and managing journal entries."""
    
    def test_view_journal_entry(self, client, logged_in_user, journal_entry):
        """Test viewing a single journal entry."""
        response = client.get(f'/journal/view/{journal_entry.id}')
        
        assert response.status_code == 200
        assert journal_entry.content.encode() in response.data
    
    def test_view_guided_journal_entry(self, client, logged_in_user, guided_journal_entry):
        """Test viewing a guided journal entry with responses."""
        response = client.get(f'/journal/view/{guided_journal_entry.id}')
        
        assert response.status_code == 200
        # Should show guided responses
        assert b'feeling' in response.data.lower()
    
    def test_view_nonexistent_entry(self, client, logged_in_user):
        """Test viewing nonexistent entry returns 404."""
        response = client.get('/journal/view/99999')
        
        assert response.status_code == 404
    
    def test_view_other_users_entry(self, client, logged_in_user, user_no_email, db_session):
        """Test cannot view other user's entries."""
        # Create entry for different user
        other_entry = JournalEntry(
            user_id=user_no_email.id,
            content='Other user entry',
            entry_type='quick'
        )
        db_session.add(other_entry)
        db_session.commit()
        
        response = client.get(f'/journal/view/{other_entry.id}')
        
        assert response.status_code == 404
    
    def test_delete_journal_entry(self, client, logged_in_user, journal_entry):
        """Test deleting a journal entry."""
        entry_id = journal_entry.id
        
        response = client.post(f'/journal/delete/{entry_id}', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'deleted' in response.data.lower()
        
        # Check entry was deleted
        deleted_entry = JournalEntry.query.get(entry_id)
        assert deleted_entry is None
    
    def test_delete_other_users_entry(self, client, logged_in_user, user_no_email, db_session):
        """Test cannot delete other user's entries."""
        # Create entry for different user
        other_entry = JournalEntry(
            user_id=user_no_email.id,
            content='Other user entry',
            entry_type='quick'
        )
        db_session.add(other_entry)
        db_session.commit()
        entry_id = other_entry.id
        
        response = client.post(f'/journal/delete/{entry_id}')
        
        assert response.status_code == 404
        
        # Entry should still exist
        existing_entry = JournalEntry.query.get(entry_id)
        assert existing_entry is not None


class TestJournalEntryTags:
    """Test tag functionality with journal entries."""
    
    def test_update_entry_tags(self, client, logged_in_user, journal_entry, tag):
        """Test updating tags on an existing entry."""
        response = client.post(f'/journal/update_tags/{journal_entry.id}', data={
            'tags': [str(tag.id)]
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'updated' in response.data.lower()
        
        # Check tags were updated
        db.session.refresh(journal_entry)
        assert tag in journal_entry.tags
    
    def test_remove_all_tags_from_entry(self, client, logged_in_user, journal_entry, tag):
        """Test removing all tags from an entry."""
        # First add a tag
        journal_entry.tags.append(tag)
        db.session.commit()
        
        # Then remove all tags
        response = client.post(f'/journal/update_tags/{journal_entry.id}', data={
            'tags': []
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Check all tags were removed
        db.session.refresh(journal_entry)
        assert len(journal_entry.tags) == 0
    
    def test_update_tags_other_users_entry(self, client, logged_in_user, user_no_email, db_session):
        """Test cannot update tags on other user's entries."""
        # Create entry for different user
        other_entry = JournalEntry(
            user_id=user_no_email.id,
            content='Other user entry',
            entry_type='quick'
        )
        db_session.add(other_entry)
        db_session.commit()
        
        response = client.post(f'/journal/update_tags/{other_entry.id}', data={
            'tags': []
        })
        
        assert response.status_code == 404


class TestJournalEntrySearch:
    """Test journal entry search functionality."""
    
    def test_search_entries_by_content(self, client, logged_in_user, user, db_session):
        """Test searching entries by content."""
        # Create test entries
        entry1 = JournalEntry(user_id=user.id, content='Searching for happiness', entry_type='quick')
        entry2 = JournalEntry(user_id=user.id, content='Another entry about work', entry_type='quick')
        db_session.add(entry1)
        db_session.add(entry2)
        db_session.commit()
        
        response = client.get('/search?q=happiness')
        
        assert response.status_code == 200
        assert b'happiness' in response.data
        assert b'work' not in response.data
    
    def test_search_entries_by_guided_responses(self, client, logged_in_user, guided_journal_entry):
        """Test searching entries by guided response content."""
        response = client.get('/search?q=Great')  # From guided response
        
        assert response.status_code == 200
        # Should find the guided entry
        assert str(guided_journal_entry.id).encode() in response.data
    
    def test_search_no_results(self, client, logged_in_user):
        """Test search with no matching results."""
        response = client.get('/search?q=nonexistentterm')
        
        assert response.status_code == 200
        # Should show no results message or empty list
        assert b'no' in response.data.lower() or b'found' in response.data.lower()
    
    def test_search_requires_login(self, client):
        """Test search requires login."""
        response = client.get('/search?q=test', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'login' in response.data.lower()


class TestJournalEntryEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_create_entry_large_file_upload(self, client, logged_in_user):
        """Test creating entry with file that's too large."""
        from io import BytesIO
        from werkzeug.datastructures import FileStorage
        
        # Create large file (larger than MAX_CONTENT_LENGTH)
        large_content = b'x' * (20 * 1024 * 1024)  # 20MB
        large_file = FileStorage(
            stream=BytesIO(large_content),
            filename='large.jpg',
            content_type='image/jpeg'
        )
        
        data = {
            'content': 'Entry with large file',
            'tags': [],
            'new_tags': '[]',
            'photos': [large_file]
        }
        
        response = client.post('/journal/quick', data=data, follow_redirects=True)
        
        # Should reject large file
        assert response.status_code in [200, 413]  # 413 = Request Entity Too Large
    
    def test_create_entry_with_malicious_content(self, client, logged_in_user, user):
        """Test creating entry with potentially malicious content."""
        malicious_content = '<script>alert("xss")</script>'
        data = {
            'content': malicious_content,
            'tags': [],
            'new_tags': '[]'
        }
        
        response = client.post('/journal/quick', data=data, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Check content was sanitized
        entry = JournalEntry.query.filter_by(user_id=user.id).first()
        assert entry is not None
        # Content should be sanitized (exact behavior depends on sanitization library)
        assert '<script>' not in entry.content
    
    def test_create_entry_concurrent_users(self, client, app, user, user_no_email):
        """Test creating entries concurrently doesn't cause issues."""
        with app.test_client() as client1, app.test_client() as client2:
            # Login both users
            with client1.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            with client2.session_transaction() as sess:
                sess['_user_id'] = str(user_no_email.id)
                sess['_fresh'] = True
            
            # Create entries simultaneously
            data1 = {'content': 'User 1 entry', 'tags': [], 'new_tags': '[]'}
            data2 = {'content': 'User 2 entry', 'tags': [], 'new_tags': '[]'}
            
            response1 = client1.post('/journal/quick', data=data1, follow_redirects=True)
            response2 = client2.post('/journal/quick', data=data2, follow_redirects=True)
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            
            # Check both entries were created for correct users
            user1_entries = JournalEntry.query.filter_by(user_id=user.id).all()
            user2_entries = JournalEntry.query.filter_by(user_id=user_no_email.id).all()
            
            assert len(user1_entries) >= 1
            assert len(user2_entries) >= 1