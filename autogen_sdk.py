from openai import OpenAI
# import anthropic
import difflib
from dotenv import load_dotenv
import os
import re

load_dotenv()

# Connect to OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# claude = anthropic.Client(api_key=os.getenv("ANTHROPIC_API_KEY"))

def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()

# Retrieve old and new openapi.yaml files to use as context - TODO LATER
def retrieve_openapi_files():
    old_spec = read_file("old_openapi.yaml")
    new_spec = read_file("new_openapi.yaml")
    return old_spec, new_spec

def extract_new_sdk(response_text):
    pattern = r"\$\$\$(.*?)\$\$\$"
    match = re.search(pattern, response_text, re.DOTALL)  # re.DOTALL allows matching across multiple lines
    if match:
        return match.group(1).strip()  # Return the content between the $$$ markers
    return None

def save_to_file(sdk_content, file_name):
    """
    Saves the generated SDK content to a specified file
    """
    with open(file_name, 'w') as file:
        file.write(sdk_content)

# Use old and new yaml files with current SDK to generate new SDK from new yaml file using 4o
def generate_new_sdk(old_spec, new_spec):

    old_sdk = read_file("exa_py/api.py")
    prompt = f"The old spec is: {old_spec} \n\n The new spec is: {new_spec} \n\n The old sdk is: {old_sdk} \n\n Please generate a new sdk following the format of the old sdk but using the changes from the new spec. The new SDK MUST follow the same format as the old sdk. In your response, wrap the new sdk in $$$. The new SDK MUST start and end with $$$. Do NOT use backticks in your response. Do not include python ~~~ in your response or wrap the file in anything else inside $$$"

    # Make the call to the model
    response = client.chat.completions.create(
        model="gpt-4o",
        messages = [
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    # Extract the response text
    generated_text = response.choices[0].message.content

    # save_to_file(generated_text, file_name="full_response.txt")

    # Extract the new SDK from the response
    new_sdk = extract_new_sdk(generated_text)

    save_to_file(new_sdk, file_name="exa_py/api.py")

    # Explore the difference
    diff = difflib.unified_diff(old_sdk.splitlines(), new_sdk.splitlines(), fromfile="old_sdk.txt", tofile="new_sdk.txt")
    with open("diffs.txt", 'w') as diff_file:
        diff_file.write("\n".join(diff))


def main():
    old_spec, new_spec = retrieve_openapi_files()
    generate_new_sdk(old_spec, new_spec)

main()