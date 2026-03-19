# NSE Insights - Production Enhancement Plan

**Status**: In Development
**Target**: Production-ready before launch
**Repository**: https://github.com/NthigaLee/nse-insights

---

## 1. Theme Toggle Bug Fix
**Priority**: HIGH | **Effort**: 1-2 hours

### Problem
Changing light/dark mode reverts to Safaricom PLC instead of maintaining current company view.

### Root Cause
Theme toggle likely triggering a page reload or state reset that loses the selected company context.

### Solution
- Store selected company in sessionStorage before theme change
- Restore company after theme toggle completes
- Prevent page reload during theme change
- Maintain chart state and active view (companies/sectors)

**Files to modify**:
- `frontend/app.js` - Fix `toggleTheme()` function
- `frontend/styles.css` - Ensure CSS variables persist across theme change

---

## 2. Sectors Tab Enhancement
**Priority**: HIGH | **Effort**: 8-12 hours

### Features
1. **Sector Grid** → **Sector Detail Page** (on click)
2. **Sector Overview Card** with:
   - Market cap (total + % of NSE All Share)
   - Sector performance (YTD, 52wk)
   - Key metrics by company type:
     - Banks: Loan book value, NPL ratio, tier-1 capital, ROE
     - Insurance: Loss ratio, expense ratio, premium growth
     - Tech: Revenue growth, EPS growth, P/E vs market
   - Gearing ratio (total debt/equity)
   - Liquidity ratio (current ratio for companies)
   - Recent sector news (prioritize local: Business Daily, KDN, Capital FM)

3. **Company List in Sector** with sortable columns:
   - Company name, Market cap, 52wk change, Key metric (loan book/loss ratio/etc), Latest price

### Data Sources
- Extract from `data.js` NSE company financial data
- Aggregate by sector using company mappings
- Fetch news via: Business Daily, KDN, Capital FM (web scrape or API)
- Calculate ratios from latest quarter/annual financials

**Files to modify/create**:
- `frontend/app.js` - Add sector detail view, calculations
- `frontend/styles.css` - Sector detail page styles
- `frontend/index.html` - Sector detail DOM structure
- `frontend/fetch-sector-news.js` (NEW) - News aggregation

---

## 3. Admin Tab - PDF Viewer Redesign
**Priority**: HIGH | **Effort**: 6-8 hours

### Current State
- Basic PDF list in admin.html

### Target State (Reference Image)
- **Sidebar** (appears on hover >1 sec, hides on mouse out)
  - Company list filtered by data coverage status
  - Visual indicators (● green = complete, ● yellow = partial, ● red = missing)
  - Hover expands company info

- **PDF Viewer Panel** (center)
  - Full-screen PDF reader
  - Toolbar: prev/next page, zoom, download, keyboard navigation
  - Page indicator (Page 1 / 73)
  - Breadcrumb: Company > Report Type > Year
  - Side panel shows financial statements extracted from PDF (Income Statement, Balance Sheet, etc)

- **Metadata Panel** (right)
  - Company info
  - Report type (Annual, Q1, Q2, Q3, Q4)
  - Year
  - Key financials extracted from report

### Implementation
- Use PDF.js library for viewer (already included)
- Create hover-reveal sidebar with 1s delay
- Parse PDF.js text extraction to populate financial statements
- Auto-extract from known PDF locations (page 1 for cover, page 2-3 for statements)

**Files to modify**:
- `frontend/admin.html` - Restructure layout
- `frontend/styles.css` - PDF viewer + sidebar styles
- `frontend/admin-viewer.js` (NEW) - PDF viewing logic
- `frontend/pdf-parser.js` (NEW) - Extract statements from PDF text

---

## 4. Companies Tab - Interactive Financials
**Priority**: MEDIUM | **Effort**: 8-10 hours

### Current State
- Company view shows all market summary + financials charts

### Target State
1. **Hide market summary** when company is selected (only show on initial dashboard)
2. **Interactive Charts**:
   - Click on a chart → Expands to full-screen modal
   - Bar chart → Double-click a bar → Opens relevant PDF/statement
   - If balance sheet double-click → Opens admin PDF viewer showing balance sheet
   - If income statement → Shows income statement from PDF
   - Falls back to opening full PDF if statement not available

3. **Chart Drill-down**:
   - Financial metric chart bars are clickable
   - Click = expand in modal
   - Dbl-click = open source PDF at relevant page
   - Show which PDF/page this data came from

