"""
247Sports JUCO Recruiting Class Scraper - DEBUG VERSION
Scrapes JUCO recruiting class data from 247Sports (2016-2027)

DEBUG FEATURES:
- Extensive logging for HS profile dropdown detection
- Shows exactly what institution links are found
- Helps diagnose why HS data isn't being scraped
"""

import asyncio
import csv
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# =============================================================================
# CONFIGURATION
# =============================================================================

YEARS = [int(os.getenv('SCRAPE_YEAR', '2024'))]
OUTPUT_DIR = Path("output")
TEST_MODE = os.getenv('TEST_MODE', 'false').lower() == 'true'
MAX_CONCURRENT = 4
DEEP_TIMELINE_LIMIT = 1000

# Resume capability
START_FROM_PLAYER = int(os.getenv('START_FROM', '0'))

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# =============================================================================
# DATA STRUCTURES
# =============================================================================

CSV_HEADERS = [
    "247 ID", "Player Name", "Position", "Height", "Weight", "City, ST", "Class",
    "Junior College", "High School", "HS Class Year",
    "247 JUCO Stars", "247 JUCO Rating", "247 JUCO National Rank", 
    "247 JUCO Position", "247 JUCO Position Rank",
    "Composite JUCO Stars", "Composite JUCO Rating", "Composite JUCO National Rank",
    "Composite JUCO Position", "Composite JUCO Position Rank",
    "247 HS Stars", "247 HS Rating", "247 HS National Rank",
    "247 HS Position", "247 HS Position Rank",
    "Composite HS Stars", "Composite HS Rating", "Composite HS National Rank",
    "Composite HS Position", "Composite HS Position Rank",
    "Signed Date", "Signed Team", "Draft Date", "Draft Team",
    "Recruiting Year", "Profile URL", "Scrape Date", "Data Source"
]

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def extract_player_id(url: str) -> str:
    match = re.search(r'/player/[^/]+-(\d+)/', url)
    return match.group(1) if match else "NA"

def clean_text(text: str) -> str:
    if not text: return "NA"
    # Replace non-breaking spaces and other whitespace
    cleaned = text.strip().replace('\n', ' ').replace('\r', '').replace('\xa0', ' ')
    return cleaned

def normalize_height(height_str: str) -> str:
    if not height_str or height_str == "NA": 
        return "NA"
    height_str = height_str.strip().strip("'\"")
    if '-' in height_str or "'" in height_str or (len(height_str) <= 4 and any(c.isdigit() for c in height_str)):
        return f"'{height_str}"
    return height_str

def parse_rank(text: str) -> str:
    if not text: return "NA"
    match = re.search(r'#?(\d+)', text)
    return match.group(1) if match else "NA"

def normalize_date(date_str: str) -> str:
    if not date_str: return "NA"
    date_str = clean_text(date_str)
    formats = ["%m/%d/%Y", "%b %d, %Y", "%B %d, %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%m/%d/%Y")
        except ValueError:
            continue
    return date_str

def is_date_valid_for_class(date_str: str, recruiting_year: int) -> bool:
    if date_str == "NA": return False
    try:
        dt = datetime.strptime(date_str, "%m/%d/%Y")
        cutoff_date = datetime(recruiting_year, 9, 1)
        return dt < cutoff_date
    except:
        return True

