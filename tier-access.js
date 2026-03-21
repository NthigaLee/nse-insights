/**
 * NSE Insights - Tier-Based Access Control System
 * Manages feature access and data filtering based on user tier
 * Tiers: free, trader, professional
 * Password: Ntigz
 */

// ========================
// TIER FEATURE DEFINITIONS
// ========================

const TIER_FEATURES = {
    free: {
        name: 'Free',
        maxCompanies: 20,
        availableYears: [2024, 2025],
        canViewHistoricalData: false,
        canViewValuation: false,
        canExportData: false,
        canAccessAdmin: false,
        canViewSectors: true,
        chartUpdateFrequency: 3600000, // 1 hour
        description: 'Dashboard view only - real-time prices'
    },
    trader: {
        name: 'Trader',
        maxCompanies: 60,
        availableYears: [2020, 2021, 2022, 2023, 2024, 2025],
        canViewHistoricalData: true,
        canViewValuation: true,
        canExportData: true,
        canAccessAdmin: false,
        canViewSectors: true,
        chartUpdateFrequency: 300000, // 5 minutes
        description: 'Full dashboard with historical data & exports'
    },
    professional: {
        name: 'Professional',
        maxCompanies: 72,
        availableYears: [2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
        canViewHistoricalData: true,
        canViewValuation: true,
        canExportData: true,
        canAccessAdmin: true,
        canViewSectors: true,
        chartUpdateFrequency: 60000, // 1 minute
        canViewAdvancedMetrics: true,
        canCreateWatchlists: true,
        description: 'Everything including admin console & advanced metrics'
    }
};

// ========================
// TIER ACCESS CONTROL CLASS
// ========================

class TierAccessControl {
    constructor(userTier = 'free') {
        this.userTier = userTier;
        this.features = TIER_FEATURES[userTier];
        this.selectedCompanies = [];
        this.selectedYears = [];

        // Store in sessionStorage for persistence across pages
        sessionStorage.setItem('userTier', userTier);

        // Log tier initialization
        console.log(`NSE Insights Tier Access initialized: ${userTier.toUpperCase()}`);
    }

    /**
     * Determine if user can access a specific company
     * @param {string} company - Company name/ticker
     * @param {array} selectedCompanies - Currently selected companies
     * @returns {boolean}
     */
    canAccessCompany(company, selectedCompanies = []) {
        if (selectedCompanies.length >= this.features.maxCompanies) {
            return selectedCompanies.includes(company);
        }
        return true;
    }

    /**
     * Determine if user can access a specific year
     * @param {number} year - Year (e.g., 2023, 2024)
     * @returns {boolean}
     */
    canAccessYear(year) {
        return this.features.availableYears.includes(parseInt(year));
    }

    /**
     * Get list of companies user can access
     * @param {array} allCompanies - All available companies
     * @returns {array} Filtered list of accessible companies
     */
    getAccessibleCompanies(allCompanies) {
        return allCompanies.slice(0, this.features.maxCompanies);
    }

    /**
     * Get list of years user can access
     * @param {array} allYears - All available years
     * @returns {array} Filtered list of accessible years
     */
    getAccessibleYears(allYears) {
        return allYears.filter(y => this.features.availableYears.includes(y));
    }

    /**
     * Check if user can view historical data
     * @returns {boolean}
     */
    canViewHistoricalData() {
        return this.features.canViewHistoricalData;
    }

    /**
     * Check if user can view valuation estimates
     * @returns {boolean}
     */
    canViewValuation() {
        return this.features.canViewValuation;
    }

    /**
     * Check if user can export data
     * @returns {boolean}
     */
    canExportData() {
        return this.features.canExportData;
    }

    /**
     * Check if user can access admin console
     * @returns {boolean}
     */
    canAccessAdmin() {
        return this.features.canAccessAdmin;
    }

    /**
     * Check if user can view sector analysis
     * @returns {boolean}
     */
    canViewSectors() {
        return this.features.canViewSectors;
    }

    /**
     * Check if user can view advanced metrics
     * @returns {boolean}
     */
    canViewAdvancedMetrics() {
        return this.features.canViewAdvancedMetrics || false;
    }

    /**
     * Check if user can create watchlists
     * @returns {boolean}
     */
    canCreateWatchlists() {
        return this.features.canCreateWatchlists || false;
    }

    /**
     * Get chart update frequency in milliseconds
     * @returns {number}
     */
    getChartUpdateFrequency() {
        return this.features.chartUpdateFrequency;
    }

    /**
     * Get tier information
     * @returns {object} Tier features object
     */
    getTierInfo() {
        return this.features;
    }

    /**
     * Get maximum number of companies for this tier
     * @returns {number}
     */
    getMaxCompanies() {
        return this.features.maxCompanies;
    }

    /**
     * Get available years for this tier
     * @returns {array}
     */
    getAvailableYears() {
        return this.features.availableYears;
    }

    /**
     * Check if tier is professional
     * @returns {boolean}
     */
    isProfessional() {
        return this.userTier === 'professional';
    }

    /**
     * Check if tier is trader or above
     * @returns {boolean}
     */
    isTrader() {
        return this.userTier === 'trader' || this.userTier === 'professional';
    }

    /**
     * Filter data based on tier restrictions
     * @param {array} data - Data to filter
     * @param {string} field - Field to check (e.g., 'ticker', 'year')
     * @returns {array} Filtered data
     */
    filterDataByTier(data, field = 'ticker') {
        if (!Array.isArray(data)) return data;

        if (field === 'ticker') {
            return data.filter(item => this.canAccessCompany(item.ticker || item.name));
        } else if (field === 'year') {
            return data.filter(item => this.canAccessYear(item.year));
        }

        return data;
    }

    /**
     * Apply data limits based on tier
     * @param {array} data - Data to limit
     * @returns {array} Limited data
     */
    applyDataLimits(data) {
        return data.slice(0, this.features.maxCompanies);
    }

    /**
     * Get display message for tier restrictions
     * @returns {string}
     */
    getRestrictionMessage() {
        return `Your ${this.features.name} tier allows viewing up to ${this.features.maxCompanies} companies`;
    }
}

// ========================
// GLOBAL INSTANCE
// ========================

let tierAccess = new TierAccessControl('free');

/**
 * Initialize or switch user tier
 * @param {string} tier - Tier name ('free', 'trader', 'professional')
 * @param {string} password - Password for tier upgrade (required for non-free)
 * @returns {boolean} Success status
 */
function setUserTier(tier, password = null) {
    const validTiers = ['free', 'trader', 'professional'];

    if (!validTiers.includes(tier)) {
        console.error(`Invalid tier: ${tier}`);
        return false;
    }

    // Require password for paid tiers
    if (tier !== 'free' && password !== 'Ntigz') {
        console.error('Invalid password for tier upgrade');
        return false;
    }

    tierAccess = new TierAccessControl(tier);
    sessionStorage.setItem('userTier', tier);

    // Dispatch event for UI updates
    window.dispatchEvent(new CustomEvent('tierChanged', { detail: { tier } }));

    console.log(`Tier upgraded to: ${tier.toUpperCase()}`);
    return true;
}

/**
 * Get current user tier
 * @returns {string}
 */
function getCurrentTier() {
    return tierAccess.userTier;
}

/**
 * Get current tier access instance
 * @returns {TierAccessControl}
 */
function getTierAccess() {
    return tierAccess;
}
