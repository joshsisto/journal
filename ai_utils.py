"""
AI utilities for journal application.
"""

import os
import json
import sys
import traceback
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from flask import current_app
import google.generativeai as genai

# Load API key from environment
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Print API key status (without revealing the key)
print(f"Gemini API key available: {'Yes' if GEMINI_API_KEY else 'No'}")
if GEMINI_API_KEY:
    print(f"API key length: {len(GEMINI_API_KEY)} characters")
else:
    print("Warning: GEMINI_API_KEY not found in environment variables.")

# Print Python and library versions for debugging
print(f"Python version: {sys.version}")
print(f"Google Generative AI version: {genai.__version__}")

# Initialize the Gemini client
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print("Gemini API client configured successfully")
        
        # Test model access
        try:
            models = genai.list_models()
            available_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
            print(f"Available models: {', '.join(available_models)}")
        except Exception as model_error:
            print(f"Error listing models: {model_error}")
    except Exception as e:
        print(f"Error initializing Gemini client: {e}")
        traceback.print_exc()
else:
    print("Warning: GEMINI_API_KEY not found in environment variables.")

def format_journal_entry(entry_data: Dict[str, Any]) -> str:
    """Format a journal entry for AI input."""
    formatted_text = f"--- JOURNAL ENTRY: {entry_data.get('date', 'Unknown Date')} ---\n\n"
    
    # Add feeling information if available
    if entry_data.get('feeling_value'):
        formatted_text += f"Feeling: {entry_data.get('feeling_value')}/10\n"
    
    # Add emotions if available
    if entry_data.get('emotions') and entry_data['emotions']:
        emotions_str = ", ".join(entry_data['emotions'])
        formatted_text += f"Emotions: {emotions_str}\n"
    
    # Add content
    if entry_data.get('content'):
        formatted_text += f"\nContent:\n{entry_data['content']}\n"
    
    # Add guided responses if available
    if entry_data.get('guided_responses'):
        formatted_text += "\nGuided Responses:\n"
        for question, answer in entry_data['guided_responses'].items():
            formatted_text += f"Q: {question}\nA: {answer}\n\n"
    
    return formatted_text

def generate_ai_prompt(entries_data: List[Dict[str, Any]], question: str) -> str:
    """Generate a prompt for the AI based on journal entries and a question."""
    prompt = "You are a helpful, empathetic AI assistant engaging in a conversation about my journal entries. "
    prompt += "Your goal is to provide thoughtful insights about my reflections, emotions, and experiences. "
    prompt += "Please be supportive, kind, and focused on understanding the themes and patterns in my journaling. "
    prompt += "Avoid making judgemental statements and respect the privacy and sensitivity of this personal information. "
    prompt += "Here are my journal entries:\n\n"
    
    # Add each journal entry to the prompt
    for entry in entries_data:
        prompt += format_journal_entry(entry) + "\n\n"
    
    # Add user's question
    prompt += f"Now, based on these journal entries, please respond to this question: {question}"
    
    return prompt