### Implementation
- Add state tracking for market summary visibility
- Enhance Chart.js click handlers with expand functionality
- Link charts to PDF documents via `data_quality.json` mappings
- Store PDF page numbers for each financial statement

**Files to modify**:
- `frontend/app.js` - Hide market summary on company select, chart click handlers
- `frontend/index.html` - Add modal for expanded charts
- `frontend/styles.css` - Modal styles
- `frontend/chart-drill-down.js` (NEW) - Chart interaction logic

---

## 5. Data Audit System
**Priority**: MEDIUM-HIGH | **Effort**: 20-30 hours

### This is a complex subsystem with multiple components

#### 5A. PDF Balance Verification
**Goal**: Automatically verify reported financial figures match PDF source

**Process**:
1. For each company, fetch latest annual/quarterly report PDF
2. Use OCR + PDF text extraction to locate key figures:
   - Balance sheet: Total assets, total liabilities, shareholders' equity
   - Income statement: Revenue, operating income, net income, EPS
3. Compare extracted figures against figures in `data.js`
4. Flag discrepancies for manual review
5. Update `data.js` if verification confirms data is correct

**Tools**:
- PDF.js for text extraction
- pytesseract for OCR (backend service)
- Manual verification workflow

**Status tracking in `data_quality.json`**:
```json
{
  "ticker": "SCOM",
  "company_name": "Safaricom PLC",
  "audit": {
    "balance_sheet": { "verified": true, "discrepancies": 0, "last_audit": "2026-03-19" },
    "income_statement": { "verified": true, "discrepancies": 0, "last_audit": "2026-03-19" }
  }
}
```

#### 5B. Company Snapshot Generator
**Goal**: Create comprehensive "company profile" with ownership, news, competitors

**Data to collect per company**:
```json
{
  "ticker": "SCOM",
  "snapshot": {
    "description": "Safaricom is East Africa's leading....",
    "ownership": {
      "total_shares": 3200000000,
      "breakdown": [
        { "institution": "British Telecom", "shares": 800000000, "percent": 25 },
        { "institution": "Vodafone", "shares": 320000000, "percent": 10 },
        { "type": "Retail/Individual", "shares": 1600000000, "percent": 50 },
        { "type": "Other Institutions", "shares": 480000000, "percent": 15 }
      ]
    },
    "major_news": [
      { "date": "2026-03-15", "headline": "Safaricom launches...", "source": "Business Daily", "url": "..." },
      { "date": "2026-03-10", "headline": "...", "source": "KDN", "url": "..." }
    ],
    "upcoming_plans": [
      "Launch of new 5G services in 2026 H2",
      "Expansion to 5 new African countries by 2027"
    ],
    "competitors": [
      { "ticker": "AIRTEL", "name": "Airtel Networks Kenya", "market_cap": "...", "sector": "Telecom" },
      { "ticker": "EQTY", "name": "Equity Group", "market_cap": "...", "sector": "Banking" }
    ],
    "sector": "Telecommunications",
    "market_cap": 450000000000,
    "updated": "2026-03-19"
  }
}
```

**Data sources**:
- Ownership: NSE fact book, company annual reports, CMA filings
- News: Web scraping from Business Daily, KDN, Capital FM, Allafrica
- Competitors: Manual mapping (data/sector-competitors.json)
- Plans: Company announcements, latest annual reports, investor presentations

#### 5C. Automated Data Audit Pipeline
**Frequency**: Quarterly (when company reports released)

**Process**:
1. Check for new PDFs (monthly)
2. Extract financial data from PDFs
3. Verify against data.js figures
4. Flag discrepancies
5. Update company snapshot
6. Generate audit report

**Backend Service**:
```bash
# Run quarterly audit
npm run audit:quarterly

# Run single company audit
npm run audit:company SCOM
```

**Output**:
- `audit-report-{date}.json` - Verification results
- Updated `data_quality.json`
- Updated company snapshots in `data.js`

**Files to create/modify**:
- `backend/audit-service.js` (NEW) - PDF extraction + verification
- `backend/snapshot-generator.js` (NEW) - Collect company snapshot data
- `backend/news-scraper.js` (NEW) - Fetch company news from sources
- `data/sector-competitors.json` (NEW) - Competitor mappings
- `frontend/ownership-chart.js` (NEW) - Render ownership pie chart
- `frontend/company-snapshot.js` (NEW) - Display snapshot data
- `frontend/index.html` - Add snapshot section before financials
- `frontend/styles.css` - Snapshot + pie chart styles