def append_to_csv(filename: Path, players: list):
    file_exists = filename.exists()
    with open(filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(players)

# =============================================================================
# LOAD MORE FUNCTIONALITY
# =============================================================================

async def click_load_more_until_complete(browser, year: int) -> list:
    print(f"\n📋 Loading all JUCO players for {year}...")
    context = await browser.new_context(user_agent=USER_AGENT)
    page = await context.new_page()
    
    # Correct Modern URL for JUCO Rankings
    url = f"https://247sports.com/Season/{year}-Football/CompositeRecruitRankings/?InstitutionGroup=JuniorCollege"
    
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        try:
            await page.wait_for_selector(".rankings-page__list-item", timeout=10000)
        except Exception:
            print("⚠️ Timeout waiting for list items to hydrate")
    except Exception as e:
        print(f"❌ Failed to load initial page for {year}: {e}")
        await context.close()
        return []

    selectors = ["li.rankings-page__list-item", "li.recruit", ".rankings-page__container ul > li"]
    valid_selector = None
    for selector in selectors:
        count = await page.locator(selector).count()
        if count > 0:
            valid_selector = selector
            print(f"  ✓ Found {count} players using selector: '{selector}'")
            break
            
    if not valid_selector:
        print(f"⚠️  No players found")
        await context.close()
        return []

    click_count = 0
    max_clicks = 500 if not TEST_MODE else 3
    
    while click_count < max_clicks:
        current_players = await page.locator(valid_selector).count()
        load_more_button = page.locator('a.load-more, button.load-more, a.rankings-page__showmore, a:has-text("Load More")')
        try:
            if await load_more_button.count() > 0 and await load_more_button.first.is_visible():
                print(f"  → Click #{click_count + 1}: {current_players} players loaded...")
                await load_more_button.first.click()
                await page.wait_for_timeout(1500)
                click_count += 1
            else:
                print(f"  ✓ All players loaded!")
                break
        except Exception:
            break
    
    print(f"\n🔗 Extracting player profile URLs...")
    player_links = await page.locator(f'{valid_selector} a.rankings-page__name-link, {valid_selector} a.recruit').all()
    if not player_links:
         player_links = await page.locator(f'{valid_selector} a[href*="/player/"]').all()

    player_urls = []
    for link in player_links:
        href = await link.get_attribute('href')
        if href and '/player/' in href:
            if href.startswith('/'): href = f"https://247sports.com{href}"
            player_urls.append(href)
    
    player_urls = list(dict.fromkeys(player_urls))
    print(f"  ✓ Found {len(player_urls)} player profiles")
    
    if TEST_MODE and len(player_urls) > 50:
        player_urls = player_urls[:50]
        print(f"  ℹ️  TEST MODE: Limited to 50 players")
    
    await context.close()
    return player_urls

# =============================================================================
# PROFILE PARSING
# =============================================================================

async def navigate_to_recruiting_profile(page) -> bool:
    """Ensures we are on the 'Recruiting' tab of the profile"""
    try:
        recruiting_link = page.locator('a:has-text("View recruiting profile"), a:has-text("Recruiting Profile")')
        if await recruiting_link.count() > 0:
            await recruiting_link.first.click()
            await page.wait_for_load_state('domcontentloaded', timeout=30000)
            await page.wait_for_timeout(1000)
            return True
        return False
    except:
        return False

async def find_most_recent_hs_profile(page) -> tuple:
    """
    DIAGNOSTIC: Dump HTML to see what Playwright actually sees
    """
    try:
        print(f"      🔍 DEBUG: Starting HS profile search...")
        
        # Wait for page to load
        await page.wait_for_timeout(3000)
        
        html = await page.content()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for institution-block div
        institution_block = soup.select_one('div.institution-block')
        if institution_block:
            print(f"      ✓ DEBUG: Found institution-block div!")
            print(f"      → DEBUG: HTML inside institution-block:")
            print(f"      {institution_block.prettify()[:500]}")
        else:
            print(f"      ❌ DEBUG: No div.institution-block found!")
        
        # Look for ANY ul on the page
        all_uls = soup.select('ul')
        print(f"      → DEBUG: Found {len(all_uls)} total <ul> elements on page")
        
        # Look for institution-list
        inst_lists = soup.select('.institution-list')
        print(f"      → DEBUG: Found {len(inst_lists)} elements with class 'institution-list'")
        
        # Try to find ANY links with "(HS)" text
        all_links = soup.select('a')
        hs_links = [link for link in all_links if '(HS)' in link.get_text()]
        print(f"      → DEBUG: Found {len(hs_links)} links containing '(HS)' text")
        
        for link in hs_links[:3]:
            print(f"      → DEBUG: HS link: {link.get_text()[:50]} → {link.get('href', 'NO HREF')[:60]}")
        
        # If we found HS links directly, use them!
        if hs_links:
            link = hs_links[0]  # First (most recent) HS
            hs_url = link.get('href', '')
            if hs_url:
                if hs_url.startswith('/'):
                    hs_url = f"https://247sports.com{hs_url}"
                hs_name = link.get_text().replace('(HS)', '').strip()
                print(f"      ✅ DEBUG: Found HS profile!")
                print(f"         Name: {hs_name}")
                print(f"         URL: {hs_url}")
                return (hs_url, hs_name)
        
        print(f"      ❌ DEBUG: No HS profile found")
        return (None, None)
        
    except Exception as e:
        print(f"      ❌ DEBUG: Exception: {e}")
        import traceback
        traceback.print_exc()
        return (None, None)

async def parse_timeline(page, data, year, do_deep_dive: bool):
    try:
        html = await page.content()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        items = soup.select('.timeline-item, .timeline li, ul.timeline > li, .vertical-timeline-element-content')
        for item in items:
            item_text = clean_text(item.get_text())
            if 'draft' in item_text.lower():
                date_match = re.search(r'([A-Z][a-z]+\s+\d{1,2},\s+\d{4}|\d{1,2}/\d{1,2}/\d{4})', item_text)
                if date_match and data['Draft Date'] == "NA":
                     data['Draft Date'] = normalize_date(date_match.group(1))
                team_match = re.search(r'(?:Draft[:\s]+)?([A-Z][A-Za-z0-9\s\.]+?)\s+(?:select|pick)', item_text, re.IGNORECASE)
                if team_match and data['Draft Team'] == "NA":
                    team_name = clean_text(team_match.group(1))
                    team_name = re.sub(r'^Draft\s*', '', team_name, flags=re.IGNORECASE).strip()
                    if team_name and team_name.lower() not in ['draft']:
                        data['Draft Team'] = team_name
            
            item_priority = 0
            if 'commitment' in item_text.lower() or 'committed' in item_text.lower() or 'commits to' in item_text.lower():
                 item_priority = 100
            elif 'signed' in item_text.lower() or 'signing' in item_text.lower():
                 item_priority = 1
            
            if item_priority > 0:
                date_match = re.search(r'([A-Z][a-z]+\s+\d{1,2},\s+\d{4}|\d{1,2}/\d{1,2}/\d{4})', item_text)
                found_date = normalize_date(date_match.group(1)) if date_match else "NA"
                if found_date != "NA" and is_date_valid_for_class(found_date, year):
                    current_priority = data.get('_date_priority', -1)
                    if item_priority > current_priority:
                        data['Signed Date'] = found_date
                        data['_date_priority'] = item_priority
                        team_match = re.search(r'(?:to|with|at|commits to)\s+([A-Z][^,.]+)', item_text)
                        if team_match:
                            data['Signed Team'] = clean_text(team_match.group(1))
        
        if do_deep_dive:
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(1500)
            see_all_link = page.locator('a[href*="TimelineEvents"]')
            if await see_all_link.count() > 0:
                href = await see_all_link.first.get_attribute('href')
                if href:
                    full_timeline_url = f"https://247sports.com{href}" if href.startswith('/') else href
                    try:
                        await page.goto(full_timeline_url, wait_until='domcontentloaded', timeout=15000)
                        page_count = 0
                        while page_count < 10:
                            html = await page.content()
                            soup = BeautifulSoup(html, 'html.parser')
                            full_items = soup.select('ul.timeline-event-index_lst li')
                            for item in full_items:
                                item_text = clean_text(item.get_text())
                                item_priority = 0
                                if 'commitment' in item_text.lower() or 'committed' in item_text.lower() or 'commits to' in item_text.lower():
                                     item_priority = 100
                                elif 'signed' in item_text.lower() or 'signing' in item_text.lower():
                                     item_priority = 1
                                if item_priority > 0:
                                    date_match = re.search(r'([A-Z][a-z]+\s+\d{1,2},\s+\d{4}|\d{1,2}/\d{1,2}/\d{4})', item_text)
                                    found_date = normalize_date(date_match.group(1)) if date_match else "NA"
                                    if found_date != "NA" and is_date_valid_for_class(found_date, year):
                                        current_priority = data.get('_date_priority', -1)
                                        if item_priority > current_priority:
                                            data['Signed Date'] = found_date
                                            data['_date_priority'] = item_priority
                                            team_match = re.search(r'(?:to|with|at|commits to)\s+([A-Z][^,.]+)', item_text)
                                            if team_match:
                                                data['Signed Team'] = clean_text(team_match.group(1))
                                            if item_priority == 100: return
                            next_button = page.locator('li.next_itm a')
                            if await next_button.count() > 0 and await next_button.is_visible():
                                await next_button.click()
                                await page.wait_for_timeout(1000)
                                page_count += 1
                            else: break
                    except Exception: pass
    except Exception: pass

# --- FIXED RANKING PARSER ---
def parse_rankings_section_robust(soup, data, prefix_map, institution_check=None):
    """
    Robust ranking parser that handles the 247Sports Composite headers
    and extracts ranks even if specific tags (like <strong>) are missing.
    """
    ranking_sections = soup.select('section.rankings, section.rankings-section, div.ranking-section')
    
    for section in ranking_sections:
        header = section.select_one('.rankings-header h3, h3.title, h3')
        if not header: continue
        
        # Upper case and clean to handle "®" or other symbols
        header_text = clean_text(header.get_text()).upper()
        
        prefix = None
        # Robust Header Matching
        if "COMPOSITE" in header_text:
            prefix = prefix_map.get("COMPOSITE")
        elif "247SPORTS" in header_text and "COMPOSITE" not in header_text:
            prefix = prefix_map.get("247SPORTS")
            
        if not prefix: continue
        
        # Stars
        stars = section.select('span.icon-starsolid.yellow, i.icon-starsolid.yellow')
        if stars: data[f'{prefix} Stars'] = str(min(len(stars), 5))
        
        # Rating
        rating_elem = section.select_one('.rank-block, .score, .rating')
        if rating_elem:
            rating_text = clean_text(rating_elem.get_text())
            rating_match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
            if rating_match: data[f'{prefix} Rating'] = rating_match.group(1)

        # Ranks
        ranks_list = section.select_one('ul.ranks-list')
        if ranks_list:
            for li in ranks_list.select('li'):
                pos_node = li.select_one('b')
                link_tag = li.select_one('a')
                
                if link_tag:
                    href = link_tag.get('href', '')
                    
                    # EXTRACT RANK TEXT ROBUSTLY (Try <strong>, then fallback to <a> text)
                    rank_node = link_tag.select_one('strong')
                    rank_text_raw = rank_node.get_text() if rank_node else link_tag.get_text()
                    rank_val = parse_rank(rank_text_raw)

                    # Position Rank
                    if 'Position=' in href:
                        if pos_node: 
                            data[f'{prefix} Position'] = clean_text(pos_node.get_text())
                        data[f'{prefix} Position Rank'] = rank_val
                    
                    # Skip State Ranks
                    elif 'State=' in href or 'state=' in href:
                        continue
                    
                    # National Rank (Checks InstitutionGroup if provided)
                    elif institution_check and f'InstitutionGroup={institution_check}' in href:
                         data[f'{prefix} National Rank'] = rank_val

async def parse_profile(page, url: str, year: int, player_num: int, total: int) -> dict:
    data = {header: "NA" for header in CSV_HEADERS}
    data['Profile URL'] = url
    data['Recruiting Year'] = str(year)
    data['Scrape Date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data['Data Source'] = '247Sports JUCO'
    data['_date_priority'] = -1
    
    try:
        # --- 1. LOAD JUCO PROFILE PAGE ---
        # Everything is already on this page - no tab clicking needed!
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(2000)  # Wait for JavaScript to fully render the page
        
        # --- 2. SCRAPE JUCO DATA DIRECTLY ---
        html = await page.content()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        data['247 ID'] = extract_player_id(url)
        
        # Header Info
        name_elem = soup.select_one('.name') or soup.select_one('h1.name')
        if name_elem: data['Player Name'] = clean_text(name_elem.get_text())
        
        all_header_items = soup.select('.metrics-list li') + soup.select('.details li') + soup.select('ul.vitals li')
        for item in all_header_items:
            text = item.get_text(strip=True)
            if 'Pos' in text or 'Position' in text:
                match = re.search(r'(?:Pos|Position)[:\s]*(.*)', text, re.IGNORECASE)
                if match: data['Position'] = clean_text(match.group(1))
            elif 'Height' in text:
                match = re.search(r'Height[:\s]*(.*)', text, re.IGNORECASE)
                if match: data['Height'] = normalize_height(match.group(1))
            elif 'Weight' in text:
                match = re.search(r'Weight[:\s]*(.*)', text, re.IGNORECASE)
                if match: data['Weight'] = clean_text(match.group(1))
            elif 'Junior College' in text:
                match = re.search(r'Junior College[:\s]*(.*)', text, re.IGNORECASE)
                if match: data['Junior College'] = clean_text(match.group(1))
            elif 'Home Town' in text or 'Hometown' in text or 'City' in text:
                match = re.search(r'(?:Home Town|Hometown|City)[:\s]*(.*)', text, re.IGNORECASE)
                if match: data['City, ST'] = clean_text(match.group(1))
            elif 'Class' in text:
                match = re.search(r'Class[:\s]*(.*)', text, re.IGNORECASE)
                if match: data['Class'] = clean_text(match.group(1))
        
        data['Class'] = str(year)
        
        # JUCO RANKINGS
        juco_map = {"COMPOSITE": "Composite JUCO", "247SPORTS": "247 JUCO"}
        parse_rankings_section_robust(soup, data, juco_map, institution_check="JuniorCollege")

        # Timeline
        do_deep_dive = player_num <= DEEP_TIMELINE_LIMIT
        await parse_timeline(page, data, year, do_deep_dive)

        # --- 3. NOW CLICK JUCO DROPDOWN TO GET HS PROFILE ---
        # The dropdown is visible on initial page load
        hs_url, hs_name = await find_most_recent_hs_profile(page)
        
        if hs_url and hs_name:
            data['High School'] = hs_name
            try:
                print(f"      → DEBUG: Clicking HS profile link: {hs_name}")
                print(f"      → DEBUG: Navigating to: {hs_url[:60]}...")
                
                # Click the HS link - it will automatically load the recruiting profile
                await page.goto(hs_url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(2000)  # Wait for page to fully load
                
                # NO NEED to click "View recruiting profile" - it auto-loads
                
                hs_html = await page.content()
                hs_soup = BeautifulSoup(hs_html, 'html.parser')
                
                # HS Class Year
                hs_header_items = hs_soup.select('.metrics-list li') + hs_soup.select('.details li') + hs_soup.select('ul.vitals li')
                for item in hs_header_items:
                    text = item.get_text(strip=True)
                    if 'Class' in text:
                        match = re.search(r'Class[:\s]*(.*)', text, re.IGNORECASE)
                        if match: 
                            data['HS Class Year'] = clean_text(match.group(1))
                            print(f"      ✓ DEBUG: Found HS Class Year: {data['HS Class Year']}")
                
                # HS RANKINGS
                print(f"      → DEBUG: Parsing HS rankings...")
                hs_map = {"COMPOSITE": "Composite HS", "247SPORTS": "247 HS"}
                parse_rankings_section_robust(hs_soup, data, hs_map, institution_check="HighSchool")
                print(f"      ✓ DEBUG: HS Rankings - 247: {data['247 HS Stars']}⭐ / Composite: {data['Composite HS Stars']}⭐")
                
            except Exception as e:
                print(f"      ❌ DEBUG: Could not load HS profile: {e}")

        # Fallback for Signed Team
        if data['Signed Team'] == "NA":
            commit_banner = soup.select_one('.commit-banner, .commitment')
            if commit_banner:
                team_elem = commit_banner.select_one('span, a')
                if team_elem:
                    team_text = clean_text(team_elem.get_text())
                    if team_text.lower() not in ['committed', 'commitment', 'signed']:
                        data['Signed Team'] = team_text
        
        return data
        
    except Exception as e:
        print(f"    ❌ Error parsing {data.get('Player Name', 'Unknown')}: {e}")
        return data

# =============================================================================
# CONCURRENT SCRAPING
# =============================================================================

async def scrape_player_batch(browser, urls: list, year: int, batch_num: int, total_players: int) -> list:
    tasks = []
    context = await browser.new_context(user_agent=USER_AGENT)
    for i, url in enumerate(urls):
        page = await context.new_page()
        player_num = batch_num * MAX_CONCURRENT + i + 1
        tasks.append(scrape_player(page, url, year, player_num, total_players))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    await context.close()
    valid_results = []
    for result in results:
        if isinstance(result, dict):
            if '_date_priority' in result: del result['_date_priority']
            valid_results.append(result)
    return valid_results

async def scrape_player(page, url: str, year: int, player_num: int, total: int) -> dict:
    try:
        print(f"  [{player_num}/{total}] {url.split('/')[-2]}")
        data = await parse_profile(page, url, year, player_num, total)
        if data['Player Name'] != "NA":
            deep_marker = "🔍" if player_num <= DEEP_TIMELINE_LIMIT else "⚡"
            hs_marker = "+" if data['High School'] != "NA" else ""
            print(f"    ✓ {deep_marker}{hs_marker} {data['Player Name']} - JUCO: {data['Composite JUCO Stars']}⭐ / HS: {data['Composite HS Stars']}⭐")
        return data
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return {header: "NA" for header in CSV_HEADERS}
    finally:
        await page.close()

# =============================================================================
# MAIN SCRAPER
# =============================================================================

async def scrape_year(browser, year: int) -> list:
    print(f"\n{'='*80}")
    print(f"🎓 SCRAPING {year} JUCO RECRUITING CLASS (DEBUG MODE)")
    print(f"{'='*80}")
    player_urls = await click_load_more_until_complete(browser, year)
    if not player_urls:
        print(f"  ❌ No players found for {year}")
        return []
    if START_FROM_PLAYER > 0:
        print(f"  ⏩ Resuming from player #{START_FROM_PLAYER}")
        player_urls = player_urls[START_FROM_PLAYER:]
    
    print(f"\n🔄 Scraping {len(player_urls)} player profiles...")
    year_range = f"{min(YEARS)}-{max(YEARS)}" if len(YEARS) > 1 else str(YEARS[0])
    timestamp = datetime.now().strftime('%Y%m%d')
    filename = OUTPUT_DIR / f"juco_recruiting_class_{year_range}_{timestamp}.csv"
    
    all_data = []
    batch_buffer = []
    for i in range(0, len(player_urls), MAX_CONCURRENT):
        batch = player_urls[i:i + MAX_CONCURRENT]
        batch_num = i // MAX_CONCURRENT
        print(f"\n  📦 Batch {batch_num + 1}/{(len(player_urls) + MAX_CONCURRENT - 1) // MAX_CONCURRENT}")
        batch_data = await scrape_player_batch(browser, batch, year, batch_num, len(player_urls))
        all_data.extend(batch_data)
        batch_buffer.extend(batch_data)
        if len(batch_buffer) >= 100:
            append_to_csv(filename, batch_buffer)
            print(f"    💾 Saved {len(batch_buffer)} players to CSV")
            batch_buffer = []
        print(f"    → Progress: {len(all_data)}/{len(player_urls)} players")
    
    if batch_buffer:
        append_to_csv(filename, batch_buffer)
        print(f"    💾 Saved final {len(batch_buffer)} players to CSV")
    print(f"\n✅ Completed {year}: {len(all_data)} players scraped")
    return all_data

async def main():
    print("\n" + "="*80)
    print("🏈 247SPORTS JUCO SCRAPER - DEBUG VERSION")
    print("="*80)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        all_players = []
        for year in YEARS:
            year_data = await scrape_year(browser, year)
            all_players.extend(year_data)
        await browser.close()
    if not all_players:
        print("\n❌ CRITICAL: No data scraped.")
        sys.exit(1)
    print(f"\n✅ SCRAPING COMPLETE! Total Players: {len(all_players)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        sys.exit(1)
