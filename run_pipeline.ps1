
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -Path $scriptPath
Set-Location -Path ..

. .\.venv\Scripts\Activate.ps1

python scripts\box_operations.py

python scripts\db2_data_upload.py

python scripts\most_sold_products_analysis.py

deactivate

Write-Host "Pipeline execution complete."

