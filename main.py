from docx import Document
import json
from openai import OpenAI
import os

def collect_instructions(instructions_path, volume_metadata, mode):
    """Collects pertinent natural language instructions for model.

    Args:
        instructions_path (str): path to json file containing model instructions

        volume_metadata (dict): dict containing basic volume metadata

        mode (str): pipeline component currently being invoked, either
        `transcription`, `normalization`, or `extraction`

    Returns:
        List containing instructions to be passed to model as system messages. 
    """
    with open(instructions_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if mode == "transcription":
        if volume_metadata["fields"]["country"] == "Brazil":
            language = "Portuguese"
        else:
            language = "Spanish"        

        keywords = [mode, language, volume_metadata["type"]]
    else:
        keywords = [mode]
    
    instructions = []

    #recursively checks instructions for those that match mode, language, and record type
    for instruction in data["instructions"]:
        match = True
        for keyword in instruction["cases"]:
            if keyword not in keywords:
                match = False
        if match:
            instructions.append(instruction)

    #sorts language by intended sequence as defined in source file (lower first)
    return sorted(instructions, key=lambda x: x["sequence"])

def read_docx_bullets(file_path):
    # Load the document
    doc = Document(file_path)

    # List to hold all bullet points with indentation
    content = {'path': file_path, 'content': []}

    # Iterate through each paragraph in the document
    for para in doc.paragraphs:
        # Check if the paragraph is part of a list (bulleted or numbered)
        if para.text.strip() and para.style.name.startswith('List'):
            # Retrieve the level of indentation from the list properties if available
            if para.paragraph_format.left_indent:
                indentation = int(para.paragraph_format.left_indent.pt / 36)  # convert points to indentation level
            elif para._p.pPr.numPr is not None:  # Access underlying XML to find list level if present
                level = int(para._p.pPr.numPr.ilvl.val)  # Extract level information directly from XML
                indentation = level + 1  # Adding 1 to make it human-readable (starts from 1 instead of 0)
            else:
                indentation = 0  # No indentation if nothing is specified

            # Store the bullet point and its indentation level
            content['content'].append({'text': para.text, 'indent': indentation})

    return content

def load_data(data_path='data', dump_output=False, output_path='docs.json'):
    documents = []
    for folder, subfolders, files in os.walk(data_path):
        for file in files:
            documents.append(read_docx_bullets(os.path.join(folder, file)))
    if dump_output:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(documents, f)

    return documents

def query_llm(data_path='data', instructions_path='instructions.json'):
    client = OpenAI()
    research_data = load_data(data_path=data_path)
    instructions = collect_instructions(instructions_path, None, "research")

    conversation = []

    #add natural language instructions to conversation history as system messages
    for instruction in instructions:
        conversation.append(
            {
                    "role": "system",
                    "content": instruction["text"]
            }
        )

    conversation.append(
        {
            "role": "user",
            "content": f"Here is my research data: {research_data}"
        }
    )

    more_questions = True
    question = input("What would you like to ask GPT4? If you're done, type 'quit'. ")

    while more_questions:

        if question.lower() == 'quit':
            more_questions = False
            break        
        conversation.append(
            {
                "role": "user",
                "content": question
            }
        )

        response = client.chat.completions.create(
        model="gpt-4o",    
        messages = conversation
        )

        print(response.choices[0].message.content)
	
        question = input("What would you like to ask GPT4? If you're done, type 'quit'. ")

query_llm()
    