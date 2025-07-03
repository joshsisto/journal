#!/usr/bin/env python3
"""
Database migration script to add journal template system.

This script adds:
1. journal_templates table
2. template_questions table  
3. template_id column to journal_entries
4. Default system template with current hardcoded questions
"""

from app import create_app
from models import db, JournalTemplate, TemplateQuestion
import json

def create_default_system_template():
    """Create the default system template with current hardcoded questions."""
    
    # Create the default template
    default_template = JournalTemplate(
        name="Default Guided Journal",
        description="The original guided journal questions for comprehensive daily reflection",
        user_id=None,  # System template
        is_system=True
    )
    
    db.session.add(default_template)
    db.session.flush()  # Get the ID
    
    # Current hardcoded questions converted to template format
    questions_data = [
        {
            'question_id': 'feeling_scale',
            'question_text': 'How are you feeling on a scale of 1-10?',
            'question_type': 'number',
            'question_order': 1,
            'required': True,
            'properties': {'min': 1, 'max': 10},
            'condition_expression': None  # Always show
        },
        {
            'question_id': 'additional_emotions',
            'question_text': 'Select additional emotions you\'re experiencing:',
            'question_type': 'emotions',
            'question_order': 2,
            'required': False,
            'properties': {},
            'condition_expression': None  # Always show
        },
        {
            'question_id': 'feeling_reason',
            'question_text': 'Why do you feel that way?',
            'question_type': 'text',
            'question_order': 3,
            'required': False,
            'properties': {},
            'condition_expression': None  # Always show
        },
        {
            'question_id': 'since_last_entry',
            'question_text': "It's been {time_since} since your last journal entry. What's happened since then?",
            'question_type': 'text',
            'question_order': 4,
            'required': False,
            'properties': {},
            'condition_expression': 'hours_since_last_entry >= 8'
        },
        {
            'question_id': 'about_day',
            'question_text': 'Tell me about your day.',
            'question_type': 'text',
            'question_order': 5,
            'required': False,
            'properties': {},
            'condition_expression': None  # Always show
        },
        {
            'question_id': 'exercise',
            'question_text': 'Did you exercise today?',
            'question_type': 'boolean',
            'question_order': 6,
            'required': False,
            'properties': {},
            'condition_expression': 'exercised_today == false'
        },
        {
            'question_id': 'exercise_type',
            'question_text': 'What type of workout did you do?',
            'question_type': 'text',
            'question_order': 7,
            'required': False,
            'properties': {},
            'condition_expression': 'exercise_response == "Yes"'
        },
        {
            'question_id': 'anything_else',
            'question_text': 'Anything else you would like to discuss?',
            'question_type': 'text',
            'question_order': 8,
            'required': False,
            'properties': {},
            'condition_expression': None  # Always show
        },
        {
            'question_id': 'goals',
            'question_text': 'What are your goals for the day?',
            'question_type': 'text',
            'question_order': 9,
            'required': False,
            'properties': {},
            'condition_expression': 'is_before_noon == true and goals_set_today == false'
        }
    ]
    
    # Create template questions
    for q_data in questions_data:
        template_question = TemplateQuestion(
            template_id=default_template.id,
            question_id=q_data['question_id'],
            question_text=q_data['question_text'],
            question_type=q_data['question_type'],
            question_order=q_data['question_order'],
            required=q_data['required'],
            properties=json.dumps(q_data['properties']) if q_data['properties'] else None,
            condition_expression=q_data['condition_expression']
        )
        db.session.add(template_question)
    
    return default_template

