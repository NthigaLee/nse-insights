# Admin PDF Viewer - Detailed Specification

## Reference Design (from user-provided image)
The reference shows a three-panel layout:
- **Left Sidebar**: Company list filtered by data coverage status (appears on hover >1 sec)
- **Center Panel**: Full-screen PDF viewer with toolbar (prev/next, zoom, download, page counter)
- **Right Panel**: Financial data extracted from PDF (Income Statement, Balance Sheet, etc)

## Implementation Plan

### Phase 1: Layout Structure (This commit)
1. Redesign admin.html with three-panel layout
2. Create hover-reveal sidebar with company list
3. Add PDF viewer placeholder (iframe-based)
4. Add metadata panel structure

### Phase 2: PDF Viewer Functionality (Next commit)
1. Implement PDF.js for advanced PDF reading
2. Add page navigation (prev/next)
3. Add zoom controls
4. Add download button
5. Display page numbers

### Phase 3: Financial Data Extraction (Follow-up)
1. Extract text from PDF using PDF.js
2. Parse for Balance Sheet data
3. Parse for Income Statement data
4. Display in metadata panel

### Phase 4: Data Coverage Audit (Follow-up)
1. Track which PDFs are available per company
2. Show status indicators (✓ complete, ⚠ partial, ✗ missing)
3. Filter companies by coverage status

## Current Implementation (Step-by-step)

### Step 1: Update admin.html structure
- Replace grid layout with three-panel layout
- Add sidebar with hover reveal mechanism
- Add PDF viewer with toolbar
- Add metadata panel

### Step 2: Add admin-specific CSS
- Sidebar styling (width 300px, slide-in on hover)
- PDF viewer styling (responsive, full-width)
- Metadata panel styling
- Toolbar styling (page controls, zoom, etc)

### Step 3: Add basic JavaScript
- Hover timer for sidebar reveal
- Company selection logic
- PDF loading logic (start with iframe)
- Show/hide metadata panel

## HTML Structure

```html
<!-- Three-panel layout -->
<div class="admin-main">
  <!-- Left Sidebar (hover-reveal) -->
  <div class="admin-sidebar">
    <div class="sidebar-header">Companies</div>
    <div class="company-list">
      <div class="company-item">
        <span class="co-status">✓</span>
        <span class="co-name">SCOM</span>
      </div>
      ...
    </div>
  </div>

  <!-- Center Panel (PDF Viewer) -->
  <div class="pdf-viewer">
    <div class="pdf-toolbar">
      <button>← Prev</button>
      <span class="page-counter">Page 1 / 73</span>
      <button>Next →</button>
      <button>🔍+ Zoom</button>
      <button>⬇ Download</button>
    </div>
    <div class="pdf-container">
      <iframe id="pdf-frame" src="..."></iframe>
    </div>
  </div>

  <!-- Right Panel (Metadata) -->
  <div class="metadata-panel">
    <div class="company-info">...</div>
    <div class="financial-statements">...</div>
  </div>
</div>
```

## CSS Breakpoints for Responsive

- **Desktop (>1200px)**: Three-panel visible, sidebar always shown
- **Tablet (768px-1200px)**: Two panels (sidebar + viewer), metadata hidden until tab click
- **Mobile (<768px)**: Full-width PDF, sidebar and metadata as modals

## Next Steps After This Implementation

1. Add PDF.js library for better PDF handling
2. Implement text extraction from PDF
3. Build financial statement parser
4. Connect to data verification workflow
5. Mobile-optimize the PDF viewer

---

## Dependencies
- PDF.js (for full implementation) - currently using iframe as fallback
- NSE data quality JSON for PDF URLs
- Company financial data from data.js

## Testing Checklist
- [ ] Sidebar appears on hover after 1 second
- [ ] Sidebar disappears on mouse out
- [ ] Clicking a company loads its PDF
- [ ] Page navigation works
- [ ] Zoom controls work
- [ ] Download button functions
- [ ] Mobile: sidebarpresents as modal
- [ ] Mobile: metadata as swipeable panel
