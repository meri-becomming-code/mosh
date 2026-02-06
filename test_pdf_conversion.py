import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import converter_utils
from bs4 import BeautifulSoup

def analyze_html_structure(html_path):
    """Analyze the structure of generated HTML"""
    if not os.path.exists(html_path):
        return None
    
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    
    stats = {
        'p_tags': len(soup.find_all('p')),
        'ul_tags': len(soup.find_all('ul')),
        'ol_tags': len(soup.find_all('ol')),
        'li_tags': len(soup.find_all('li')),
        'h2_tags': len(soup.find_all('h2')),
        'h3_tags': len(soup.find_all('h3')),
        'tables': len(soup.find_all('table')),
        'images': len(soup.find_all('img')),
    }
    
    # Calculate average paragraph length
    paragraphs = soup.find_all('p', class_=lambda x: x != 'note')
    if paragraphs:
        avg_p_length = sum(len(p.get_text().split()) for p in paragraphs) / len(paragraphs)
        stats['avg_paragraph_words'] = round(avg_p_length, 1)
    else:
        stats['avg_paragraph_words'] = 0
    
    return stats

def print_stats(label, stats):
    """Pretty print statistics"""
    if not stats:
        print(f"{label}: File not found")
        return
        
    print(f"\n{label}:")
    print(f"  Paragraphs: {stats['p_tags']}")
    print(f"  Lists (ul): {stats['ul_tags']}")
    print(f"  Lists (ol): {stats['ol_tags']}")
    print(f"  List items: {stats['li_tags']}")
    print(f"  Headers (h2): {stats['h2_tags']}")
    print(f"  Headers (h3): {stats['h3_tags']}")
    print(f"  Tables: {stats['tables']}")
    print(f"  Images: {stats['images']}")
    print(f"  Avg words/paragraph: {stats['avg_paragraph_words']}")

def test_pdf_conversion():
    """Test PDF conversion with improved algorithm"""
    print("=" * 60)
    print("Testing Improved PDF to HTML Conversion")
    print("=" * 60)
    
    # Test file path - use the one directly in Downloads
    test_pdf = r"C:\Users\mkasprak\Downloads\Python Escape.pdf"
    
    if not os.path.exists(test_pdf):
        print(f"ERROR: Test PDF not found: {test_pdf}")
        return False
    
    print(f"\nTesting with: {os.path.basename(test_pdf)}")
    
    # Run conversion
    print("\nConverting PDF...")
    result_path, error = converter_utils.convert_pdf_to_html(test_pdf)
    
    if error:
        print(f"ERROR: Conversion failed: {error}")
        return False
    
    print(f"✓ Conversion successful: {os.path.basename(result_path)}")
    
    # Analyze structure
    stats = analyze_html_structure(result_path)
    print_stats("Generated HTML Structure", stats)
    
    # Check for expected improvements
    print("\n" + "=" * 60)
    print("VERIFICATION CHECKS")
    print("=" * 60)
    
    checks_passed = 0
    checks_total = 4
    
    # Check 1: Should have lists detected
    if stats['ul_tags'] > 0 or stats['ol_tags'] > 0:
        print("✓ PASS: Lists detected (ul or ol tags present)")
        checks_passed += 1
    else:
        print("✗ FAIL: No lists detected")
    
    # Check 2: Average paragraph should be longer than 2 words
    if stats['avg_paragraph_words'] > 2:
        print(f"✓ PASS: Average paragraph length is {stats['avg_paragraph_words']} words (>2)")
        checks_passed += 1
    else:
        print(f"✗ FAIL: Average paragraph too short ({stats['avg_paragraph_words']} words)")
    
    # Check 3: Should have reasonable number of paragraphs (not excessive)
    # Old version would create ~50+ paragraphs for this PDF
    if stats['p_tags'] < 30:
        print(f"✓ PASS: Reasonable paragraph count ({stats['p_tags']} < 30)")
        checks_passed += 1
    else:
        print(f"✗ WARNING: High paragraph count ({stats['p_tags']})")
    
    # Check 4: Should have list items
    if stats['li_tags'] > 0:
        print(f"✓ PASS: List items detected ({stats['li_tags']} items)")
        checks_passed += 1
    else:
        print("✗ FAIL: No list items detected")
    
    print(f"\nOverall: {checks_passed}/{checks_total} checks passed")
    
    # Show sample content
    print("\n" + "=" * 60)
    print("SAMPLE CONTENT (First 500 characters)")
    print("=" * 60)
    
    with open(result_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    body = soup.find('body')
    if body:
        # Get text content
        text = body.get_text()[:500]
        print(text)
    
    print("\n" + "=" * 60)
    print(f"Full output file: {result_path}")
    print("=" * 60)
    
    return checks_passed >= 3  # Pass if at least 3/4 checks pass

if __name__ == "__main__":
    success = test_pdf_conversion()
    sys.exit(0 if success else 1)