def create_sample_templates():
    """Create sample templates for common use cases."""
    
    templates_data = [
        {
            'name': 'Daily Gratitude',
            'description': 'Focus on gratitude and positive moments from your day',
            'questions': [
                {
                    'question_id': 'feeling_scale',
                    'question_text': 'How are you feeling on a scale of 1-10?',
                    'question_type': 'number',
                    'question_order': 1,
                    'required': True,
                    'properties': {'min': 1, 'max': 10}
                },
                {
                    'question_id': 'gratitude_1',
                    'question_text': 'What are you most grateful for today?',
                    'question_type': 'text',
                    'question_order': 2,
                    'required': True,
                    'properties': {}
                },
                {
                    'question_id': 'gratitude_2',
                    'question_text': 'Name two more things you appreciate:',
                    'question_type': 'text',
                    'question_order': 3,
                    'required': False,
                    'properties': {}
                },
                {
                    'question_id': 'positive_moment',
                    'question_text': 'What was the best moment of your day?',
                    'question_type': 'text',
                    'question_order': 4,
                    'required': False,
                    'properties': {}
                },
                {
                    'question_id': 'tomorrow_intention',
                    'question_text': 'What positive intention do you set for tomorrow?',
                    'question_type': 'text',
                    'question_order': 5,
                    'required': False,
                    'properties': {}
                }
            ]
        },
        {
            'name': 'Habit Tracker',
            'description': 'Track your daily habits and progress toward goals',
            'questions': [
                {
                    'question_id': 'exercise_check',
                    'question_text': 'Did you exercise today?',
                    'question_type': 'boolean',
                    'question_order': 1,
                    'required': True,
                    'properties': {}
                },
                {
                    'question_id': 'exercise_details',
                    'question_text': 'What type of exercise did you do?',
                    'question_type': 'text',
                    'question_order': 2,
                    'required': False,
                    'properties': {},
                    'condition_expression': 'exercise_check == "Yes"'
                },
                {
                    'question_id': 'reading_check',
                    'question_text': 'Did you read today?',
                    'question_type': 'boolean',
                    'question_order': 3,
                    'required': True,
                    'properties': {}
                },
                {
                    'question_id': 'meditation_check',
                    'question_text': 'Did you meditate or practice mindfulness?',
                    'question_type': 'boolean',
                    'question_order': 4,
                    'required': True,
                    'properties': {}
                },
                {
                    'question_id': 'water_intake',
                    'question_text': 'How many glasses of water did you drink? (0-10)',
                    'question_type': 'number',
                    'question_order': 5,
                    'required': False,
                    'properties': {'min': 0, 'max': 10}
                },
                {
                    'question_id': 'habit_reflection',
                    'question_text': 'How do you feel about your habit progress today?',
                    'question_type': 'text',
                    'question_order': 6,
                    'required': False,
                    'properties': {}
                }
            ]
        },
        {
            'name': 'Work Reflection',
            'description': 'Reflect on your work day, productivity, and professional growth',
            'questions': [
                {
                    'question_id': 'productivity_scale',
                    'question_text': 'How productive did you feel today? (1-10)',
                    'question_type': 'number',
                    'question_order': 1,
                    'required': True,
                    'properties': {'min': 1, 'max': 10}
                },
                {
                    'question_id': 'accomplishments',
                    'question_text': 'What were your main accomplishments today?',
                    'question_type': 'text',
                    'question_order': 2,
                    'required': False,
                    'properties': {}
                },
                {
                    'question_id': 'challenges',
                    'question_text': 'What challenges did you face and how did you handle them?',
                    'question_type': 'text',
                    'question_order': 3,
                    'required': False,
                    'properties': {}
                },
                {
                    'question_id': 'learning',
                    'question_text': 'What did you learn today?',
                    'question_type': 'text',
                    'question_order': 4,
                    'required': False,
                    'properties': {}
                },
                {
                    'question_id': 'tomorrow_priorities',
                    'question_text': 'What are your top 3 priorities for tomorrow?',
                    'question_type': 'text',
                    'question_order': 5,
                    'required': False,
                    'properties': {}
                }
            ]
        }
    ]
    
    created_templates = []
    for template_data in templates_data:
        template = JournalTemplate(
            name=template_data['name'],
            description=template_data['description'],
            user_id=None,  # System template
            is_system=True
        )
        db.session.add(template)
        db.session.flush()  # Get the ID
        
        # Create questions for this template
        for q_data in template_data['questions']:
            template_question = TemplateQuestion(
                template_id=template.id,
                question_id=q_data['question_id'],
                question_text=q_data['question_text'],
                question_type=q_data['question_type'],
                question_order=q_data['question_order'],
                required=q_data['required'],
                properties=json.dumps(q_data['properties']) if q_data['properties'] else None,
                condition_expression=q_data.get('condition_expression')
            )
            db.session.add(template_question)
        
        created_templates.append(template)
    
    return created_templates

def run_migration():
    """Run the complete migration to add template system."""
    app = create_app()
    
    with app.app_context():
        print("🔧 Starting journal template system migration...")
        
        try:
            # Create the new tables
            print("📝 Creating new database tables...")
            db.create_all()
            print("✅ Tables created successfully!")
            
            # Create default system template
            print("🎯 Creating default system template...")
            default_template = create_default_system_template()
            print(f"✅ Default template created: {default_template.name}")
            
            # Create sample templates
            print("📋 Creating sample templates...")
            sample_templates = create_sample_templates()
            print(f"✅ Created {len(sample_templates)} sample templates:")
            for template in sample_templates:
                print(f"   - {template.name}")
            
            # Commit all changes
            print("💾 Committing changes to database...")
            db.session.commit()
            print("✅ Migration completed successfully!")
            
            # Display summary
            print("\n📊 Migration Summary:")
            print(f"   • Default template: '{default_template.name}' with {default_template.questions.count()} questions")
            for template in sample_templates:
                print(f"   • Sample template: '{template.name}' with {template.questions.count()} questions")
            
            print("\n🎉 Template system is ready!")
            print("   • Existing guided journal entries will continue working")
            print("   • New entries can use templates or default behavior")
            print("   • Users can create custom templates through the UI")
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            db.session.rollback()
            raise

def rollback_migration():
    """Rollback the migration (for testing purposes)."""
    app = create_app()
    
    with app.app_context():
        print("🔄 Rolling back template system migration...")
        
        try:
            # Remove the template_id column from journal_entries
            # Note: SQLite doesn't support DROP COLUMN, so we'd need to recreate the table
            # For now, just clear the template data
            print("🗑️  Clearing template data...")
            
            db.session.execute("DELETE FROM template_questions")
            db.session.execute("DELETE FROM journal_templates")
            db.session.execute("UPDATE journal_entries SET template_id = NULL")
            
            db.session.commit()
            print("✅ Template data cleared successfully!")
            
        except Exception as e:
            print(f"❌ Rollback failed: {str(e)}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        run_migration()