---

## 6. Mobile Optimization
**Priority**: HIGH | **Effort**: 12-16 hours

### Strategy: Mobile-First Responsive Design

#### 6A. Responsive Grid System
- Desktop: 3-column layout (company info + chart, financial charts grid, valuation)
- Tablet (768px-1024px): 2-column layout (stack smartly)
- Mobile (<768px): Full-width single-column stack

#### 6B. Mobile Navigation
- Hamburger menu instead of full nav
- Breadcrumbs for navigation context
- "Back" button to return to company list

#### 6C. Mobile-Friendly Components
1. **Company Select**
   - Full-screen select modal (not dropdown)
   - Search with autocomplete
   - Favorites section

2. **Charts on Mobile**
   - Full-width, shorter height
   - Swipeable carousel to switch between charts
   - Tap to expand instead of click
   - Double-tap for drill-down

3. **Financial Data**
   - Swipeable tabs: Income Statement | Balance Sheet | Valuation
   - Collapsible sections (expand on demand)
   - Horizontal scroll for tables

4. **Admin PDF Viewer**
   - Full-screen reader
   - Two-finger pinch to zoom
   - Swipe to next page
   - Bottom button controls

#### 6D. Touch Interactions
- Replace hover states with active/focus states
- Increase tap target size (min 44px)
- Add touch feedback (haptic where available)
- Long-press = context menu (instead of right-click)

#### 6E. Performance
- Lazy-load charts below fold
- Image optimization (use WEBP with fallbacks)
- Service worker for offline access
- Minimize JavaScript bundle

**Files to modify**:
- `frontend/styles.css` - Add @media queries, mobile styles (will be substantial)
- `frontend/index.html` - Add mobile-friendly meta tags, restructure
- `frontend/app.js` - Add mobile event handlers (tap, swipe, long-press)
- `frontend/mobile-navigation.js` (NEW) - Mobile nav logic
- `frontend/swipe-handler.js` (NEW) - Touch gesture detection
- `frontend/mobile-charts.js` (NEW) - Mobile chart UX

### Breakpoints
```css
/* Mobile First */
/* Small devices: < 480px */
/* Tablets: 481px - 768px */
/* Tablets (landscape): 769px - 1024px */
/* Desktops: > 1025px */
```

---

## Implementation Order

1. ✅ **Merge openclaw** (DONE)
2. 🔲 **Fix theme toggle bug** (1-2 hrs) ← START HERE
3. 🔲 **Mobile optimization** (12-16 hrs) - Do early so other features are mobile-ready
4. 🔲 **Sectors enhancement** (8-12 hrs)
5. 🔲 **Admin PDF viewer** (6-8 hrs)
6. 🔲 **Companies interactive financials** (8-10 hrs)
7. 🔲 **Data audit system** (20-30 hrs) - Complex, can run in parallel with other features

---

## Tech Stack & Dependencies

### Frontend
- Chart.js 4.4+ (already included)
- PDF.js (for PDF viewing - add if not present)
- date-fns (for date formatting)
- JetBrains Mono font (already configured)

### Backend (New)
- Node.js with Express (for audit service)
- pdf-parse (PDF text extraction)
- tesseract.js (OCR)
- cheerio (web scraping)
- axios (HTTP requests)

### Data
- NSE Insights data in `data.js`
- PDF reports from NSE website
- Company financials in `data_quality.json`

---

## Success Criteria

- [ ] Theme toggle maintains company context
- [ ] Sectors tab shows 5+ key metrics per sector
- [ ] Admin PDF viewer fully functional with reference design
- [ ] Financial charts are interactive with drill-down to PDFs
- [ ] Company snapshots display ownership as pie chart
- [ ] Data audit completes quarterly with <2% discrepancies
- [ ] All features work on mobile (iPhone 12, iPad)
- [ ] Performance: <3s page load, <1s chart interaction
- [ ] 100% test coverage for critical paths

---

## Notes for Implementation

- All CSS changes should use existing CSS variables (black + green theme)
- Maintain consistent spacing (8px base unit)
- Use semantic HTML for accessibility
- Store critical data in sessionStorage (not localStorage)
- Add error boundaries for PDF reading failures
- Provide manual verification interface for audit discrepancies
