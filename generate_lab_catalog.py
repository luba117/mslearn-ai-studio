#!/usr/bin/env python3
"""
Generate a CSV catalog of all lab markdown files in the Instructions folder.

This script analyzes all .md files in the Instructions folder (recursively),
extracts lab information, and generates a CSV file with:
- File name
- Description
- Technologies/Products
- Last merge date
- Last merge author
"""

import os
import re
import csv
import subprocess
from pathlib import Path
from datetime import datetime


def parse_frontmatter(content):
    """Extract YAML frontmatter from markdown content."""
    # Match YAML frontmatter between --- delimiters
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if match:
        frontmatter = match.group(1)
        # Extract title and description
        title_match = re.search(r"title:\s*['\"](.+?)['\"]", frontmatter)
        desc_match = re.search(r"description:\s*['\"](.+?)['\"]", frontmatter)
        
        title = title_match.group(1) if title_match else ""
        description = desc_match.group(1) if desc_match else ""
        
        return title, description
    
    # Fallback: try to extract from first H1 heading
    h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if h1_match:
        title = h1_match.group(1).strip()
        # Try to extract first paragraph as description
        # Skip the H1 line and look for the first substantial paragraph
        lines = content.split('\n')
        desc_lines = []
        in_content = False
        for line in lines:
            if line.startswith('# '):
                in_content = True
                continue
            if in_content and line.strip() and not line.startswith('#') and not line.startswith('!'):
                # Found a content line
                desc_lines.append(line.strip())
                if len(' '.join(desc_lines)) > 100:  # Get enough context
                    break
        description = ' '.join(desc_lines)[:200]  # Limit description length
        return title, description
    
    return "", ""


def extract_technologies(content):
    """Extract technologies and products mentioned in the lab content."""
    technologies = set()
    
    # Common AI/Azure technologies to look for (case-insensitive)
    tech_patterns = [
        r'\bAzure\s+OpenAI\b',
        r'\bGPT-4o?\b',
        r'\bFoundry\b',
        r'\bprompt\s+flow\b',
        r'\bRAG\b',
        r'\bRetrieval\s+Augmented\s+Generation\b',
        r'\bAzure\s+AI\s+(?:Services|Studio|Foundry)\b',
        r'\bAI\s+hub\b',
        r'\bPython\s+SDK\b',
        r'\bTypeScript\b',
        r'\b\.NET\b',
        r'\bfine-tun(?:e|ing)\b',
        r'\bcontent\s+filter(?:s|ing)?\b',
        r'\bevaluation\b',
        r'\bembedding\b',
        r'\bmodel\s+catalog\b',
        r'\bchat\s+(?:app|playground)\b',
        r'\bNER\b',
        r'\bNamed\s+Entity\s+Recognition\b',
    ]
    
    for pattern in tech_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            # Normalize the match
            technologies.add(matches[0].strip())
    
    # Return as comma-separated string
    return ", ".join(sorted(technologies, key=str.lower)) if technologies else "N/A"


def get_git_info(file_path, repo_root):
    """Get last merge commit date and author for a file."""
    try:
        # Get the relative path from repo root
        rel_path = os.path.relpath(file_path, repo_root)
        
        # Get last commit info for this file (using git log with merges)
        cmd = [
            'git', 'log', '-1', '--merges', '--format=%ai|%an', '--', rel_path
        ]
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split('|')
            if len(parts) == 2:
                date_str, author = parts
                # Parse and format the date
                date_obj = datetime.strptime(date_str.split()[0], '%Y-%m-%d')
                return date_obj.strftime('%Y-%m-%d'), author
        
        # If no merge commit found, try regular commits
        cmd = [
            'git', 'log', '-1', '--format=%ai|%an', '--', rel_path
        ]
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split('|')
            if len(parts) == 2:
                date_str, author = parts
                # Parse and format the date
                date_obj = datetime.strptime(date_str.split()[0], '%Y-%m-%d')
                return date_obj.strftime('%Y-%m-%d'), author
        
    except Exception as e:
        print(f"Warning: Could not get git info for {file_path}: {e}")
    
    return "N/A", "N/A"


def process_lab_files(repo_root, instructions_dir):
    """Process all markdown lab files and extract information."""
    labs = []
    
    # Find all .md files in Instructions directory
    instructions_path = Path(instructions_dir)
    md_files = sorted(instructions_path.rglob('*.md'))
    
    print(f"Found {len(md_files)} markdown files in {instructions_dir}")
    
    for md_file in md_files:
        print(f"Processing: {md_file}")
        
        try:
            # Read the file content
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract information
            title, description = parse_frontmatter(content)
            technologies = extract_technologies(content)
            last_merge_date, last_merge_author = get_git_info(str(md_file), repo_root)
            
            # Get relative filename from Instructions directory
            rel_filename = md_file.relative_to(instructions_path)
            
            # Combine title and description for the description field
            full_description = f"{title}. {description}" if title and description else (description or title or "N/A")
            
            labs.append({
                'filename': str(rel_filename),
                'description': full_description,
                'technologies': technologies,
                'last_merge_date': last_merge_date,
                'last_merge_author': last_merge_author
            })
            
        except Exception as e:
            print(f"Error processing {md_file}: {e}")
    
    return labs


def generate_csv(labs, output_file):
    """Generate CSV file with lab information."""
    fieldnames = ['filename', 'description', 'technologies', 'last_merge_date', 'last_merge_author']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(labs)
    
    print(f"\nCSV file generated: {output_file}")
    print(f"Total labs documented: {len(labs)}")


def main():
    """Main function to generate the lab catalog."""
    # Get repository root and instructions directory
    repo_root = os.path.dirname(os.path.abspath(__file__))
    instructions_dir = os.path.join(repo_root, 'Instructions')
    output_file = os.path.join(repo_root, 'lab_catalog.csv')
    
    print("="*60)
    print("Lab Catalog Generator")
    print("="*60)
    
    # Process all lab files
    labs = process_lab_files(repo_root, instructions_dir)
    
    # Generate CSV
    generate_csv(labs, output_file)
    
    print("\n" + "="*60)
    print("Done!")
    print("="*60)


if __name__ == '__main__':
    main()
