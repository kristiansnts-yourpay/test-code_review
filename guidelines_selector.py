import json
import os
import re
import sys

def select_guidelines(diff_content, guidelines_path='code_review_guidelines/guidelines.json'):
    """
    Analyze diff content to determine file types and select appropriate guidelines.
    
    Args:
        diff_content (str): The git diff content
        guidelines_path (str): Path to the guidelines JSON file
        
    Returns:
        dict: Selected guideline object with content
    """
    # Load the guidelines
    with open(guidelines_path, 'r') as f:
        guidelines = json.load(f)

    # Determine file types in the diff
    file_extensions = set()
    for line in diff_content.split('\n'):
        if line.startswith('+++') or line.startswith('---'):
            match = re.search(r'\.([\w]+)$', line)
            if match:
                file_extensions.add(match.group(1))

    # Print detected file types for logging
    print(f"File types detected: {', '.join(file_extensions)}")
    
    # Select appropriate guideline based on file types
    selected_guideline = None
    for guideline in guidelines:
        if guideline['language'] in file_extensions:
            selected_guideline = guideline
            print(f"Using guidelines for: {guideline['language']}")
            break

    # Default to first guideline if no match found
    if not selected_guideline and guidelines:
        selected_guideline = guidelines[0]
        print(f"No matching guidelines found. Defaulting to: {guidelines[0]['language']}")
    
    # Fallback if no guidelines are available
    if not selected_guideline:
        print("No guidelines available. Using default system prompt.")
        selected_guideline = {
            "content": "You are an expert code reviewer and software engineer specializing in best practices, clean code, performance optimization, security, and maintainability. Analyze the following code changes and provide constructive feedback."
        }
    
    return selected_guideline

def create_review_payload(diff_content, model="deepseek/deepseek-r1-distill-llama-70b:free"):
    """
    Create the payload for the AI review API request.
    
    Args:
        diff_content (str): The git diff content
        model (str): The AI model to use
        
    Returns:
        dict: The payload for the API request
    """
    guideline = select_guidelines(diff_content)
    
    # Add detailed code example format instruction above the review
    review_instruction = """
When providing code examples, please use clear "Wrong" and "Correct" sections with explanatory comments:

# Wrong:

# Arguments on first line forbidden when not using vertical alignment
foo = long_function_name(var_one, var_two,
    var_three, var_four)

# Further indentation required as indentation is not distinguishable
def long_function_name(
    var_one, var_two, var_three,
    var_four):
    print(var_one)

# Correct:

# Aligned with opening delimiter
foo = long_function_name(var_one, var_two,
                         var_three, var_four)

# Add 4 spaces (an extra level of indentation) to distinguish arguments from the rest
def long_function_name(
        var_one, var_two, var_three,
        var_four):
    print(var_one)

# Hanging indents should add a level
foo = long_function_name(
    var_one, var_two,
    var_three, var_four)
"""
    
    guideline_content = guideline["content"] + "\n\n" + review_instruction
    
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": guideline_content
            },
            {
                "role": "user",
                "content": diff_content
            }
        ]
    }

if __name__ == "__main__":
    # If run as a script, read diff from file and output payload to file
    if len(sys.argv) > 1:
        diff_file = sys.argv[1]
        with open(diff_file, 'r') as f:
            diff_content = f.read()
        
        payload = create_review_payload(diff_content)
        
        # Write payload to file
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'payload.json'
        with open(output_file, 'w') as f:
            json.dump(payload, f)
        
        print(f"Payload written to {output_file}")
    else:
        print("Usage: python guidelines_selector.py diff_file [output_file]")
