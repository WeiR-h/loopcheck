$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$loopcheckScenes = Get-Content -Raw -Encoding UTF8 (Join-Path $PSScriptRoot '../docs/video/scenes-v052.json') | ConvertFrom-Json
$loopcheckAudioDir = Join-Path $PSScriptRoot '../data/video-v052'
New-Item -ItemType Directory -Path $loopcheckAudioDir -Force | Out-Null
$loopcheckVoice = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $loopcheckVoice.SelectVoice('Microsoft Zira Desktop')
    $loopcheckVoice.Rate = 1
    for ($loopcheckIndex = 0; $loopcheckIndex -lt $loopcheckScenes.Count; $loopcheckIndex++) {
        $loopcheckVoice.SetOutputToWaveFile((Join-Path $loopcheckAudioDir "voice-$loopcheckIndex.wav"))
        $loopcheckVoice.Speak($loopcheckScenes[$loopcheckIndex].narration)
        $loopcheckVoice.SetOutputToNull()
    }
} finally { $loopcheckVoice.Dispose() }
Write-Output "English narration created for $($loopcheckScenes.Count) scenes."
