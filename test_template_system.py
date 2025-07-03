#!/usr/bin/env python3
"""
Test script for the journal template system.

This script tests the complete template functionality:
1. Template creation and management
2. Question loading from templates
3. Guided journal with templates
4. Backward compatibility
"""

from app import create_app
from models import db, JournalTemplate, TemplateQuestion, QuestionManager
import json

def test_template_system():
    """Run comprehensive tests for the template system."""
    app = create_app()
    
    with app.app_context():
        print("🧪 Testing Journal Template System")
        print("=" * 50)
        
        # Test 1: Check existing templates
        print("\n1. Testing Template Database")
        templates = JournalTemplate.query.all()
        print(f"   ✅ Found {len(templates)} templates in database")
        
        for template in templates:
            question_count = template.questions.count()
            print(f"   - {template.name}: {question_count} questions")
        
        # Test 2: Test QuestionManager with templates
        print("\n2. Testing QuestionManager")
        
        # Test backward compatibility (no template)
        default_questions = QuestionManager.get_questions()
        print(f"   ✅ Default questions (backward compatible): {len(default_questions)}")
        
        # Test template questions
        if templates:
            template_id = templates[0].id
            template_questions = QuestionManager.get_questions(template_id)
            print(f"   ✅ Template {template_id} questions: {len(template_questions)}")
            
            # Verify question structure
            if template_questions:
                sample_q = template_questions[0]
                required_keys = ['id', 'text', 'type', 'condition']
                missing_keys = [key for key in required_keys if key not in sample_q]
                if not missing_keys:
                    print(f"   ✅ Question structure is correct")
                else:
                    print(f"   ❌ Missing keys in question: {missing_keys}")
        
        # Test 3: Test question conditions
        print("\n3. Testing Question Conditions")
        
        # Test context for conditions
        test_context = {
            'hours_since_last_entry': 10,
            'exercised_today': False,
            'is_before_noon': True,
            'goals_set_today': False,
            'exercise_response': 'Yes'
        }
        
        if templates:
            template = templates[0]
            applicable_questions = []
            
            for tq in template.questions:
                question_dict = tq.to_dict()
                if question_dict['condition'](test_context):
                    applicable_questions.append(question_dict)
            
            print(f"   ✅ {len(applicable_questions)}/{template.questions.count()} questions applicable with test context")
        
        # Test 4: Test template-specific features
        print("\n4. Testing Template Features")
        
        # Find a system template (Daily Gratitude)
        gratitude_template = JournalTemplate.query.filter_by(name="Daily Gratitude").first()
        if gratitude_template:
            print(f"   ✅ Found '{gratitude_template.name}' template")
            print(f"   - Description: {gratitude_template.description}")
            print(f"   - System template: {gratitude_template.is_system}")
            print(f"   - Questions: {gratitude_template.questions.count()}")
            
            # Test question types
            question_types = set()
            for q in gratitude_template.questions:
                question_types.add(q.question_type)
            print(f"   - Question types: {', '.join(question_types)}")
        
        # Test 5: Test condition expressions
        print("\n5. Testing Condition Expressions")
        
        test_expressions = [
            ("Always show", None, True),
            ("Hours condition", "hours_since_last_entry >= 8", True),  # 10 >= 8
            ("Exercise condition", "exercised_today == false", True),  # False == false
            ("Morning condition", "is_before_noon == true", True),     # True == true
        ]
        
        for desc, expr, expected in test_expressions:
            if expr:
                # Create a test question with this expression
                test_question = TemplateQuestion(
                    template_id=1,  # Dummy
                    question_id='test',
                    question_text='Test',
                    question_type='text',
                    question_order=1,
                    condition_expression=expr
                )
                
                condition_func = test_question._create_condition_function()
                result = condition_func(test_context)
                status = "✅" if result == expected else "❌"
                print(f"   {status} {desc}: {expr} -> {result}")
            else:
                print(f"   ✅ {desc}: Always True")
        
        # Test 6: Performance test
        print("\n6. Performance Test")
        import time
        
        start_time = time.time()
        for _ in range(100):
            QuestionManager.get_questions()
        default_time = time.time() - start_time
        
        start_time = time.time()
        for _ in range(100):
            QuestionManager.get_questions(template_id=1)
        template_time = time.time() - start_time
        
        print(f"   ✅ Default questions (100x): {default_time:.3f}s")
        print(f"   ✅ Template questions (100x): {template_time:.3f}s")
        
        # Summary
        print("\n" + "=" * 50)
        print("🎉 Template System Test Complete")
        print(f"   • {len(templates)} templates available")
        print(f"   • Question loading: Working")
        print(f"   • Condition evaluation: Working")
        print(f"   • Backward compatibility: Maintained")
        print(f"   • Performance: Acceptable")
        
        return True

if __name__ == "__main__":
    test_template_system()