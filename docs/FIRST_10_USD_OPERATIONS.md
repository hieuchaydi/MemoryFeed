# First $20 Operations (Execution Mode)

Goal: collect at least `$20` as fast as possible with validated payments.

## Offer setup

Use two fixed offers:

1. `$10` Debug/Triage package
2. `$10` Setup/Integration mini package

Two completed orders = `$20`.

## Revenue tracker files

- Tracker CSV: `tools/monetization/revenue_tracker.csv`
- Add payment script: `tools/monetization/record_payment.ps1`
- Status script: `tools/monetization/revenue_status.ps1`
- Pipeline script: `tools/monetization/run_10usd_pipeline.ps1`
- Leads tracker: `tools/monetization/leads_tracker.csv`
- Leads init script: `tools/monetization/init_leads_from_targets.ps1`
- Next actions script: `tools/monetization/show_next_actions.ps1`
- Lead stage update script: `tools/monetization/update_lead_stage.ps1`
- Add direct lead script: `tools/monetization/add_direct_lead.ps1`
- SLA refresh script: `tools/monetization/apply_lead_sla.ps1`
- Continuous loop: `tools/monetization/continuous_until_10usd.ps1`
- Start loop in background: `tools/monetization/start_continuous_10usd.ps1`
- Stop loop: `tools/monetization/stop_continuous_10usd.ps1`
- Watchdog loop: `tools/monetization/watchdog_10usd.ps1`
- Start watchdog: `tools/monetization/start_watchdog_10usd.ps1`
- Stop watchdog: `tools/monetization/stop_watchdog_10usd.ps1`

## Commands

Add payment:

```powershell
powershell -ExecutionPolicy Bypass -File tools\monetization\record_payment.ps1 `
  -AmountUsd 10 `
  -Client "client-handle" `
  -Channel "facebook" `
  -Package "debug-triage-10usd" `
  -TransactionId "txn-123" `
  -ProofRef "screenshot-or-receipt-link" `
  -Note "paid and delivered"
```

Check status:

```powershell
powershell -ExecutionPolicy Bypass -File tools\monetization\revenue_status.ps1 -GoalUsd 20
```

Run full pipeline:

```powershell
powershell -ExecutionPolicy Bypass -File tools\monetization\run_10usd_pipeline.ps1 -GoalUsd 20
```

Run continuously in background:

```powershell
powershell -ExecutionPolicy Bypass -File tools\monetization\start_continuous_10usd.ps1 `
  -GoalUsd 20 `
  -IntervalMinutes 15
```

Run watchdog in background:

```powershell
powershell -ExecutionPolicy Bypass -File tools\monetization\start_watchdog_10usd.ps1 `
  -GoalUsd 20 `
  -RunnerIntervalMinutes 10 `
  -WatchIntervalSeconds 60
```

## Done condition

Stop only when `Total USD (validated) >= 20` in status output.
