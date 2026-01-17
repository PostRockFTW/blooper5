# Blooper5 Issues and Questions

## Completed

### Architecture Refactoring (2026-01-16)
✅ **FIXED**: Consolidated audio/ and audio_engine/ folders - merged into single audio/ folder
✅ **FIXED**: Deleted unused audio/mixer.py placeholder
✅ **FIXED**: Moved PianoRoll, DrumRoll, PluginRack from views/ to widgets/
✅ **FIXED**: Views now contain only full-page contexts (DAWView, LandingPage, SettingsPage)
✅ **FIXED**: Widgets now contain reusable components (PianoRoll, NoteDrawToolbar, MixerStrip, etc.)
✅ **FIXED**: Extracted note drawing toolbar from Piano Roll into separate NoteDrawToolbar widget
✅ **FIXED**: Toolbar now includes quantization, snap toggle, and other features from Blooper4

## Future Enhancements

### Audio Pre-buffering
Consider adding hybrid pre-buffering system:
- Pre-render notes before playback starts to prevent glitches
- Buffer ahead during playback for smooth real-time playback
- Adjustable buffer size for performance tuning

### Piano Roll Grid Zoom
Implement Blooper4's hierarchical zoom system:
- Zoom levels: Measure only → Measure+Beat → Beat+Triplets → Subdivisions
- Dynamic grid line visibility based on zoom level
- Mouse wheel zoom controls
- Grid snapping respects current zoom level

### Note Drawing Enhancements
- Add N-Tuplet support (custom tuplet divisions)
- Add bar length controls (+/- buttons)
- Visual feedback for current quantization setting
- Keyboard shortcuts for tool switching
