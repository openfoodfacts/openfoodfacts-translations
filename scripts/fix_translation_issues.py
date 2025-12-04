#!/usr/bin/env python3
"""
Script to fix common translation issues in Crowdin-translated HTML files.

Features:
- Fix text repetitions (duplicated sentences/phrases)
- Fix UTM campaign parameters to use correct language codes
- Remove duplicated HTML tags like </figcaption> </figcaption>

Usage:
    python fix_translation_issues.py [--base-dir DIR] [--no-utm] [--no-repetitions] [-v]
"""

import argparse
import os
import re
import sys
from pathlib import Path


def fix_duplicated_tags(content):
    """Fix duplicated HTML closing tags like </figcaption> </figcaption>."""
    fixed = content
    
    # Fix duplicated closing tags with space between them
    # Common patterns: </tag> </tag> or </tag></tag>
    tags_to_check = ['figcaption', 'p', 'span', 'strong', 'em', 'a', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    
    for tag in tags_to_check:
        # Pattern: </tag> </tag> or </tag>  </tag> (with varying whitespace)
        pattern = rf'(</{tag}>)\s+\1'
        fixed = re.sub(pattern, rf'\1', fixed, flags=re.IGNORECASE)
        
        # Pattern: </tag></tag> (no whitespace)
        pattern = rf'(</{tag}>)\1'
        fixed = re.sub(pattern, rf'\1', fixed, flags=re.IGNORECASE)
    
    return fixed


def fix_text_repetitions(content):
    """
    Fix text repetitions where the same sentence/phrase appears multiple times consecutively.
    
    This handles cases like:
    - "This is a sentence. This is a sentence." -> "This is a sentence."
    - "Hello world! Hello world! Hello world!" -> "Hello world!"
    """
    fixed = content
    
    # We need to be careful not to break HTML structure
    # Strategy: Find repeated substantial text chunks and reduce to single occurrence
    
    min_length = 20
    
    def replace_repetitions(match):
        """Keep only the first occurrence of repeated text."""
        return match.group(1)
    
    # We need to iteratively apply this since one replacement might expose another
    max_iterations = 10
    for _ in range(max_iterations):
        original = fixed
        
        # Match text that's at least min_length chars, followed by whitespace and itself
        # Use a simpler pattern: capture text without newlines or angle brackets,
        # then match whitespace followed by the same text
        pattern = r'([^\n<>]{' + str(min_length) + r',}?)(\s+\1)+'
        fixed = re.sub(pattern, replace_repetitions, fixed)
        
        # If no changes were made, we're done
        if fixed == original:
            break
    
    return fixed


def fix_utm_parameters(content, lang_code):
    """
    Fix UTM campaign parameters to use the correct language code.
    
    Common issue: UTM parameters might have wrong language codes or be missing.
    """
    # Pattern to match UTM campaign parameters with language codes
    # Example: utm_campaign=blog-de-DE -> utm_campaign=blog-{correct_lang}
    
    if not lang_code:
        return content
    
    fixed = content
    
    # Fix utm_campaign=blog-XX-XX patterns
    pattern = r'utm_campaign=blog-[a-z]{2}-[A-Z]{2}'
    replacement = f'utm_campaign=blog-{lang_code}'
    fixed = re.sub(pattern, replacement, fixed)
    
    return fixed


def process_file(filepath, fix_utm=True, fix_repetitions=True, verbose=False):
    """
    Process a single HTML file and fix translation issues.
    
    Returns: (bool, str) - (was_modified, list of changes made)
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except Exception as e:
        if verbose:
            print(f"  ⚠️  Could not read {filepath}: {e}")
        return False, []
    
    content = original_content
    changes = []
    
    # Extract language code from path (e.g., blog/zh-TW/... -> zh-TW)
    lang_code = None
    parts = Path(filepath).parts
    for i, part in enumerate(parts):
        if re.match(r'^[a-z]{2}-[A-Z]{2}$', part):
            lang_code = part
            break
    
    # Apply fixes
    if fix_repetitions:
        new_content = fix_duplicated_tags(content)
        if new_content != content:
            changes.append("Fixed duplicated HTML tags")
            content = new_content
        
        new_content = fix_text_repetitions(content)
        if new_content != content:
            changes.append("Fixed text repetitions")
            content = new_content
    
    if fix_utm and lang_code:
        new_content = fix_utm_parameters(content, lang_code)
        if new_content != content:
            changes.append(f"Fixed UTM parameters to use {lang_code}")
            content = new_content
    
    # Write changes if any
    if content != original_content:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes
        except Exception as e:
            if verbose:
                print(f"  ⚠️  Could not write {filepath}: {e}")
            return False, []
    
    return False, []


def find_html_files(base_dir):
    """Find all HTML files in the base directory."""
    html_files = []
    
    for root, dirs, files in os.walk(base_dir):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))
    
    return sorted(html_files)


def main():
    parser = argparse.ArgumentParser(description='Fix common translation issues in HTML files.')
    parser.add_argument('--base-dir', '-d', default='blog',
                        help='Base directory to search for HTML files (default: blog)')
    parser.add_argument('--no-utm', action='store_true',
                        help='Skip fixing UTM parameters')
    parser.add_argument('--no-repetitions', action='store_true',
                        help='Skip fixing text repetitions')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output')
    parser.add_argument('files', nargs='*',
                        help='Specific files to process (optional)')
    
    args = parser.parse_args()
    
    fix_utm = not args.no_utm
    fix_repetitions = not args.no_repetitions
    verbose = args.verbose
    
    print("=" * 70)
    print("🔧 Translation Issue Fixer")
    print("=" * 70)
    print(f"  Fix UTM parameters: {'Yes' if fix_utm else 'No'}")
    print(f"  Fix text repetitions: {'Yes' if fix_repetitions else 'No'}")
    print()
    
    # Get list of files to process
    if args.files:
        files = args.files
    else:
        base_dir = args.base_dir
        if not os.path.isdir(base_dir):
            # Try common alternatives
            for alt in ['blog', 'lang', '.']:
                if os.path.isdir(alt):
                    base_dir = alt
                    break
        
        if not os.path.isdir(base_dir):
            print(f"❌ Directory not found: {base_dir}")
            sys.exit(1)
        
        print(f"📂 Searching for HTML files in: {base_dir}")
        files = find_html_files(base_dir)
    
    print(f"📋 Found {len(files)} HTML files to process")
    print()
    
    # Process files
    total_fixed = 0
    files_with_changes = []
    
    for filepath in files:
        was_modified, changes = process_file(filepath, fix_utm, fix_repetitions, verbose)
        
        if was_modified:
            total_fixed += 1
            files_with_changes.append((filepath, changes))
            if verbose:
                print(f"  ✅ Fixed: {filepath}")
                for change in changes:
                    print(f"      - {change}")
    
    # Summary
    print()
    print("=" * 70)
    print("📊 Summary")
    print("=" * 70)
    print(f"  Files processed: {len(files)}")
    print(f"  Files fixed: {total_fixed}")
    
    if files_with_changes:
        print()
        print("📝 Files with changes:")
        for filepath, changes in files_with_changes:
            print(f"  - {filepath}")
            if verbose:
                for change in changes:
                    print(f"      {change}")
    
    print()
    if total_fixed > 0:
        print("✅ Done! Translation issues have been fixed.")
    else:
        print("✨ No issues found - all files are clean!")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
