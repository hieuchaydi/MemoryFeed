# Daily Selling Loop (Khong Dung Lai Truoc Khi Dat Muc Tieu)

Muc tieu ngay: dat them it nhat `$10`.

## Vong lap moi 60 phut

1. Chay `run_10usd_pipeline.ps1` de day outreach.
2. Cap nhat lead stage trong `leads_tracker.csv`.
3. Follow-up cac lead den han.
4. Kiem tra payment moi, ghi vao `revenue_tracker.csv`.
5. Kiem tra lai tong doanh thu.
6. Neu muon chay lien tuc, bat `start_continuous_10usd.ps1`.

## Lenh su dung

Khoi tao lead tracker tu danh sach repo:

```powershell
powershell -ExecutionPolicy Bypass -File tools\monetization\init_leads_from_targets.ps1
```

Xem viec can lam tiep theo:

```powershell
powershell -ExecutionPolicy Bypass -File tools\monetization\show_next_actions.ps1 -Limit 10
```

Cap nhat trang thai lead:

```powershell
powershell -ExecutionPolicy Bypass -File tools\monetization\update_lead_stage.ps1 `
  -Repo "owner/name" `
  -Stage "contacted" `
  -Note "Sent partnership issue"
```

Ghi nhan payment:

```powershell
powershell -ExecutionPolicy Bypass -File tools\monetization\record_payment.ps1 `
  -AmountUsd 5 `
  -Client "owner/name" `
  -Channel "github" `
  -Package "quick-triage" `
  -Note "paid"
```

Kiem tra tong tien:

```powershell
powershell -ExecutionPolicy Bypass -File tools\monetization\revenue_status.ps1 -GoalUsd 10
```

## Dinh nghia stage

- `new`: chua lien he
- `contacted`: da gui offer
- `replied`: da co phan hoi
- `negotiating`: dang chot scope/phi
- `won`: da nhan tien
- `lost`: khong chot duoc

## Dieu kien dung

Chi dung khi status doanh thu bao `GOAL_REACHED` voi muc tieu `$10`.
