param([string]$ClionRoot = "$env:LOCALAPPDATA/Programs/CLion")
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$vcpkgRoot = Join-Path $repoRoot 'build/vcpkg'
$installRoot = Join-Path $repoRoot 'build/windows-deps'
$revision = (Get-Content -Raw (Join-Path $repoRoot 'vcpkg.json') | ConvertFrom-Json).'builtin-baseline'
$compilerDir = Join-Path $ClionRoot 'bin/mingw/bin'
if (!(Test-Path (Join-Path $compilerDir 'gcc.exe'))) { throw "CLion MinGW was not found at $compilerDir. Supply -ClionRoot." }
$env:PATH = "$compilerDir;$env:PATH"
$env:VCPKG_DISABLE_METRICS = '1'
if (!(Test-Path $vcpkgRoot)) {
    git clone --no-checkout --depth 1 https://github.com/microsoft/vcpkg.git $vcpkgRoot
    if ($LASTEXITCODE -ne 0) { throw 'vcpkg clone failed' }
}
git -C $vcpkgRoot fetch --depth 1 origin $revision
if ($LASTEXITCODE -ne 0) { throw 'vcpkg revision fetch failed' }
git -C $vcpkgRoot checkout --detach $revision
if ($LASTEXITCODE -ne 0) { throw 'vcpkg revision checkout failed' }
& (Join-Path $vcpkgRoot 'bootstrap-vcpkg.bat') -disableMetrics
if ($LASTEXITCODE -ne 0) { throw 'vcpkg bootstrap failed' }
& (Join-Path $vcpkgRoot 'vcpkg.exe') install --triplet x64-mingw-static --host-triplet x64-mingw-static "--x-manifest-root=$repoRoot" "--x-install-root=$installRoot" --disable-metrics
if ($LASTEXITCODE -ne 0) { throw 'Windows dependency installation failed' }
Write-Output "Windows headers and libraries installed in $installRoot. Reload CMake in CLion."
