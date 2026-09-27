# AutoCaption AI — Premium V14

This build focuses on template fidelity and editor/export consistency.

## What changed

- Full template contract shared by gallery, live editor and FFmpeg renderer.
- Template categories: Built-in, Static Captions, Dynamic Captions, AI / Creator.
- Template search and selected-template indicator.
- 38 creator templates, including glow, word-highlight, glass, editorial and kinetic styles.
- Template-specific caption rhythm (`chunk_words`, max characters and line limits).
- Original Whisper word timestamps are preserved when a word is corrected.
- Editing a caption does not merge neighboring chunks.
- If edited text becomes too long, it is split using that caption's original template rhythm instead of creating one giant sentence.
- Renderer receives the complete selected template object and locks the export to that template.
- Orientation-aware preview/export scaling for portrait, square and landscape videos.
- Safe-area clamping prevents captions from leaving the real video picture area.
- Active-word tracking is a UI state only; no underline is burned into the export.
- Template typography/case/effects are applied in both editor preview and final ASS render.
- Source video is rendered only once, after caption editing is complete.
- File picker uses one explicit click path to avoid the first-selection issue.

## Run on Windows

From the folder containing `app.py`:

```powershell
$env:WHISPER_DEVICE="cpu"
$env:WHISPER_COMPUTE_TYPE="int8"
$env:WHISPER_MODEL="medium"
python app.py
```

Open `http://127.0.0.1:8000`.

If the extracted ZIP has an extra folder level, locate the real application folder with:

```powershell
Get-ChildItem -Recurse -Filter app.py | Select-Object FullName
```

Then `cd` into the directory that contains `app.py`.
\n\nV14 All Templates Fixed build\n- Existing template registry is preserved.\n- Editor keeps the selected template locked during render.\n- Export respects each template's chunk word limit and max line count.\n- Single-line templates remain single-line in export.\n- Glow animation uses persistent blur during export so edited captions do not fall back to plain text.\n- Existing Hinglish word timestamps and editable caption chunks are preserved.\n