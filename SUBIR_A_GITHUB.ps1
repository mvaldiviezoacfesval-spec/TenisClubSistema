param(
    [Parameter(Mandatory=$true)]
    [string]$RepoUrl
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".git")) {
    git init
}

if (git remote | Select-String -Quiet "^origin$") {
    git remote set-url origin $RepoUrl
} else {
    git remote add origin $RepoUrl
}

git branch -M main
git push -u origin main

Write-Host ""
Write-Host "Codigo subido a GitHub correctamente."
Write-Host "Ahora crea/sincroniza el Blueprint en Render usando el repositorio:"
Write-Host $RepoUrl
