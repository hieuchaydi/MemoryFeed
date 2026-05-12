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
- Pipeline script: `tools/monetization/run_10usd_pipeline.ps1`
- Leads tracker: `tools/monetization/leads_tracker.csv`
- Leads init script: `tools/monetization/init_leads_from_targets.ps1`
- Next actions script: `tools/monetization/show_next_actions.ps1`
- Lead stage update script: `tools/monetization/update_lead_stage.ps1`
- Continuous loop: `tools/monetization/continuous_until_10usd.ps1`
- Start loop in background: `tools/monetization/start_continuous_10usd.ps1`
- Stop loop: `tools/monetization/stop_continuous_10usd.ps1`

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

Run full pipeline:

```powershell
powershell -ExecutionPolicy Bypass -File tools\monetization\run_10usd_pipeline.ps1 -GoalUsd 10
```

Run continuously in background:

```powershell
powershell -ExecutionPolicy Bypass -File tools\monetization\start_continuous_10usd.ps1 `
  -GoalUsd 10 `
  -IntervalMinutes 15
```

## Done condition

Stop only when `Total >= 10` in status output.
