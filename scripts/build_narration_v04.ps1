$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force -Path 'data/video-v04' | Out-Null
Add-Type -AssemblyName System.Speech
$loopNarrator = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $loopNarrator.SelectVoice('Microsoft Zira Desktop')
    $loopScenes = Get-Content -LiteralPath 'docs/video/scenes-v04.json' -Raw | ConvertFrom-Json
    $loopIndex = 0
    foreach ($loopScene in $loopScenes) {
        $loopNarrator.SetOutputToWaveFile((Join-Path (Get-Location).Path ('data/video-v04/voice-' + $loopIndex + '.wav')))
        $loopNarrator.Speak($loopScene.narration)
        $loopNarrator.SetOutputToNull()
        $loopIndex++
    }
} finally { $loopNarrator.Dispose() }
Write-Output 'Narration complete. Install imageio-ffmpeg in the development environment, then run scripts/build_video_v04.py.'

