# ENHANCED JAVASCRIPT FIX
# 
# Issue 1: HS dropdown still not working
# Issue 2: Need to capture multiple 247 IDs (Base, JUCO, HS)

# SOLUTION 1: Force dropdown visibility with JavaScript
# Instead of just clicking, we'll:
# 1. Remove the 'hidden' class from the dropdown
# 2. Make it visible with inline styles
# 3. THEN parse the links

async def find_most_recent_hs_profile_ENHANCED(page) -> tuple:
    """
    Enhanced version that FORCES the dropdown to be visible using JavaScript
    """
    try:
        print(f"      🔍 DEBUG: Starting HS profile search (ENHANCED)...")
        
        await page.wait_for_timeout(2000)
        
        # STEP 1: Try to click button first
        print(f"      → DEBUG: Attempting JavaScript click...")
        clicked = await page.evaluate('''() => {
            const button = document.querySelector('button[data-js="institution-selector"]');
            if (button) {
                button.click();
                return true;
            }
            return false;
        }''')
        
        if clicked:
            print(f"      ✓ DEBUG: Button clicked!")
            await page.wait_for_timeout(1500)
        else:
            print(f"      ⚠️  DEBUG: Button not found, trying to force visibility...")
        
        # STEP 2: FORCE the dropdown to be visible
        print(f"      → DEBUG: Forcing dropdown visibility with JavaScript...")
        forced = await page.evaluate('''() => {
            // Find the institution list
            const list = document.querySelector('ul.institution-list');
            if (list) {
                // Remove 'hidden' class
                list.classList.remove('hidden');
                // Force display
                list.style.display = 'block';
                list.style.visibility = 'visible';
                list.style.opacity = '1';
                return true;
            }
            return false;
        }''')
        
        if forced:
            print(f"      ✓ DEBUG: Dropdown forced visible!")
            await page.wait_for_timeout(500)
        else:
            print(f"      ⚠️  DEBUG: Could not find institution-list")
        
        # STEP 3: Now parse the HTML
        html = await page.content()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try multiple selectors
        selectors = [
            'ul.institution-list a',
            '.institution-list a',
            'div.institution-block ul a',
            'a[href*="/high-school-"]'
        ]
        
        institution_links = []
        for selector in selectors:
            institution_links = soup.select(selector)
            if institution_links:
                print(f"      ✓ DEBUG: Found {len(institution_links)} links with selector: {selector}")
                break
        
        # Print all links
        for idx, link in enumerate(institution_links):
            link_text = link.get_text(strip=True)
            href = link.get('href', '')
            print(f"      → DEBUG: Link #{idx+1}: '{link_text}' → {href[:60] if href else 'NO HREF'}")
        
        # Find (HS) link and extract HS ID
        for link in institution_links:
            link_text = link.get_text(strip=True)
            
            if '(HS)' in link_text:
                hs_url = link.get('href', '')
                if not hs_url:
                    continue
                    
                if hs_url.startswith('/'):
                    hs_url = f"https://247sports.com{hs_url}"
                    
                hs_name = link_text.replace('(HS)', '').strip()
                
                # EXTRACT HS ID from URL
                hs_id = None
                hs_id_match = re.search(r'/high-school-(\d+)', hs_url)
                if hs_id_match:
                    hs_id = hs_id_match.group(1)
                
                print(f"      ✅ DEBUG: Found HS profile!")
                print(f"         Name: {hs_name}")
                print(f"         URL: {hs_url}")
                print(f"         HS ID: {hs_id}")
                
                return (hs_url, hs_name, hs_id)
        
        print(f"      ⚠️  DEBUG: No (HS) link found")
        return (None, None, None)
        
    except Exception as e:
        print(f"      ❌ DEBUG: Exception: {e}")
        import traceback
        traceback.print_exc()
        return (None, None, None)


# SOLUTION 2: Extract all IDs from the institution links

async def extract_all_institution_ids(page) -> dict:
    """
    Extract all 247 IDs for a player across all institutions.
    Returns dict with keys: 'base', 'juco', 'hs', 'colleges'
    """
    try:
        print(f"      → DEBUG: Extracting all institution IDs...")
        
        # Force dropdown visible
        await page.evaluate('''() => {
            const list = document.querySelector('ul.institution-list');
            if (list) {
                list.classList.remove('hidden');
                list.style.display = 'block';
            }
        }''')
        
        await page.wait_for_timeout(500)
        
        html = await page.content()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        ids = {
            'base': None,
            'juco': None,
            'hs': None,
            'colleges': []
        }
        
        # Get base ID from current URL
        current_url = page.url
        base_match = re.search(r'/player/[^/]+-(\d+)', current_url)
        if base_match:
            ids['base'] = base_match.group(1)
        
        # Parse all institution links
        all_links = soup.select('a[href*="/player/"]')
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # JUCO ID
            if '/junior-college-' in href:
                juco_match = re.search(r'/junior-college-(\d+)', href)
                if juco_match and not ids['juco']:
                    ids['juco'] = juco_match.group(1)
                    print(f"      → Found JUCO ID: {ids['juco']}")
            
            # HS ID
            elif '/high-school-' in href:
                hs_match = re.search(r'/high-school-(\d+)', href)
                if hs_match and not ids['hs']:
                    ids['hs'] = hs_match.group(1)
                    print(f"      → Found HS ID: {ids['hs']}")
            
            # College IDs (can be multiple)
            elif '/college-' in href and '(NCAA)' in text:
                college_match = re.search(r'/college-(\d+)', href)
                if college_match:
                    college_id = college_match.group(1)
                    if college_id not in ids['colleges']:
                        ids['colleges'].append(college_id)
                        print(f"      → Found College ID: {college_id} ({text})")
        
        print(f"      ✓ DEBUG: IDs extracted - Base: {ids['base']}, JUCO: {ids['juco']}, HS: {ids['hs']}, Colleges: {len(ids['colleges'])}")
        return ids
        
    except Exception as e:
        print(f"      ⚠️  DEBUG: Error extracting IDs: {e}")
        return {'base': None, 'juco': None, 'hs': None, 'colleges': []}


# USAGE IN parse_profile():
#
# # After loading JUCO profile:
# ids = await extract_all_institution_ids(page)
# data['247 Base ID'] = ids['base'] or "NA"
# data['247 JUCO ID'] = ids['juco'] or "NA"
# data['247 HS ID'] = ids['hs'] or "NA"
# data['247 College IDs'] = ','.join(ids['colleges']) if ids['colleges'] else "NA"
#
# # For HS profile finding:
# hs_url, hs_name, hs_id = await find_most_recent_hs_profile_ENHANCED(page)
# if hs_id:
#     data['247 HS ID'] = hs_id


# UPDATE CSV_HEADERS to include:
CSV_HEADERS = [
    "247 Base ID", "247 JUCO ID", "247 HS ID", "247 College IDs",
    "Player Name", "Position", "Height", "Weight", "City, ST", "Class",
    # ... rest of headers ...
]
