# 247Sports JUCO Recruiting Class Scraper

🏈 **Automated scraper for 247Sports Junior College recruiting data (2016-2027)**

Scrapes both **JUCO profile data** AND **High School profile data** for comprehensive recruiting analytics.

---

## 🎯 What This Scraper Does

For each JUCO player, it collects:

### JUCO Profile Data:
- 247SPORTSJUCO ratings (Stars, Rating, National Rank, Position Rank)
- Composite JUCO ratings (Stars, Rating, National Rank, Position Rank)
- Junior College name
- Basic info (Name, Position, Height, Weight, City, Class)

### Most Recent High School Profile Data:
- 247SPORTS ratings (Stars, Rating, National Rank, Position Rank)
- Composite ratings (Stars, Rating, National Rank, Position Rank)
- High School name and Class Year

### Timeline Data:
- Commitment date and team (4-year school)
- Draft date and team (if applicable)

**Output:** 36-column CSV with complete recruiting journey from HS → JUCO → College/Draft

---

## 📊 Features

✅ **Matrix Execution** - Run multiple years simultaneously (2016-2027)  
✅ **Dual Profile Scraping** - Automatically finds and scrapes most recent HS profile  
✅ **Deep Timeline Parsing** - Gets commitment dates for top 1000 players  
✅ **Incremental Saves** - No data loss on timeout (saves every 100 players)  
✅ **Resume Capability** - Continue from where it left off  
✅ **Combined CSV Output** - All years merged into one file  
✅ **Test Mode** - Quick 50-player test runs  

---

## 🚀 Quick Start

### 1. Create Repository

```bash
# On GitHub
Create new repo: juco-recruiting-scraper-matrix
Initialize with README
```

### 2. Upload Files

Upload these files to your repo:
- `scraper.py` (main scraper)
- `requirements.txt` (dependencies)
- `validate_output.py` (CSV validator)
- `.github/workflows/scraper.yml` (workflow file)

### 3. Run Workflow

1. Go to **Actions** tab
2. Click **"Run JUCO Recruiting Class Scraper"**
3. Select options:
   - **Years:** "All Years (2016-2027)" or any subset
   - **Test Mode:** `false` for production, `true` for 50-player test
4. Click **"Run workflow"**

### 4. Download Results

After completion, download artifacts:
- **JUCO_Combined_CSV_All_Years** ← One file with all years
- **JUCO_CSV_Output_YEAR** ← Individual files per year

---

## ⚙️ Configuration Options

### Year Selection Dropdown:

**Preset Ranges:**
- All Years (2016-2027) ← 12 years
- Historical (2016-2019) ← 4 years
- Core Years (2020-2022) ← 3 years
- Recent Years (2023-2027) ← 5 years

**Individual Years:**
- 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027

### Test Mode:
- `true` = Scrape 50 players (~9-10 minutes)
- `false` = Scrape all players (~1-2 hours per year)

---

## 📋 CSV Output Structure (36 columns)

```
# Basic Info (7)
247 ID, Player Name, Position, Height, Weight, City ST, Class

# School Info (3)
Junior College, High School, HS Class Year

# JUCO Ratings - 247SPORTSJUCO (5)
247 JUCO Stars, 247 JUCO Rating, 247 JUCO National Rank, 
247 JUCO Position, 247 JUCO Position Rank

# JUCO Ratings - Composite JUCO (5)
Composite JUCO Stars, Composite JUCO Rating, Composite JUCO National Rank,
Composite JUCO Position, Composite JUCO Position Rank

# HS Ratings - 247SPORTS (5)
247 HS Stars, 247 HS Rating, 247 HS National Rank,
247 HS Position, 247 HS Position Rank

# HS Ratings - Composite (5)
Composite HS Stars, Composite HS Rating, Composite HS National Rank,
Composite HS Position, Composite HS Position Rank

# Timeline (4)
Signed Date, Signed Team, Draft Date, Draft Team

# Meta (3)
Recruiting Year, Profile URL, Scrape Date, Data Source
```

---

## ⏱️ Performance

### Per Player:
- **~10-12 seconds** (JUCO profile + HS profile + timeline)

### Estimated Runtimes:

**50-player test:**
- Time: ~9-10 minutes
- Use: Validate scraper works correctly

**Full year (~400 JUCO players):**
- Time: ~70-90 minutes
- Runs in parallel with other years

**All 12 years (2016-2027) in parallel:**
- Time: ~1.5-2 hours
- All years complete simultaneously

---

## 🔧 Advanced Features

### Resume Capability

If a run times out, resume from where it left off:

1. Check last player number in CSV (e.g., player 350)
2. Go to Actions → Re-run workflow
3. Set environment variable: `START_FROM=350`

### Concurrency Adjustment

Edit `scraper.py` line 30:
```python
MAX_CONCURRENT = 4  # Increase to 6 or 8 for faster scraping
```

⚠️ Higher concurrency = faster but higher chance of rate limiting

---

## 📊 Example Use Cases

### Track JUCO → FBS Pipeline
Filter combined CSV by Signed Team to see which schools recruit most from JUCO

### Analyze Rating Differences
Compare HS ratings vs JUCO ratings to identify improvement/decline

### Predict NFL Success
Correlate JUCO+HS ratings with Draft outcomes

### Recruiting Trends
Analyze which positions transfer through JUCO most frequently

---

## 🐛 Troubleshooting

### "No players found for YEAR"
- Year may have very few JUCO recruits
- Check 247Sports website manually to confirm

### Workflow times out
- Use Resume Capability (see Advanced Features)
- Or run fewer years at once

### Some HS data is "NA"
- Player may not have a 247Sports HS profile
- Expected behavior, not an error

### Rate limiting errors
- Reduce MAX_CONCURRENT in scraper.py
- Run fewer years simultaneously

---

## 🤝 Contributing

Found a bug? Have a feature request?
1. Open an Issue
2. Submit a Pull Request
3. Contact: [Your contact info]

---

## 📜 License

This project is for educational and research purposes.  
Respect 247Sports' Terms of Service and rate limits.

---

## 🙏 Credits

Built for advanced college football recruiting analytics.  
Data source: 247Sports.com

---

**Happy Scraping!** 🏈📊
