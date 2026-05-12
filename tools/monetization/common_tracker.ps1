Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Convert-ToSafeCsvField {
  param([string]$Value)
  if ($null -eq $Value) { return "" }
  return $Value.Replace("`r", " ").Replace("`n", " ").Replace(",", ";")
}

function Ensure-RevenueTrackerSchema {
  param([string]$TrackerFile)

  $desiredHeader = "timestamp_utc,amount_usd,client,channel,package,transaction_id,proof_ref,validated,note"
  $legacyHeader = "timestamp_utc,amount_usd,client,channel,package,note"

  if (-not (Test-Path -LiteralPath $TrackerFile)) {
    $desiredHeader | Set-Content -LiteralPath $TrackerFile -Encoding UTF8
    return
  }

  $firstLine = ""
  $first = Get-Content -LiteralPath $TrackerFile -TotalCount 1 -ErrorAction SilentlyContinue
  if ($first) { $firstLine = "$first".Trim() }
  if ($firstLine -eq $desiredHeader -or $firstLine -eq "`"$desiredHeader`"") { return }
  if ($firstLine -eq "") {
    $desiredHeader | Set-Content -LiteralPath $TrackerFile -Encoding UTF8
    return
  }

  $rows = @(Import-Csv -LiteralPath $TrackerFile)
  $migrated = @()
  foreach ($row in $rows) {
    $tx = ""
    $proof = ""
    if ($row.PSObject.Properties.Name -contains "transaction_id") { $tx = "$($row.transaction_id)" }
    if ($row.PSObject.Properties.Name -contains "proof_ref") { $proof = "$($row.proof_ref)" }
    $validated = "false"
    if (($tx.Trim() -ne "") -and ($proof.Trim() -ne "")) { $validated = "true" }
    if ($row.PSObject.Properties.Name -contains "validated" -and "$($row.validated)".Trim() -ne "") {
      $validated = "$($row.validated)"
    }

    $note = ""
    if ($row.PSObject.Properties.Name -contains "note") { $note = "$($row.note)" }

    $migrated += [PSCustomObject]@{
      timestamp_utc   = "$($row.timestamp_utc)"
      amount_usd      = "$($row.amount_usd)"
      client          = "$($row.client)"
      channel         = "$($row.channel)"
      package         = "$($row.package)"
      transaction_id  = $tx
      proof_ref       = $proof
      validated       = $validated
      note            = $note
    }
  }

  $desiredHeader | Set-Content -LiteralPath $TrackerFile -Encoding UTF8
  foreach ($row in $migrated) {
    $line = "{0},{1},{2},{3},{4},{5},{6},{7},{8}" -f `
      (Convert-ToSafeCsvField -Value $row.timestamp_utc), `
      (Convert-ToSafeCsvField -Value $row.amount_usd), `
      (Convert-ToSafeCsvField -Value $row.client), `
      (Convert-ToSafeCsvField -Value $row.channel), `
      (Convert-ToSafeCsvField -Value $row.package), `
      (Convert-ToSafeCsvField -Value $row.transaction_id), `
      (Convert-ToSafeCsvField -Value $row.proof_ref), `
      (Convert-ToSafeCsvField -Value $row.validated), `
      (Convert-ToSafeCsvField -Value $row.note)
    Add-Content -LiteralPath $TrackerFile -Value $line
  }
}

function Get-RevenueTotals {
  param([string]$TrackerFile)

  Ensure-RevenueTrackerSchema -TrackerFile $TrackerFile
  $rows = @(Import-Csv -LiteralPath $TrackerFile)

  $count = 0
  $total = 0.0
  $validatedCount = 0
  $validatedTotal = 0.0

  foreach ($row in $rows) {
    $count += 1
    $amount = 0.0
    if ($row.amount_usd -ne $null -and "$($row.amount_usd)".Trim() -ne "") {
      $amount = [double]$row.amount_usd
      $total += $amount
    }

    $hasTx = $row.transaction_id -ne $null -and "$($row.transaction_id)".Trim() -ne ""
    $hasProof = $row.proof_ref -ne $null -and "$($row.proof_ref)".Trim() -ne ""
    $validated = ($row.validated -eq "true") -or ($hasTx -and $hasProof)
    if ($validated) {
      $validatedCount += 1
      $validatedTotal += $amount
    }
  }

  return [PSCustomObject]@{
    Count          = $count
    Total          = [Math]::Round($total, 2)
    ValidatedCount = $validatedCount
    ValidatedTotal = [Math]::Round($validatedTotal, 2)
  }
}

function Ensure-LeadsTrackerSchema {
  param([string]$LeadsFile)

  $desiredHeader = "repo,owner,name,stage,last_action_utc,next_action_utc,offer_price_usd,source_channel,contact_channel,notes"

  if (-not (Test-Path -LiteralPath $LeadsFile)) {
    $desiredHeader | Set-Content -LiteralPath $LeadsFile -Encoding UTF8
    return
  }

  $firstLine = ""
  $first = Get-Content -LiteralPath $LeadsFile -TotalCount 1 -ErrorAction SilentlyContinue
  if ($first) { $firstLine = "$first".Trim('"').Trim() }
  $quotedDesiredHeader = '"repo","owner","name","stage","last_action_utc","next_action_utc","offer_price_usd","source_channel","contact_channel","notes"'
  if ($firstLine -eq $desiredHeader -or $firstLine -eq $quotedDesiredHeader) { return }
  if ($firstLine -eq "") {
    $desiredHeader | Set-Content -LiteralPath $LeadsFile -Encoding UTF8
    return
  }

  $rows = @(Import-Csv -LiteralPath $LeadsFile)
  $migrated = @()
  foreach ($row in $rows) {
    $offer = "10"
    if ($row.PSObject.Properties.Name -contains "offer_price_usd" -and "$($row.offer_price_usd)".Trim() -ne "") {
      $offer = "$($row.offer_price_usd)"
    } elseif ($row.PSObject.Properties.Name -contains "budget_offer_usd" -and "$($row.budget_offer_usd)".Trim() -ne "") {
      $offer = "$($row.budget_offer_usd)"
    }

    $contact = "github"
    if ($row.PSObject.Properties.Name -contains "contact_channel" -and "$($row.contact_channel)".Trim() -ne "") {
      $contact = "$($row.contact_channel)"
    }

    $source = $contact
    if ($row.PSObject.Properties.Name -contains "source_channel" -and "$($row.source_channel)".Trim() -ne "") {
      $source = "$($row.source_channel)"
    }

    $migrated += [PSCustomObject]@{
      repo            = "$($row.repo)"
      owner           = "$($row.owner)"
      name            = "$($row.name)"
      stage           = "$($row.stage)"
      last_action_utc = "$($row.last_action_utc)"
      next_action_utc = "$($row.next_action_utc)"
      offer_price_usd = $offer
      source_channel  = $source
      contact_channel = $contact
      notes           = "$($row.notes)"
    }
  }

  $migrated | Export-Csv -LiteralPath $LeadsFile -NoTypeInformation
}
