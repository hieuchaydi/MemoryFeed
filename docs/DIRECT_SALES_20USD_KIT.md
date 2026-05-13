# Direct Sales $20 Kit (No Freelance Account Needed)

Goal: close 2 real payments x $10 using personal channels (facebook/zalo/linkedin/community).

## Fixed $10 offers

1. Debug/Triage package ($10)
   - Deliverable: diagnosis, root-cause shortlist, fix path, acceptance checklist.
2. Setup/Integration mini package ($10)
   - Deliverable: setup runbook + patch scope + risk notes.

## Public post template

```text
Nhan 2 slot hom nay, moi slot $10, giao nhanh trong ngay:
1) Debug/Triage package
2) Setup/Integration mini package

Ban gui issue/noi dung can xu ly, minh tra ket qua ro rang:
- huong fix cu the
- checklist nghiem thu
- plan patch thuc thi

Slot co han, uu tien ai chot som.
```

## DM template

```text
Minh co 1 slot $10 phu hop nhu cau cua ban.
Neu ban gui task cu the, minh lam ngay va tra:
- diagnosis + fix path (hoac setup runbook)
- checklist xac nhan done
Thoi gian: trong ngay.
```

## Pricing + close template

```text
Scope nay minh chot tron goi $10.
Ban thanh toan truoc, minh giao ban dau trong <X> gio.
Sau khi giao, minh ho tro chinh sua nhe trong cung scope.
```

## FAQ quick answers

- Why $10?
  - Scope nho, de test nhanh, giam rui ro cho ca hai ben.
- What do I receive?
  - Ban giao ro rang: huong xu ly, checklist, va patch scope.
- How fast?
  - Cung ngay cho scope nho.

## Delivery checklist

1. Xac nhan scope 1 cau.
2. Xac nhan gia $10.
3. Nhan thanh toan + transaction id.
4. Giao output dung format.
5. Xin feedback + referral.

## Payment validation rule

Chi tinh doanh thu khi co:
- transaction_id
- proof_ref (receipt link / screenshot reference)

Ghi vao tracker:

```powershell
powershell -ExecutionPolicy Bypass -File tools\monetization\record_payment.ps1 `
  -AmountUsd 10 `
  -Client "client-handle" `
  -Channel "facebook" `
  -Package "debug-triage-10usd" `
  -TransactionId "txn-123" `
  -ProofRef "receipt-link" `
  -Note "slot-1 paid"
```
