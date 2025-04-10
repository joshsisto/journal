#!/usr/bin/env python3
"""
Test script to validate Gemini API integration.
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

def main():
    """Test Gemini API connectivity."""
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables.")
        print("Make sure you have added your API key to the .env file.")
        return
    
    print(f"API key found: {api_key[:4]}...{api_key[-4:]}")
    
    try:
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # List available models
        print("\nListing available models:")
        for model in genai.list_models():
            if "gemini" in model.name:
                print(f"- {model.name}")
        
        # Try to use a model
        print("\nTesting model generation:")
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            print("Using model: gemini-1.5-flash")
        except Exception as e:
            print(f"Error with gemini-1.5-flash: {e}")
            try:
                model = genai.GenerativeModel('gemini-1.0-pro')
                print("Using model: gemini-1.0-pro")
            except Exception as e:
                print(f"Error with gemini-1.0-pro: {e}")
                model = genai.GenerativeModel('gemini-pro')
                print("Using model: gemini-pro")
        
        # Generate content
        response = model.generate_content("Say hello and introduce yourself as a journal assistant")
        
        print("\nAPI Response:")
        print(response.text)
        
        print("\nGemini API is working correctly!")
    except Exception as e:
        print(f"\nError testing Gemini API: {e}")
        print("Make sure your API key is valid and the Google Generative AI package is installed.")

if __name__ == "__main__":
    main()