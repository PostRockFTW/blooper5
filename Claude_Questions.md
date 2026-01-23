# Blooper5 Issues and Questions

## Completed

### 2026-01-22: Voice Manager System - Fixed MIDI Keyboard Retriggering
✅ **IMPLEMENTED**: Pre-rendering voice manager eliminates keyboard note retriggering artifacts

**Problem:**
- MIDI keyboard notes were retriggering hundreds of times per second
- Every audio frame re-created the synth, causing phase discontinuities and audio glitches
- Notes had audible clicks and pops during sustained playback
- Real-time performance was degraded by constant synth recreation

**Solution - Voice Manager with Pre-rendering:**
- New `audio/voice_manager.py` module with `LiveVoice` and `VoiceManager` classes
- Pre-renders notes in 2-second chunks when note_on is received
- Streams audio from pre-rendered buffers (no phase resets)
- Automatically extends buffers if notes held longer than 2 seconds
- Applies smooth exponential release envelope on note_off
- Full polyphony support with per-note state tracking

**Technical Implementation:**
- **Symbol Translation**: Maps symbolic waveform notation to proper names
  - "~" → "SINE", "[]" → "SQUARE", "|/" → "SAW", "/\\" → "TRIANGLE"
  - `translate_waveform_params()` handles conversion transparently
- **Buffer Management**:
  - Initial 2-second pre-render on note_on
  - 1-second chunk extensions for held notes
  - Memory-efficient truncation after release
