"""API routes for templates, weather, and location services."""
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user

from models import JournalTemplate, TemplateQuestion, Location
from services.weather_service import weather_service

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/templates/<int:template_id>/questions')
@login_required
def get_template_questions(template_id):
    """API endpoint to get questions for a specific template"""
    # Get template and verify access
    template = JournalTemplate.query.get_or_404(template_id)
    
    # Check if user has access to this template (system templates or own templates)
    if not template.is_system and template.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    # Get questions for this template
    questions = []
    for question in template.questions.order_by(TemplateQuestion.question_order):
        questions.append({
            'question_id': question.question_id,
            'question_text': question.question_text,
            'question_type': question.question_type,
            'required': question.required,
            'properties': question.properties
        })
    
    return jsonify({
        'success': True,
        'template_name': template.name,
        'questions': questions
    })


@api_bp.route('/weather/current', methods=['POST'])
@login_required
def get_weather():
    """Get current weather for coordinates"""
    try:
        data = request.get_json()
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not latitude or not longitude:
            return jsonify({'error': 'Missing coordinates'}), 400
            
        weather_data = weather_service.get_weather_by_coordinates(latitude, longitude)
        
        if weather_data:
            return jsonify(weather_data)
        else:
            return jsonify({'error': 'Weather data unavailable'}), 503
            
    except Exception as e:
        current_app.logger.error(f"Error fetching weather: {e}")
        return jsonify({'error': 'Weather service error'}), 500


@api_bp.route('/location/reverse-geocode', methods=['POST'])
@login_required
def reverse_geocode():
    """Reverse geocode coordinates to location"""
    try:
        data = request.get_json()
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not latitude or not longitude:
            return jsonify({'error': 'Missing coordinates'}), 400
            
        location_info = weather_service.reverse_geocode(latitude, longitude)
        
        if location_info:
            return jsonify(location_info)
        else:
            return jsonify({'error': 'Location information unavailable'}), 503
            
    except Exception as e:
        current_app.logger.error(f"Error reverse geocoding: {e}")
        return jsonify({'error': 'Geocoding service error'}), 500


@api_bp.route('/location/search', methods=['POST'])
@login_required
def search_location():
    """Search for location by name"""
    try:
        data = request.get_json()
        location_name = data.get('location_name')
        
        if not location_name:
            return jsonify({'error': 'Missing location name'}), 400
            
        # First try to geocode the location
        coordinates = weather_service.geocode_location(location_name)
        
        if coordinates:
            latitude, longitude = coordinates
            # Get detailed location info
            location_info = weather_service.reverse_geocode(latitude, longitude)
            
            if location_info:
                location_info['latitude'] = latitude
                location_info['longitude'] = longitude
                return jsonify(location_info)
            else:
                # Just return coordinates if reverse geocoding fails
                return jsonify({
                    'latitude': latitude,
                    'longitude': longitude,
                    'name': location_name
                })
        else:
            return jsonify({'error': 'Location not found'}), 404
            
    except Exception as e:
        current_app.logger.error(f"Error searching location: {e}")
        return jsonify({'error': 'Location search error'}), 500


@api_bp.route('/location/<int:location_id>', methods=['GET'])
@login_required
def get_location(location_id):
    """Get location by ID"""
    try:
        location = Location.query.get_or_404(location_id)
        
        location_data = {
            'id': location.id,
            'name': location.name,
            'latitude': location.latitude,
            'longitude': location.longitude,
            'city': location.city,
            'state': location.state,
            'country': location.country,
            'address': location.address
        }
        
        return jsonify(location_data)
        
    except Exception as e:
        current_app.logger.error(f"Error getting location: {e}")
        return jsonify({'error': 'Location not found'}), 404