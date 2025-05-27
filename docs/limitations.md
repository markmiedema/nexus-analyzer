# Known Limitations - Nexus Analyzer v0.1.0

## Implemented Features
- ✅ Rolling 12-month lookback calculations
- ✅ Calendar year (previous or current) calculations  
- ✅ Sales threshold detection
- ✅ Transaction count threshold detection
- ✅ Marketplace sales inclusion/exclusion

## Not Yet Implemented

### Lookback Rules
- ❌ `calendar_prev` - Previous calendar year only (FL, MO, NM, RI)
- ❌ `rolling_4q` - Rolling quarters (IL, NY)
- ❌ `accounting_year` - Puerto Rico special case

### Financial Calculations
- ❌ Penalty calculations (all states use 10% placeholder)
- ❌ Interest calculations (simplified to 6% annual)
- ❌ VDA lookback caps
- ❌ State-specific penalty waivers

### State-Specific Rules
- ❌ California district taxes
- ❌ Colorado home-rule jurisdictions
- ❌ Louisiana parish taxes
- ❌ Alaska local taxes (no state sales tax)

### Edge Cases
- ❌ Mid-year threshold changes
- ❌ Retroactive law changes
- ❌ Marketplace facilitator law effective dates
- ❌ State-specific filing frequency rules

### Data Handling
- ❌ Multi-currency transactions
- ❌ Exempt sales tracking
- ❌ Interstate sales allocation
- ❌ Drop-shipment scenarios

## Assumptions Made
1. All sales are taxable unless marked exempt
2. Marketplace sales count toward thresholds unless specifically excluded
3. Negative sales (returns) do not count toward nexus thresholds
4. Transaction counts are whole numbers (no fractional transactions)
5. All dates are in US timezones

## Planned for v0.2.0
- Structured logging with audit trail
- CLI interface
- All remaining lookback rules
- State configuration versioning