param(
  [ValidateSet('server','model','runtime')]
  [string]$Source = 'server',
  [string]$Output = "lmstudio-$Source.jsonl"
)

$lms = Get-Command lms -ErrorAction SilentlyContinue
if (-not $lms) {
  Write-Error "lms CLI not found in PATH."
  exit 1
}

switch ($Source) {
  'server' {
    lms log stream --source server --json | Tee-Object -FilePath $Output -Append
  }
  'model' {
    lms log stream --source model --filter input,output --json | Tee-Object -FilePath $Output -Append
  }
  'runtime' {
    $help = lms log stream --help 2>$null | Out-String
    if ($help -notmatch 'runtime') {
      Write-Error "This lms CLI does not list runtime as a log source."
      exit 2
    }
    lms log stream --source runtime --json | Tee-Object -FilePath $Output -Append
  }
}
