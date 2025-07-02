"""
Tests for Content Security Policy and JavaScript functionality.

These tests ensure that:
1. All inline scripts have proper CSP nonces
2. JavaScript functionality works as expected
3. CSP doesn't block legitimate scripts
"""
import pytest
import re
from bs4 import BeautifulSoup


class TestCSPJavaScript:
    """Test CSP nonce implementation and JavaScript functionality."""
    
    def test_guided_journal_scripts_have_nonces(self, client, logged_in_user):
        """Test that all inline scripts in guided journal have CSP nonces."""
        response = client.get('/journal/guided')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        inline_scripts = soup.find_all('script', src=False)
        
        # Filter out empty scripts
        inline_scripts = [script for script in inline_scripts if script.string and script.string.strip()]
        
        assert len(inline_scripts) > 0, "Should have inline scripts to test"
        
        for script in inline_scripts:
            assert script.get('nonce'), f"Inline script missing nonce: {script.string[:50]}..."
            
            # Verify nonce format (should be base64-like string)
            nonce = script.get('nonce')
            assert len(nonce) > 10, f"Nonce too short: {nonce}"
            assert re.match(r'^[A-Za-z0-9+/=]+$', nonce), f"Invalid nonce format: {nonce}"
    
    def test_emotion_selection_javascript_structure(self, client, logged_in_user):
        """Test that emotion selection JavaScript has correct structure."""
        response = client.get('/journal/guided')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find the emotion selection script
        emotion_script = None
        for script in soup.find_all('script'):
            if script.string and 'emotion-checkbox' in script.string:
                emotion_script = script.string
                break
        
        assert emotion_script, "Should have emotion selection JavaScript"
        
        # Check for required JavaScript elements
        required_elements = [
            'document.querySelectorAll(\'.emotion-checkbox\')',
            'getElementById(\'question_',
            'addEventListener(\'change\'',
            'JSON.stringify(allSelected)',
            'selectedEmotions[category]'
        ]
        
        for element in required_elements:
            assert element in emotion_script, f"Missing required JavaScript element: {element}"
    
    def test_happiness_slider_javascript_structure(self, client, logged_in_user):
        """Test that happiness slider JavaScript has correct structure."""
        response = client.get('/journal/guided')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find the slider script
        slider_script = None
        for script in soup.find_all('script'):
            if script.string and '_range\').addEventListener(\'input\'' in script.string:
                slider_script = script.string
                break
        
        assert slider_script, "Should have slider JavaScript"
        
        # Check for emoji mapping
        emoji_checks = [
            'if (value == 1) emoji = \'😭\'',
            'if (value == 5) emoji = \'😐\'',
            'if (value == 10) emoji = \'🤩\''
        ]
        
        for check in emoji_checks:
            assert check in slider_script, f"Missing emoji mapping: {check}"
    
    def test_form_elements_exist(self, client, logged_in_user):
        """Test that required form elements exist for JavaScript to target."""
        response = client.get('/journal/guided')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check for emotion-related elements
        emotion_checkboxes = soup.find_all('input', class_='emotion-checkbox')
        assert len(emotion_checkboxes) > 0, "Should have emotion checkboxes"
        
        # Check for hidden emotion input
        emotion_input = soup.find('input', attrs={'name': lambda x: x and 'additional_emotions' in x})
        assert emotion_input, "Should have hidden emotion input field"
        
        # Check for emotion display area
        emotion_display = soup.find('div', id='selected_emotions_display')
        assert emotion_display, "Should have emotion display area"
        
        # Check for happiness slider
        happiness_slider = soup.find('input', type='range')
        assert happiness_slider, "Should have happiness slider"
    
    def test_no_inline_scripts_without_nonces(self, client, logged_in_user):
        """Test that no inline scripts exist without nonces."""
        response = client.get('/journal/guided')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find all script tags
        all_scripts = soup.find_all('script')
        
        for script in all_scripts:
            # Skip external scripts (they don't need nonces)
            if script.get('src'):
                continue
                
            # Skip empty scripts
            if not script.string or not script.string.strip():
                continue
            
            # This script should have a nonce
            assert script.get('nonce'), f"Inline script without nonce found: {script.string[:100]}..."
    
    def test_csp_meta_tag_exists(self, client, logged_in_user):
        """Test that CSP is properly configured (check for nonce in CSP header)."""
        response = client.get('/journal/guided')
        
        # Check for CSP header
        csp_header = response.headers.get('Content-Security-Policy')
        if csp_header:
            # Should contain nonce for script-src
            assert "'nonce-" in csp_header, "CSP header should contain nonce for scripts"
    
    def test_javascript_variables_properly_templated(self, client, logged_in_user):
        """Test that template variables in JavaScript are properly rendered."""
        response = client.get('/journal/guided')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find emotion script
        emotion_script = None
        for script in soup.find_all('script'):
            if script.string and 'question_' in script.string and 'emotion' in script.string:
                emotion_script = script.string
                break
        
        if emotion_script:
            # Should not contain unrendered template variables
            assert '{{ question.id }}' not in emotion_script, "Template variables should be rendered"
            assert 'question_additional_emotions' in emotion_script, "Should contain rendered question ID"


class TestJavaScriptFunctionality:
    """Test JavaScript functionality through server-side form processing."""
    
    def test_emotion_data_format_accepted(self, client, logged_in_user):
        """Test that emotion data in correct JSON format is accepted."""
        # Test various emotion combinations
        emotion_data_tests = [
            '["Happy"]',
            '["Happy", "Excited"]',
            '["Happy", "Excited", "Grateful"]',
            '[]',  # Empty selection
        ]
        
        for emotion_json in emotion_data_tests:
            data = {
                'question_feeling_scale': '7',
                'question_additional_emotions': emotion_json,
                'question_feeling_reason': 'Test response',
                'tags': [],
                'new_tags': '[]'
            }
            
            response = client.post('/journal/guided', data=data, follow_redirects=True)
            
            # Should succeed (not get blocked by security)
            assert response.status_code == 200
            assert b'successfully' in response.data or b'success' in response.data.lower()
    
    def test_malformed_emotion_data_handling(self, client, logged_in_user):
        """Test handling of malformed emotion data."""
        malformed_data_tests = [
            'not_json',
            '{"invalid": "format"}',
            '[unclosed array',
            '"string instead of array"'
        ]
        
        for malformed_json in malformed_data_tests:
            data = {
                'question_feeling_scale': '7',
                'question_additional_emotions': malformed_json,
                'question_feeling_reason': 'Test response',
                'tags': [],
                'new_tags': '[]'
            }
            
            response = client.post('/journal/guided', data=data, follow_redirects=True)
            
            # Should handle gracefully (not crash the app)
            assert response.status_code in [200, 400], f"Unexpected status for malformed data: {malformed_json}"