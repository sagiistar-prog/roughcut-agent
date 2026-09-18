"""Create original synthetic fixtures, with a review timeline written before every video generation."""
from pathlib import Path
import argparse
import csv
import json
import os
import subprocess
from stage2_generate_timeline import TIMELINE_FIELDS

ROOT = Path(__file__).resolve().parents[1]
SPEECH = [
    'I used to watch every recording twice, then write the start and end times on paper. It took too long to prepare a first cut.',
    'Now I can read the transcript, listen to the selected clip, and change the cut before exporting. The original recording stays unchanged.',
]


def create(directory: Path) -> Path:
    directory = directory.resolve()
    if not directory.is_relative_to(ROOT / 'output'):
        raise ValueError('Use a new directory inside output/')
    directory.mkdir(parents=True, exist_ok=False)
    rows = []
    for index, speech in enumerate(SPEECH):
        wav = directory / f'speech{index + 1}.wav'
        if os.name == 'nt':
            env = os.environ.copy()
            env.update(ROUGHCUT_SPEECH=speech, ROUGHCUT_WAV=str(wav))
            command = "$ErrorActionPreference='Stop'; Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; $voice = $synth.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name.StartsWith('en') } | Select-Object -First 1; if ($voice) { $synth.SelectVoice($voice.VoiceInfo.Name) }; $synth.SetOutputToWaveFile($env:ROUGHCUT_WAV); $synth.Speak($env:ROUGHCUT_SPEECH); $synth.Dispose()"
            subprocess.run(['powershell.exe', '-NoProfile', '-Command', command], env=env, check=True, timeout=60)
        else:
            subprocess.run(['espeak', '-v', 'en-us', '-s', '145', '-w', str(wav), speech], check=True, timeout=60)
        probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(wav)], capture_output=True, text=True, check=True)
        duration = float(json.loads(probe.stdout)['format']['duration'])
        video = directory / f'speech{index + 1}.mp4'
        row = dict(order=index + 1, source_file=video.relative_to(ROOT).as_posix(), start_time=0, end_time=duration,
                   duration_seconds=duration, transcript=speech, role='synthetic', reason='Original TTS fixture', risk_note='Synthetic, not real user media')
        rows.append(row)
        with (directory / 'timeline_review.csv').open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=TIMELINE_FIELDS); writer.writeheader(); writer.writerows(rows)
        color, size, rate = ('0x354b83', '640x360', '24') if index == 0 else ('0x675b87', '360x640', '25')
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-n', '-f', 'lavfi', '-i', f'color=c={color}:s={size}:r={rate}', '-i', str(wav), '-t', str(duration), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(video)], check=True, timeout=120)
    return directory


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, required=True); args = parser.parse_args()
    print(create(args.directory).relative_to(ROOT).as_posix())