def get_ai_response(entries_data: List[Dict[str, Any]], question: str) -> str:
    """Get AI response based on journal entries and a question."""
    if not GEMINI_API_KEY:
        print("No API key found")
        return "I'm running in demo mode since no API key is configured. In a real deployment, I would analyze your journal entries and provide personalized insights about your question: " + question
    
    try:
        print("="*40)
        print(f"Starting AI response generation")
        print(f"Question: '{question}'")
        print(f"Number of entries: {len(entries_data)}")
        
        # Log entry IDs and dates for debugging
        entry_summary = []
        for entry in entries_data:
            entry_id = entry.get('id', 'unknown')
            entry_date = entry.get('date', 'unknown date')
            entry_type = entry.get('entry_type', 'unknown type')
            entry_summary.append(f"ID:{entry_id}, Date:{entry_date}, Type:{entry_type}")
        
        print(f"Entries: {', '.join(entry_summary)}")
        
        # Generate the prompt
        print(f"Generating AI prompt...")
        prompt = generate_ai_prompt(entries_data, question)
        print(f"Prompt generated, length: {len(prompt)} characters")
        
        # For debugging: output first and last 100 chars of prompt
        print(f"Prompt start: {prompt[:100]}...")
        print(f"Prompt end: ...{prompt[-100:]}")
        
        # Try available models in order of preference (updated for 2025)
        available_models = [
            'models/gemini-2.0-flash',          # Latest Gemini 2.0 Flash model
            'models/gemini-2.0-flash-001',      # Specific version
            'models/gemini-1.5-flash-latest',   # Latest 1.5 Flash
            'models/gemini-1.5-flash',          # Stable 1.5 Flash
            'models/gemini-1.5-flash-002',      # Specific 1.5 version
            'models/gemini-1.5-pro-latest',     # Latest 1.5 Pro
            'models/gemini-1.5-pro',            # Stable 1.5 Pro
            'models/gemini-1.5-pro-002'         # Specific 1.5 Pro version
        ]
        
        model = None
        model_name = None
        
        # Try models until one works
        for m_name in available_models:
            try:
                print(f"Trying to use model: {m_name}")
                model = genai.GenerativeModel(m_name)
                model_name = m_name
                print(f"Model initialized: {m_name}")
                break
            except Exception as model_error:
                print(f"Error with model {m_name}: {model_error}")
                if m_name == available_models[-1]:
                    # Last model failed, re-raise the exception
                    raise Exception(f"All models failed. Last error: {model_error}")
                # Otherwise try the next model
                continue
        
        if not model:
            raise Exception("Failed to initialize any model")
        
        # Set safety settings
        safety_settings = {
            "HARASSMENT": "BLOCK_NONE",
            "HATE": "BLOCK_NONE",
            "SEXUAL": "BLOCK_NONE",
            "DANGEROUS": "BLOCK_NONE"
        }
        
        # Generate content with a timeout
        print(f"Generating content with model {model_name}...")
        
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 1000,
        }
        
        print(f"Generation config: {generation_config}")
        
        try:
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            print("Content generated successfully")
            
            # Debug the response object
            print(f"Response type: {type(response)}")
            print(f"Response attributes: {dir(response)}")
            
            # Extract text from response
            if hasattr(response, 'text'):
                print(f"Response has text attribute, length: {len(response.text)}")
                result = response.text
                print(f"Response preview: {result[:100]}...")
            else:
                # Handle alternative response formats
                print(f"Response has no text attribute, trying to extract text...")
                if hasattr(response, 'parts'):
                    parts_text = " ".join([p.text for p in response.parts if hasattr(p, 'text')])
                    if parts_text:
                        result = parts_text
                        print(f"Extracted from parts: {result[:100]}...")
                    else:
                        result = str(response)
                        print(f"Falling back to string representation: {result[:100]}...")
                else:
                    result = str(response)
                    print(f"Fallback response: {result[:100]}...")
            
            print("="*40)
            return result
            
        except Exception as generation_error:
            print(f"Error during content generation: {generation_error}")
            print(f"Error type: {type(generation_error)}")
            traceback.print_exc()
            
            # Try one more time with a simpler prompt as fallback
            try:
                print("Attempting fallback with simpler prompt...")
                simple_prompt = f"Please analyze these journal entries and answer the question: {question}"
                fallback_response = model.generate_content(simple_prompt)
                
                if hasattr(fallback_response, 'text'):
                    fallback_result = fallback_response.text
                else:
                    fallback_result = str(fallback_response)
                
                print(f"Fallback response: {fallback_result[:100]}...")
                return fallback_result
            except Exception as fallback_error:
                print(f"Fallback also failed: {fallback_error}")
                return f"Sorry, I couldn't generate a response. Please try again with a different question."
            
    except Exception as e:
        print("="*40)
        print(f"Error getting AI response: {e}")
        print(f"Error type: {type(e)}")
        traceback.print_exc()
        print("="*40)
        return f"Sorry, I encountered an error while processing your request: {str(e)}"