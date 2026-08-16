import re

prompt_path = r"C:\Users\fabio\OneDrive\Área de Trabalho\Fran\eber\nlt\1-promptAnaliseAtendimentos.txt"

try:
    with open(prompt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Prompt loaded successfully.")
    print("Length of prompt in characters:", len(content))
    print("Approximate word count:", len(content.split()))
    
    # Find any JSON keys or structure
    json_keys = set(re.findall(r'"([a-zA-Z0-9_]{3,30})"\s*:', content))
    print("\nJSON keys found in prompt:")
    print(sorted(list(json_keys)))
    
    # Search for headings
    headings = re.findall(r'^#+ .+', content, re.MULTILINE)
    print("\nHeadings found:")
    for h in headings[:40]:
        print("  ", h)
    if len(headings) > 40:
        print(f"   ... and {len(headings) - 40} more headings.")
        
except Exception as e:
    print("Error loading prompt:", str(e))