- **Release Envelope**:
  - 300ms exponential decay by default (configurable)
  - Applies to remaining buffer only (doesn't extend duration)
  - Quick 50ms release on rapid retriggering
- **Integration**:
  - `DAWView._process_midi_event()` uses voice manager for note_on/note_off
  - `DAWView._handle_audio_clock()` calls `voice_manager.render_frame()`
  - Transport events (stop, loop, SPP jump) call `voice_manager.clear_all()`
  - Mixer controls (mute/solo/volume/pan) integrated in render pipeline

**Files Modified:**
- `audio/voice_manager.py` - NEW - Core voice management system
- `ui/views/DAWView.py` - Integrated voice manager for live MIDI rendering
- `core/models.py` - Added waveform symbol support validation
- `midi/handler.py` - Enhanced MIDI event handling
- `audio/dsp.py` - DSP utility updates
- `audio/scheduler.py` - Scheduler integration
- `main.py` - Application initialization updates
- `plugins/registry.py` - Plugin registry enhancements
- `requirements.txt` - Updated dependencies (python-rtmidi, mido)
- `ui/views/LandingPage.py` - UI improvements
- `ui/widgets/PianoRoll.py` - Piano roll enhancements
- `.claude/settings.local.json` - Local configuration updates

**Impact:**
- ✅ Notes sustain smoothly without clicks or pops
- ✅ Full polyphony with independent voice state
- ✅ Velocity-sensitive playback
- ✅ Clean release envelopes (no abrupt cutoffs)
- ✅ Efficient CPU usage (pre-rendering vs. real-time synthesis)
- ✅ Mixer controls work seamlessly with live input
- ✅ Proper cleanup on transport events

**Performance:**
- 2-second initial buffer ≈ 88,200 samples @ 44.1kHz (178KB per voice)
- Automatic extension in 1-second chunks (44KB) for held notes
- No CPU spikes during note sustain (only during initial note_on)
- Memory released immediately after note completion

### 2026-01-21: Real-Time MIDI Input with Channel-Based Routing
✅ **IMPLEMENTED**: Live MIDI input from MPK25 controller
- **MIDI Handler Enhancements**: Added note event queue (1000 event capacity) for incoming MIDI messages
  - Enhanced `_midi_input_callback()` to parse note on/off, CC, and aftertouch events
  - Added `get_note_events()` method to retrieve queued events (thread-safe)
  - Added `input_opened` and `output_opened` properties for status checking
- **Track Model Updates**: Added MIDI input routing fields
  - `receive_midi_input: bool` - Enable MIDI input on specific tracks
  - `midi_note_min: int` - Minimum note number to accept (0-127)
  - `midi_note_max: int` - Maximum note number to accept (0-127)
  - Full serialization support in .bloom5 files
- **Live Note Triggering**: Real-time audio synthesis from MIDI input
  - `active_live_notes` dictionary tracks currently playing notes
  - `_process_midi_event()` method handles channel-based routing with note range filtering
  - Audio callback processes MIDI events and renders live notes every frame
  - Mixer integration: mute/solo/volume/pan work with live input in real-time
- **MPK25 Configuration**: Generic preset analysis
  - All pads on MIDI Channel 1, notes 36-83 (48 pads across 4 banks)
  - Channel aftertouch supported and detected
  - Note range filtering separates keyboard from pads on same MIDI channel
- **Test Project**: `test_midi_input.bloom5` with 3 configured tracks
  - Track 0: Keyboard High (Ch 1, notes 84-127) - Melodic synth (sine waves)
  - Track 1: Pads (Ch 1, notes 36-83) - Percussive synth (saw + square)
  - Track 2: Keyboard Low (Ch 1, notes 0-35) - Bass synth (dual saw)

Files modified:
- `midi/handler.py` - Note event queue, MIDI parsing, event retrieval
- `core/models.py` - Track MIDI input fields (receive_midi_input, note range)
- `ui/views/DAWView.py` - Live note triggering, MIDI event routing

Files created:
- `test_midi_input.bloom5` - Pre-configured test project
- `create_midi_input_test.py` - Test project generator script
- `MIDI_INPUT_TESTING.md` - Complete testing guide

**Key Features**:
- ✅ Channel-based routing (each track listens to specific MIDI channel)
- ✅ Note range filtering (separate keyboard from pads on same channel)
- ✅ Real-time synthesis (zero-latency note triggering)
- ✅ Polyphony (multiple simultaneous notes)
- ✅ Velocity sensitivity (soft/loud hits sound different)
- ✅ Aftertouch detection (currently logged, parameter modulation TODO)
- ✅ Mixer integration (mute/solo/volume/pan work with live input)

**Bugs Fixed**:
1. Audio buffer bug - Output was being zeroed after mixing live notes
2. Waveform names - Test project used symbols instead of valid names ("SAW", "SINE", "SQUARE")
3. MIDI port conflicts - Properly handles exclusive port access

**Future Enhancements**:
- Aftertouch → synth parameter modulation (filter cutoff, vibrato, etc.)
- CC controllers → synth parameter mapping
- MIDI input device selection in UI (currently hardcoded to "Akai MPK25 0")
- MIDI learn for parameter assignment
- Recording live MIDI input to Piano Roll

### 2026-01-20: Loop Functionality Fixes
✅ **FIXED**: Loop markers now work from initial position
- **Root Cause**: Playback logic checked `song.loop_end_tick` directly, which is `None` for new projects
- **Visual vs Playback Mismatch**: Loop markers displayed at song boundaries, but playback saw `None` and never looped
- **Solution**: Handle `None` gracefully by defaulting to `song.length_ticks` in playback worker
- **Implementation**: `ui/views/DAWView.py:1634` - Added `loop_end_tick` effective value calculation

✅ **FIXED**: Note edits now reflected during loop playback
- **Root Cause**: `current_song_id` not updated when loop settings changed, causing save validation to fail
- **Impact**: After toggling loop or dragging markers, note edits were blocked with "Skipping save" message
- **Solution**: Update `current_song_id` when creating new song objects in loop-related callbacks
- **Implementation**:
  - `ui/views/DAWView.py:1451` - Update song ID in `_on_loop_toggle()`
  - `ui/views/DAWView.py:1380` - Update song ID in `_on_loop_markers_changed()`

Files modified:
- `ui/views/DAWView.py` - Loop playback logic, song ID tracking

**Result**:
- Looping works immediately on new projects without dragging markers
- Live note editing during playback updates audio on next loop iteration
- No more cross-project note pollution warnings during normal editing

### 2026-01-20: UI Toolbar Improvements & Bar Editing
- **Note Toolbar Compaction**: Reduced height from 85px to 70px by adding WindowPadding override
- **Bar Edit Toolbar**: New inline toolbar for bar/measure operations (Clear, Remove, Copy, Paste, Add Before/After)
  - Compact 40px height (single row of buttons)
  - Context-aware button states (enabled only when bar selected)
  - Proper selection mode toggle (waits for user selection, clears on disable)
- **Mixer Splitter**: Added adjustable splitter between main content and mixer panel
- **Combined Layout**: Total toolbar height 110px when both toolbars visible (was 125px)

Files modified:
- `ui/widgets/NoteDrawToolbar.py` - Height reduction to 70px
- `ui/widgets/BarEditToolbar.py` - NEW file, bar editing operations
- `ui/views/DAWView.py` - Mixer splitter integration, toolbar layout
- `core/commands.py` - Bar operation commands (Clear, Copy, Paste, etc.)
- `core/models.py` - Bar editing support

### Architecture Refactoring (2026-01-16)
✅ **FIXED**: Consolidated audio/ and audio_engine/ folders - merged into single audio/ folder
✅ **FIXED**: Deleted unused audio/mixer.py placeholder
✅ **FIXED**: Moved PianoRoll, DrumRoll, PluginRack from views/ to widgets/
✅ **FIXED**: Views now contain only full-page contexts (DAWView, LandingPage, SettingsPage)
✅ **FIXED**: Widgets now contain reusable components (PianoRoll, NoteDrawToolbar, MixerStrip, etc.)
✅ **FIXED**: Extracted note drawing toolbar from Piano Roll into separate NoteDrawToolbar widget
✅ **FIXED**: Toolbar now includes quantization, snap toggle, and other features from Blooper4

### Time-Signature-Aware Grid & Tempo Changes (2026-01-17)
✅ **IMPLEMENTED**: Per-measure time signature support
- MeasureMetadata model for storing per-measure tempo and time signature
- Denominator-aware grid visibility (9/8 grids stay visible longer than 4/4)
- Backward compatible with global time signatures
- Full .bloom5 serialization support
- MIDI-compatible design (maps to SetTempo/TimeSignature meta events)

✅ **IMPLEMENTED**: Per-measure tempo changes
- NoteScheduler.get_bpm_at_tick() for tempo-aware scheduling
- Real-time BPM display updates during playback
- Tick-based playhead positioning (no visual jumps at tempo changes)
- Elapsed time tracking for accurate time display
- Test track: 3/4@60bpm → 4/4@120bpm → 9/8@240bpm

Files modified:
- `core/models.py` - MeasureMetadata class, Song.measure_metadata field
- `core/test_data.py` - Test track generator (NEW)
- `audio/scheduler.py` - Tempo-aware scheduling
- `ui/widgets/PianoRoll.py` - Grid rendering, set_playhead_tick()
- `ui/views/DAWView.py` - Tempo tracking, BPM display updates

### Unsaved Changes Protection (2026-01-17)
✅ **IMPLEMENTED**: Unsaved changes warnings when loading projects
- Dialog prompts appear when loading project with unsaved changes
- Three options: Save, Don't Save, Cancel
- Applies to landing page "Load Project" button
- Applies to clicking recent projects
- Save As dialog integration for untitled projects
- Prevents data loss by protecting all load operations

Files modified:
- `main.py` - Added unsaved checks to on_open_project(), dialog handlers

### PianoRoll Multi-Measure Editing (2026-01-18)
✅ **FIXED**: PianoRoll only editable in first measure
- Root cause: `song_length_ticks` hardcoded to 1920 ticks (1 bar) at initialization
- Grid lines, note rendering, and interactions were all bounded by this hardcoded value
- Solution: Update `song_length_ticks = song.length_ticks` when loading tracks
- Now properly supports multi-measure editing, bar addition, and project loading

Files modified:
- `ui/widgets/PianoRoll.py:300-301` - Added song_length_ticks update in load_track_notes()

Impact:
- ✅ Grid lines render for all measures
- ✅ Notes visible in all measures
- ✅ Can draw notes in any measure
- ✅ Add Bar After/Before creates editable bars
- ✅ Multi-measure projects load correctly

## Future Enhancements

### Audio Pre-buffering '''todo when we start testing fx'''
Consider adding hybrid pre-buffering system:
- Pre-render notes before playback starts to prevent glitches
- Buffer ahead during playback for smooth real-time playback
- Adjustable buffer size for performance tuning

### Piano Roll Grid Zoom '''good to go'''
Implement Blooper4's hierarchical zoom system:
- Zoom levels: Measure only → Measure+Beat → Beat+Triplets → Subdivisions
- Dynamic grid line visibility based on zoom level
- Mouse wheel zoom controls (currently work?)
- Grid snapping respects current zoom level

### 9/8 Time Signature Grid Display '''todo'''
The 9/8 time signature grid rendering needs visual refinement:
- Visual display has issues (specifics TBD)
- Grid lines use denominator-aware scaling (working)
- May need adjustment to grid spacing calculations or visual appearance

### Note Drawing Enhancements
- Add N-Tuplet support (custom tuplet divisions)
- Add bar length controls (+/- buttons) '''this should be it's own toolbar for bar mods like time signature changes'''
- Visual feedback for current quantization setting
- Keyboard shortcuts for tool switching
'''Also you need to add radio button for all the standard tuplets that were in blooper4.'''

---

## MIDI Feature Completeness Audit (2026-01-20 UPDATE)

**Status Summary:**
- ✅ **Data Model**: COMPLETE - All MIDI fields/classes implemented and serialized
- ⚠️ **UI Layer**: PARTIAL - Velocity controls only, no automation lanes
- ❌ **MIDI I/O**: NOT IMPLEMENTED - Real-time input/output are stubs

**Goal**: Ensure UI and I/O features catch up with the complete data model

### Channel Voice Messages (Per-Note/Per-Channel MIDI Data)

#### ✅ Note On/Off (0x80/0x90)
**Data Model**: ✅ COMPLETE
- ✅ Note number (pitch 0-127) - `Note.note` (core/models.py:310)
- ✅ Note on velocity (0-127) - `Note.velocity` (core/models.py:313)
- ✅ Note off velocity (release velocity) - `Note.release_velocity` (core/models.py:315)
- ✅ MIDI channel (0-15) - `Track.midi_channel` (core/models.py:434)
- ✅ Full serialization to .bloom5 files
- ✅ Validation (0-127 range checks)

**UI Implementation**: ⚠️ PARTIAL
- ✅ Velocity toolbar slider (applies to new notes globally) (ui/widgets/NoteDrawToolbar.py:106-118)
- ✅ Release velocity toolbar slider (ui/widgets/NoteDrawToolbar.py:119-127)
- ✅ Visual velocity bars on notes (left=on velocity, right=off velocity) (ui/widgets/PianoRoll.py:790-820)
- ❌ No per-note velocity editing lane
- ❌ No velocity painting tool
- ❌ No velocity color coding by brightness

**MIDI I/O**: ⚠️ PARTIAL
- ✅ Import/export note on velocity
- ✅ Real-time MIDI input (live playback, velocity-sensitive) - **NEW 2026-01-21**
- ❌ Release velocity not exported to MIDI files
- ❌ MIDI input recording to Piano Roll not implemented

#### ⚠️ Polyphonic Aftertouch (0xA0)
**Data Model**: ✅ COMPLETE
- ✅ `Note.aftertouch_curve` field (core/models.py:316)
- ✅ Stores per-note aftertouch as `Tuple[AutomationPoint, ...]`
- ✅ AutomationPoint supports linear/stepped/bezier interpolation (core/models.py:14-50)
- ✅ Full serialization to .bloom5 files

**UI Implementation**: ❌ NOT IMPLEMENTED
- ❌ No aftertouch automation lane rendering
- ❌ No pencil tool to draw aftertouch curves
- ❌ No freehand drawing mode for smooth curves
- ❌ No visual overlay on notes showing pressure changes

**MIDI I/O**: ❌ NOT IMPLEMENTED
- ❌ Polyphonic aftertouch not imported from MIDI
- ❌ Polyphonic aftertouch not exported to MIDI

#### ⚠️ Control Change (0xB0) - 128 Controllers
**Data Model**: ✅ COMPLETE
- ✅ `AutomationPoint` class (core/models.py:14-50)
  - tick: Absolute tick position
  - value: Normalized 0.0-1.0
  - curve_type: "linear", "stepped", or "bezier"
- ✅ `CCAutomation` class (core/models.py:52-132)
  - cc_number: 0-127
  - points: Tuple of AutomationPoint objects
  - display_name: Human-readable label
  - get_value_at_tick() method for interpolation
- ✅ `Track.cc_automation` field (core/models.py:438)
  - Stores multiple CC lanes per track
  - Full serialization to .bloom5 files

**Critical Controllers Supported** (data model ready, UI needed):
- CC1 (Modulation Wheel) - Vibrato, tremolo, filter modulation
- CC2 (Breath Controller) - Wind instrument expression
- CC4 (Foot Controller) - Volume pedal, expression pedal
- CC7 (Volume) - Track.volume exists but no CC automation curve
- CC10 (Pan) - Track.pan exists but no CC automation curve
- CC11 (Expression) - Dynamic expression separate from velocity
- CC64 (Sustain Pedal) - Hold notes, most common pedal
- CC65-69 (Portamento, Sostenuto, Soft, Legato, Hold2)
- CC71 (Filter Resonance) - Synth control
- CC74 (Filter Cutoff) - Brightness control
- CC91 (Reverb Send) - Effect send level
- CC93 (Chorus Send) - Effect send level
- All 128 controllers supported via generic automation system

**UI Implementation**: ❌ NOT IMPLEMENTED
- ❌ No automation lane rendering system
- ❌ No CC selector dropdown
- ❌ No drawing tools (pencil/line/freehand)
- ❌ No visualization of CC curves
- ❌ No filled area graphs
- ❌ No multi-lane display

**MIDI I/O**: ⚠️ PARTIAL
- ✅ CC message detection from MIDI input (logged) - **NEW 2026-01-21**
- ❌ CC automation not imported from MIDI files
- ❌ CC automation not exported to MIDI files
- ❌ CC messages not routed to synth parameters (TODO: MIDI learn system)

#### ⚠️ Program Change (0xC0)
**Data Model**: ✅ COMPLETE
- ✅ `Track.program_number` field (core/models.py:435)
  - MIDI program/patch number (0-127)
- ✅ `Track.bank_msb` field (core/models.py:436)
  - Bank Select MSB (CC0)
- ✅ `Track.bank_lsb` field (core/models.py:437)
  - Bank Select LSB (CC32)
- ✅ Full serialization to .bloom5 files

**UI Implementation**: ❌ NOT IMPLEMENTED
- ❌ No track header dropdown for selecting program/preset
- ❌ No timeline markers showing program changes
- ❌ No "Insert Program Change" button
- ❌ No visual indicator when program changes occur
- ❌ No support for mid-song program changes (only initial program stored)

**MIDI I/O**: ❌ NOT IMPLEMENTED
- ❌ Program change not exported to MIDI files
- ❌ Bank select not exported to MIDI files

#### ⚠️ Channel Pressure/Aftertouch (0xD0)
**Data Model**: ✅ COMPLETE
- ✅ `Track.channel_pressure` field (core/models.py:440)
  - Stores as `Tuple[AutomationPoint, ...]`
  - Track-level pressure curve (applies to all notes, not per-note)
- ✅ Full serialization to .bloom5 files

**UI Implementation**: ❌ NOT IMPLEMENTED
- ❌ No dedicated automation lane for channel pressure
- ❌ No drawing tools for pressure curves
- ❌ No visual feedback showing pressure affecting notes

**MIDI I/O**: ⚠️ PARTIAL
- ✅ Channel aftertouch detection from MIDI input (logged) - **NEW 2026-01-21**
- ❌ Channel pressure not imported from MIDI files
- ❌ Channel pressure not exported to MIDI files
- ❌ Aftertouch not routed to synth parameters (TODO: modulate filter, vibrato, etc.)

#### ⚠️ Pitch Bend (0xE0)
**Data Model**: ✅ COMPLETE
- ✅ `PitchBendAutomation` class (core/models.py:135-213)
  - points: Tuple of AutomationPoint objects (value range: -1.0 to +1.0)
  - range_semitones: Pitch bend range in semitones (default 2)
  - get_value_at_tick() method returns 14-bit value (-8192 to +8191)
- ✅ `Track.pitch_bend` field (core/models.py:439)
  - Optional[PitchBendAutomation]
- ✅ Full serialization to .bloom5 files
- ✅ Linear and stepped interpolation support

**UI Implementation**: ❌ NOT IMPLEMENTED
- ❌ No automation lane for pitch bend
- ❌ No drawing tools for bend curves
- ❌ No bend range selector (±1, ±2, ±12 semitones)
- ❌ No visual feedback showing pitch bend on notes
- ❌ No vibrato preset generator
- ❌ No reset to center (0) button

**MIDI I/O**: ❌ NOT IMPLEMENTED
- ❌ Pitch bend not imported from MIDI files
- ❌ Pitch bend not exported to MIDI files

---

### System Common Messages (Song-Level Events)

#### ❌ Song Position Pointer (0xF2)
**Current Status**: NOT IMPLEMENTED
- **Description**: Jump to specific position in song (14-bit MIDI beats)
- **Use Cases**: Sync with external sequencers, loop points
- **TODO Data Model**: Store loop markers and sync points in Song model
- **TODO UI**: Add loop region markers in timeline

#### ❌ Song Select (0xF3)
**Current Status**: NOT IMPLEMENTED
- **Description**: Select which song to play (0-127)
- **Use Cases**: Live performance setlists
- **TODO**: Out of scope (single-project DAW)

#### ❌ Tune Request (0xF6)
**Current Status**: NOT IMPLEMENTED
- **Use Cases**: Analog synth tuning
- **TODO**: Low priority (digital-only DAW)

---

### System Real-Time Messages (Transport Control)

#### ⚠️ Timing Clock (0xF8)
**Data Model**: ✅ COMPLETE
- ✅ `Song.send_midi_clock` field (core/models.py:570)
- ✅ `Song.receive_midi_clock` field (core/models.py:571)
- ✅ Full serialization to .bloom5 files

**UI Implementation**: ❌ NOT IMPLEMENTED
- ❌ No "Sync to MIDI Clock" checkbox in settings
- ❌ No MIDI clock indicator

**MIDI I/O**: ❌ NOT IMPLEMENTED
- ❌ No MIDI clock transmission (24 clocks per quarter note)
- ❌ No MIDI clock reception for sync

#### ❌ Start/Stop/Continue (0xFA, 0xFC, 0xFB)
**Current Status**: PARTIAL - Internal playback only, no MIDI messages
- **Current**: DAWView has play/pause buttons
- **TODO**: Send MIDI Start/Stop/Continue messages when transport changes
- **TODO**: Receive external transport control

---

### Meta Events (MIDI File Format - For Future Import/Export)

#### ✅ Tempo Changes (0xFF 0x51)
**Current Status**: PLANNED (in current plan document)
- Will be stored in `MeasureMetadata.bpm`
- Maps to MIDI SetTempo meta event

#### ✅ Time Signature (0xFF 0x58)
**Current Status**: PLANNED (in current plan document)
- Will be stored in `MeasureMetadata.time_signature`
- Maps to MIDI TimeSignature meta event

#### ⚠️ Key Signature (0xFF 0x59)
**Data Model**: ✅ COMPLETE
- ✅ `Song.key_signature` field (core/models.py:568)
  - Tuple[int, int]: (sharps/flats [-7 to +7], major/minor [0=major, 1=minor])
- ✅ Full serialization to .bloom5 files

**UI Implementation**: ❌ NOT IMPLEMENTED
- ❌ No key signature indicator in piano roll
- ❌ No scale note highlighting (in-key notes brighter)
- ❌ No "Snap to Scale" option when drawing notes

**MIDI I/O**: ❌ NOT IMPLEMENTED
- ❌ Key signature not exported to MIDI files

#### ❌ Lyrics (0xFF 0x05)
**Current Status**: NOT IMPLEMENTED
- **TODO**: Add lyrics track/lane for vocal notation

#### ⚠️ Marker (0xFF 0x06)
**Data Model**: ✅ COMPLETE
- ✅ `Marker` class (core/models.py:216-250)
  - tick: Absolute tick position
  - name: Marker name/label
  - color: RGB color tuple
- ✅ `Song.markers` field (core/models.py:569)
  - Stores tuple of Marker objects
- ✅ Full serialization to .bloom5 files

**UI Implementation**: ❌ NOT IMPLEMENTED
- ❌ No timeline markers display
- ❌ No marker creation/editing UI
- ❌ No marker labels in timeline

**MIDI I/O**: ❌ NOT IMPLEMENTED
- ❌ Markers not exported to MIDI files

#### ❌ Cue Point (0xFF 0x07)
**Current Status**: NOT IMPLEMENTED
- **Use Cases**: Live performance cues, rehearsal marks
- **TODO**: Add cue point system to timeline

#### ❌ Text Events (0xFF 0x01)
**Current Status**: NOT IMPLEMENTED
- **Use Cases**: Comments, annotations, production notes
- **TODO**: Add text annotation system

---

### MPE (MIDI Polyphonic Expression)

#### ❌ MPE Support
**Current Status**: NOT IMPLEMENTED
- **Description**: Use multiple MIDI channels for per-note expression
- **Per-Note Data**: Pitch bend, CC74 (timbre), channel pressure
- **Use Cases**: Expressive controllers (ROLI Seaboard, Linnstrument, Haken Continuum)
- **TODO Data Model**:
  - Designate MPE zone (master channel + member channels)
  - Store per-note pitch bend, timbre, pressure
  - Link Note objects to MPE channel assignments
- **TODO Piano Roll UI**:
  - MPE mode toggle
  - Per-note expression visualization
  - Timbre slider per note
  - Pressure sensitivity display

---

### Real-Time MIDI Input/Output

#### ⚠️ MIDI Input (Live Performance & Recording)
**Current Status**: PARTIAL - Live playback implemented, recording TODO
- **✅ IMPLEMENTED (2026-01-21)**:
  - MIDIHandler using `rtmidi` library (midi/handler.py)
  - Real-time note input with channel-based routing
  - Thread-safe note event queue (1000 event capacity)
  - Note on/off parsing and routing
  - Aftertouch detection (channel aftertouch)
  - CC message detection
  - Live audio synthesis from MIDI input
  - Note range filtering (separate keyboard from pads)
  - Polyphonic input (multiple simultaneous notes)
  - Mixer integration (mute/solo/volume/pan)
- **❌ TODO**:
  - Record MIDI input to Piano Roll
  - Input quantization during recording
  - CC learning/recording to automation lanes
  - Metronome/click track during recording
  - Count-in before recording
  - Overdub vs replace recording modes
  - MIDI input device selection in UI (currently hardcoded to "Akai MPK25 0")

**Implementation Details**:
- MIDI callback runs in separate thread (rtmidi thread)
- Events queued via `note_event_queue` (non-blocking)
- Audio callback retrieves events via `get_note_events()`
- Routing via `_process_midi_event()` based on track configuration
- Active notes tracked in `active_live_notes` dictionary
- Audio generated per-frame using track's synth parameters

#### ⚠️ MIDI Output (Playback to External Devices)
**Current Status**: PARTIAL - SPP sync implemented, note output TODO
- **✅ IMPLEMENTED (2026-01-20)**:
  - MIDI SPP (Song Position Pointer) sending on loop jumps
  - MIDI Start/Stop/Continue messages
  - Thread-safe output handling
- **❌ TODO**:
  - Send note on/off to external synths
  - Send CC automation to hardware
  - Send pitch bend, aftertouch
  - MIDI clock sync output (24 clocks per quarter note)
  - Latency compensation

#### ❌ MIDI Learn
**Current Status**: NOT IMPLEMENTED
- **TODO**:
  - Right-click any parameter → "MIDI Learn"
  - Assign CC to plugin parameters
  - Assign CC to mixer controls (volume, pan, mute, solo)
  - Visual feedback showing learned mappings
  - Save mappings in .bloom5 file

---

### Piano Roll UI Enhancements for MIDI Data

#### Automation Lane System (NEW FEATURE)
**Priority**: HIGH - Needed for CC, pitch bend, aftertouch
- **Layout**:
  - Note grid at top (current piano roll)
  - Automation lanes below (collapsible/expandable)
  - Lane height adjustable (drag divider)
  - Multiple lanes shown simultaneously
- **Lane Types**:
  - Velocity (vertical bars per note)
  - Release Velocity
  - CC lanes (one per CC number)
  - Pitch Bend
  - Channel Pressure
  - Polyphonic Aftertouch (per-note)
  - Tempo curve (global)
- **Controls**:
  - "+" button to add lane
  - Dropdown to select CC/parameter
  - Solo/mute per lane
  - Lock editing per lane
  - Clear all automation button

#### Drawing Tools for Automation
**Priority**: HIGH
- **Pencil Tool**: Click to add points, drag to adjust
- **Line Tool**: Click-drag to create ramps (fade in/out)
- **Freehand Tool**: Mouse painting for smooth curves
- **Eraser Tool**: Remove automation points
- **Selection Tool**: Select/move/copy multiple points

#### Curve Types
**Already Supported in Data Model** (core/models.py:14-50):
- **Linear**: ✅ Straight line between points
- **Stepped**: ✅ No interpolation, jumps instantly
- **Bezier**: ✅ Smooth curves with control handles (not yet implemented in UI)

**TODO - Add to Data Model**:
- **Exponential**: Natural fade curves (for future implementation)

#### Velocity Editor Enhancements
**Current**: Velocity stored and visualized on notes, but no dedicated editor lane
- **TODO**:
  - Velocity lane showing vertical bars per note
  - Color gradient on notes (velocity = brightness)
  - Velocity painting tool (brush over notes to paint velocity)
  - Velocity humanization (randomize slightly for realism)
  - Velocity scaling (scale all selected notes by percentage)
  - Crescendo/diminuendo tool (ramp velocity over selection)

---

### Data Model Implementation Status

**✅ COMPLETE - All models implemented in core/models.py:**

```python
# Already implemented (core/models.py:14-50)
@dataclass(frozen=True)
class AutomationPoint:
    tick: int
    value: float  # Normalized 0.0-1.0 for CC, -1.0 to 1.0 for pitch bend
    curve_type: str = "linear"  # "linear", "stepped", "bezier"

# Already implemented (core/models.py:52-132)
@dataclass(frozen=True)
class CCAutomation:
    cc_number: int  # 0-127
    points: Tuple[AutomationPoint, ...]
    display_name: str = ""

    def get_value_at_tick(self, tick: int) -> float:
        """Get interpolated automation value at a specific tick."""

# Already implemented (core/models.py:135-213)
@dataclass(frozen=True)
class PitchBendAutomation:
    points: Tuple[AutomationPoint, ...]  # value: -1.0 to +1.0
    range_semitones: int = 2

    def get_value_at_tick(self, tick: int) -> int:
        """Get interpolated pitch bend value (-8192 to +8191)."""

# Already implemented (core/models.py:216-250)
@dataclass(frozen=True)
class Marker:
    tick: int
    name: str
    color: Tuple[int, int, int] = (255, 255, 0)

# NOT YET IMPLEMENTED (planned for MIDI learn feature)
@dataclass(frozen=True)
class MIDILearnMapping:
    cc_number: int
    target_type: str  # "track_volume", "track_pan", "plugin_param", etc.
    target_id: str  # Track name or plugin parameter path
    min_value: float = 0.0
    max_value: float = 1.0
```

**✅ Note Model (core/models.py:295-359) - ALL MIDI FIELDS IMPLEMENTED:**
```python
@dataclass(frozen=True)
class Note:
    note: int  # MIDI note number 0-127
    start: float  # Start time in beats
    duration: float  # Duration in beats
    velocity: int = 100  # Note-on velocity 1-127
    selected: bool = False  # UI selection state
    release_velocity: int = 64  # ✅ Note-off velocity 0-127
    aftertouch_curve: Optional[Tuple[AutomationPoint, ...]] = None  # ✅ Polyphonic aftertouch
```

**✅ Track Model (core/models.py:361-540) - ALL MIDI FIELDS IMPLEMENTED:**
```python
@dataclass(frozen=True)
class Track:
    # ... existing fields (name, mode, source, effects, etc.)

    # ✅ MIDI compliance fields (all implemented):
    midi_channel: int = 0  # 0-15 (displayed as 1-16 in UI)
    program_number: int = 0  # 0-127 (MIDI program/patch number)
    bank_msb: int = 0  # CC0 (bank select MSB)
    bank_lsb: int = 0  # CC32 (bank select LSB)
    cc_automation: Tuple[CCAutomation, ...] = ()  # CC automation lanes
    pitch_bend: Optional[PitchBendAutomation] = None  # Pitch bend automation
    channel_pressure: Tuple[AutomationPoint, ...] = ()  # Channel aftertouch
```

**✅ Song Model (core/models.py:544-645) - ALL MIDI FIELDS IMPLEMENTED:**
```python
@dataclass(frozen=True)
class Song:
    # ... existing fields (name, bpm, time_signature, tracks, etc.)

    # ✅ MIDI compliance fields (all implemented):
    measure_metadata: Optional[Tuple[MeasureMetadata, ...]] = None  # ✅ Already implemented
    key_signature: Tuple[int, int] = (0, 0)  # ✅ (sharps/flats, major/minor)
    markers: Tuple[Marker, ...] = ()  # ✅ Timeline markers
    send_midi_clock: bool = False  # ✅ Send MIDI clock to external devices
    receive_midi_clock: bool = False  # ✅ Sync to external MIDI clock
```

**Summary:**
- ✅ All automation classes implemented with full interpolation support
- ✅ All Note MIDI fields implemented (release velocity, aftertouch)
- ✅ All Track MIDI fields implemented (channel, program, CC, pitch bend, pressure)
- ✅ All Song MIDI fields implemented (key signature, markers, MIDI clock)
- ✅ Full .bloom5 serialization working for all fields
- ❌ MIDILearnMapping not yet implemented (planned for future)
- ❌ UI for automation lanes not implemented
- ❌ MIDI I/O not implemented (real-time input/output are stubs)

---

### UI Implementation Roadmap

**Phase 1: Velocity Editor (NEXT)**
**Priority**: HIGH - Data exists but no per-note editing
- Add velocity lane below piano roll
- Implement velocity painting tool
- Add color coding by velocity
- Add crescendo/diminuendo tool

**Phase 2: Automation Lane Infrastructure (HIGH)**
**Priority**: HIGH - Needed for CC, pitch bend, aftertouch
- Implement lane rendering system
- Add lane selector dropdown
- Implement drawing tools (pencil, line, freehand, eraser)
- Support multiple visible lanes

**Phase 3: CC Automation UI (HIGH)**
**Priority**: HIGH - Data model complete, UI missing
- Add CC lane display
- Implement CC curve editing
- Add preset CC templates (modulation, expression, etc.)

**Phase 4: Pitch Bend UI (MEDIUM)**
**Priority**: MEDIUM - Data model complete, UI missing
- Add pitch bend lane
- Implement bend curve drawing
- Add bend range selector
- Add vibrato generator

**Phase 5: MIDI I/O (MEDIUM)**
**Priority**: MEDIUM - Critical for real-time performance
- Implement real-time MIDI input (rtmidi)
- Add MIDI recording
- Add MIDI output to external devices
- Export all automation to MIDI files

**Phase 6: Advanced Features (LOW)**
**Priority**: LOW - Nice to have
- Aftertouch editing UI
- Channel pressure UI
- Key signature display
- Marker timeline
- MIDI learn system
- MPE support

---

### File Format Compatibility

**Storage Strategy**:
- All MIDI data serializes to .bloom5 via Song.to_dict()
- MessagePack handles nested structures automatically
- Optional fields default gracefully for backward compatibility
- When MIDI export is added, all data maps cleanly to MIDI file format

**Round-Trip Compatibility**:
✅ Note on/off → MIDI NoteOn/NoteOff messages
✅ Velocity → MIDI velocity byte
✅ CC automation → MIDI CC messages at each tick
✅ Pitch bend → MIDI PitchBend messages (14-bit)
✅ Program change → MIDI ProgramChange messages
✅ Tempo/time sig → MIDI meta events (already planned)
✅ Markers → MIDI marker meta events

