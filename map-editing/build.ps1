param(
    [string]$QuakeLivePath = "C:\Program Files (x86)\Steam\steamapps\common\Quake Live",
    [string]$NetRadiantPath = "C:\tools\netradiant-custom"
)

$ErrorActionPreference = "Stop"
$workspace = $PSScriptRoot
$q3map2 = Join-Path $NetRadiantPath "q3map2.exe"
$mbspc = Join-Path $NetRadiantPath "mbspc.exe"
$pak00 = Join-Path $QuakeLivePath "baseq3\pak00.pk3"
$sourceBsp = Join-Path $workspace "src\maps\heroskeep.bsp"
$sourceMap = Join-Path $workspace "src\maps\heroskeep_converted.map"
$map = Join-Path $workspace "build\pk3root\maps\spacekeep.map"
$bsp = Join-Path $workspace "build\pk3root\maps\spacekeep.bsp"
$aas = Join-Path $workspace "build\pk3root\maps\spacekeep.aas"
$packageRoot = Join-Path $workspace "build\package"

foreach ($required in @($q3map2, $mbspc, $pak00)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required file not found: $required"
    }
}

New-Item -ItemType Directory -Force -Path (Split-Path $sourceMap), (Split-Path $map) | Out-Null
if (-not (Test-Path -LiteralPath $sourceMap)) {
    tar -xf $pak00 -C (Join-Path $workspace "src") "maps/heroskeep.bsp"
    if ($LASTEXITCODE -ne 0) { throw "Could not extract stock Hero's Keep BSP" }
    & $q3map2 -game quakelive -fs_basepath $QuakeLivePath -convert -format map $sourceBsp
    if ($LASTEXITCODE -ne 0) { throw "Hero's Keep decompile failed" }
}

python (Join-Path $workspace "build_spacekeep_source.py") $sourceMap $map
if ($LASTEXITCODE -ne 0) { throw "Spacekeep source generation failed" }
python (Join-Path $workspace "verify_spacekeep.py") $map
if ($LASTEXITCODE -ne 0) { throw "Spacekeep source verification failed" }

& $q3map2 -game quakelive -fs_basepath $QuakeLivePath -meta -patchmeta -leaktest $map
if ($LASTEXITCODE -ne 0 -or (Test-Path ([IO.Path]::ChangeExtension($map, ".lin")))) {
    throw "Structural compile failed or leaked"
}
& $q3map2 -game quakelive -fs_basepath $QuakeLivePath -vis -saveprt $map
if ($LASTEXITCODE -ne 0) { throw "Visibility compile failed" }
& $q3map2 -game quakelive -fs_basepath $QuakeLivePath -light -fast -filter -bounce 1 -samples 2 $map
if ($LASTEXITCODE -ne 0) { throw "Lighting compile failed" }
& $mbspc -bsp2aas $bsp -optimize -threads 12
if ($LASTEXITCODE -ne 0) { throw "Bot navigation compile failed" }

New-Item -ItemType Directory -Force -Path `
    (Join-Path $packageRoot "maps"), `
    (Join-Path $packageRoot "scripts"), `
    (Join-Path $packageRoot "levelshots") | Out-Null
Copy-Item -LiteralPath $bsp, $aas -Destination (Join-Path $packageRoot "maps") -Force
Copy-Item -LiteralPath (Join-Path $workspace "src\scripts\spacekeep.arena") `
    -Destination (Join-Path $packageRoot "scripts") -Force
tar -xf $pak00 -C $packageRoot "levelshots/heroskeep.jpg"
if ($LASTEXITCODE -ne 0) { throw "Could not extract levelshot" }
Move-Item -LiteralPath (Join-Path $packageRoot "levelshots\heroskeep.jpg") `
    -Destination (Join-Path $packageRoot "levelshots\spacekeep.jpg") -Force

$zip = Join-Path $workspace "build\spacekeep_test.zip"
$pk3 = Join-Path $workspace "build\spacekeep_test.pk3"
Compress-Archive -Path (Join-Path $packageRoot "*") -DestinationPath $zip -Force
Move-Item -LiteralPath $zip -Destination $pk3 -Force
Write-Host "Built $pk3"
