# Bao Cao Chi Tiet: Cach Dat Muc Tieu $15, Nhan Tien, Rut Tien

Ngay cap nhat: 2026-05-12
Repo: https://github.com/hieuchaydi/MemoryFeed
Nhanh dang trien khai: `codex/memoryfeed-revenue-kit`

## 1) Viec da lam de tao co hoi kiem tien

Da trien khai bo monetization trong repo:

- README bo sung khu "Work With MemoryFeed" + lien ket tai lieu doanh thu
- Bat Sponsor entry: `.github/FUNDING.yml`
- Issue template nhan viec tra phi:
  - `.github/ISSUE_TEMPLATE/paid-integration-request.yml`
  - `.github/ISSUE_TEMPLATE/micro-gig-order.yml`
- Issue draft chao ban dich vu:
  - `.github/issues/paid-integration-slots-this-week.md`
- Tai lieu ban hang va chot don:
  - `docs/REVENUE_PLAYBOOK.md`
  - `docs/FIRST_15_USD_PLAN.md`
  - `docs/OUTREACH_TEMPLATES.md`
- Cong cu outbound:
  - `tools/monetization/post_partnership_issues.ps1`
  - `tools/monetization/generate_outreach_pack.ps1`
  - `tools/monetization/outreach_pack.md`
  - `tools/monetization/target_repos.txt` (16 target)

Commit lien quan:

- `e1d2b2f` Add monetization toolkit
- `d2da02a` Expand monetization flow for first $15
- `b518137` Expand monetization targets to 16 repos

## 2) Cach lay duoc tien ($15 dau tien)

Muc tieu: ban 3 micro gig x $5 = $15.

Goi ban nhanh:

1. `$5` Quick triage
2. `$5` Setup validation
3. `$5` Docs cleanup

Quy trinh chot tien:

1. Dang bai "Paid Integration Slots (This Week)".
2. Day nguoi mua vao issue template `$5 Micro Gig Order`.
3. Xac nhan scope ngan, deadline, tieu chi nghiem thu.
4. Nhan thanh toan theo kenh da thong nhat.
5. Giao hang (patch/commit/runbook) trong 1-3 gio.
6. Xin comment xac nhan da nhan hang + da thanh toan.

Bang doi soat doanh thu (dien khi co giao dich):

- Slot #1: [ ] da ban - So tien: ___ - Ma giao dich: ___
- Slot #2: [ ] da ban - So tien: ___ - Ma giao dich: ___
- Slot #3: [ ] da ban - So tien: ___ - Ma giao dich: ___
- Tong thu: ___ USD (muc tieu 15 USD)

## 3) Cach rut duoc tien (chi tiet)

### A. Neu nhan tien qua GitHub Sponsors

Tai lieu chinh thuc:

- https://docs.github.com/en/sponsors/receiving-sponsorships-through-github-sponsors/managing-your-payouts-from-github-sponsors
- https://docs.github.com/en/sponsors/receiving-sponsorships-through-github-sponsors/using-a-fiscal-host-to-receive-github-sponsors-payouts

Buoc rut tien:

1. Vao `Your sponsors` -> `Dashboard` -> `Payouts`.
2. Kiem tra `Payout overview` (last payout, next estimated payout).
3. Chon `Edit your bank information` de cap nhat thong tin ngan hang (neu dung Stripe Connect).
4. Tai `Payout receipts`, export phieu chi de doi soat.
5. Khi payout da ve tai khoan ngan hang, doi chieu so tien sau phi.

Ghi chu:

- Neu dung fiscal host thi thay doi thong tin payout thong qua support/fiscal host.
- Co the can KYC/thu tuc xac minh danh tinh truoc khi nhan/rut tien.

### B. Neu nhan tien qua kenh ngoai (vi du: PayPal/chuyen khoan)

1. Chot kenh thanh toan truoc khi lam viec.
2. Gui thong tin nhan tien + noi dung don hang.
3. Nhan anh/chung tu xac nhan chuyen tien.
4. Kiem tra tien ve vi/tai khoan.
5. Rut ve ngan hang noi dia (neu can), luu lai ma giao dich va phi.

## 4) Tieu chi xem la hoan thanh muc tieu

Duoc xem la hoan thanh khi dat dong thoi:

1. Tong tien nhan >= 15 USD.
2. Co it nhat 3 giao dich (hoac it hon neu 1 giao dich >= 15 USD).
3. Co bang chung giao dich (receipt/transaction id).
4. Da doi soat tien ve tai khoan rut cuoi cung.

## 5) Trang thai hien tai

- Bo may kiem tien da san sang va da push GitHub.
- Chua co giao dich thanh toan duoc ghi nhan trong repo o thoi diem cap nhat nay.
