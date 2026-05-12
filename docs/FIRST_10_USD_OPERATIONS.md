# First $10 Operations (Execution Mode)

Goal: collect at least `$10` as fast as possible with micro gigs.

## Offer setup

Use two fixed offers:

1. `$5` Quick Triage
2. `$5` Setup Validation

Two completed orders = `$10`.

## Revenue tracker files

- Tracker CSV: `tools/monetization/revenue_tracker.csv`
- Add payment script: `tools/monetization/record_payment.ps1`
- Status script: `tools/monetization/revenue_status.ps1`

## Commands

Add payment:

```powershell
powershell -ExecutionPolicy Bypass -File tools\monetization\record_payment.ps1 `
  -AmountUsd 5 `
  -Client "client-handle" `
  -Channel "github-issue" `
  -Package "quick-triage" `
  -Note "paid and delivered"
```

Check status:

```powershell
powershell -ExecutionPolicy Bypass -File tools\monetization\revenue_status.ps1 -GoalUsd 10
```

## Done condition

Stop only when `Total >= 10` in status output.
