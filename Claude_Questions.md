# Blooper5 Issues and Questions

## Completed

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

## MIDI Feature Completeness Audit (2026-01-16)

**Goal**: Ensure every possible MIDI event can be saved in .bloom5 files and has Piano Roll UI representation

### Channel Voice Messages (Per-Note/Per-Channel MIDI Data)

#### ✅ Note On/Off (0x80/0x90)
**Current Status**: PARTIAL
- ✅ Note number (pitch 0-127) - Stored in Note model
- ✅ Note on velocity (0-127) - Stored in Note model
- ❌ Note off velocity (release velocity) - NOT STORED
- ❌ MIDI channel (0-15) - No channel concept in Track model
- **TODO Data Model**:
  - Add `release_velocity: int = 127` to Note model
  - Add `midi_channel: int = 0` to Track model
- **TODO Piano Roll UI**:
  - Velocity editor lane (vertical bars showing velocity per note)
  - Release velocity editor (separate lane or combined)
  - Color-code notes by velocity (darker = softer, brighter = louder)
  - Velocity painting tool (draw velocity curves with mouse)

#### ❌ Polyphonic Aftertouch (0xA0)
**Current Status**: NOT IMPLEMENTED
- **Description**: Per-note pressure after initial strike (0-127)
- **Use Cases**: MPE controllers, expressive playing, per-note vibrato/timbre control
- **TODO Data Model**:
  - Add `AutomationLane` model for time-series data
  - Store per-note aftertouch curves: `List[Tuple[tick, value]]`
  - Or add `aftertouch_curve: Optional[Tuple[AutomationPoint, ...]]` to Note model
- **TODO Piano Roll UI**:
  - Aftertouch automation lane below notes (like DAW automation)
  - Pencil tool to draw aftertouch curves
  - Freehand drawing mode for smooth curves
  - Display as gradient overlay on notes showing pressure changes

#### ❌ Control Change (0xB0) - 128 Controllers
**Current Status**: COMPLETELY MISSING
- **Critical Controllers to Support**:

  **Continuous Controllers (0-31, 64-95):**
  - CC1 (Modulation Wheel) - Vibrato, tremolo, filter modulation
  - CC2 (Breath Controller) - Wind instrument expression
  - CC4 (Foot Controller) - Volume pedal, expression pedal
  - CC7 (Volume) - Currently stored as Track.volume, not as CC automation
  - CC10 (Pan) - Currently stored as Track.pan, not as CC automation
  - CC11 (Expression) - Dynamic expression separate from velocity
  - CC64 (Sustain Pedal) - Hold notes, most common pedal
  - CC65 (Portamento On/Off) - Glide between notes
  - CC66 (Sostenuto Pedal) - Selective sustain
  - CC67 (Soft Pedal) - Reduce velocity
  - CC71 (Filter Resonance) - Synth control
  - CC74 (Filter Cutoff) - Brightness control
  - CC91 (Reverb Send) - Effect send level
  - CC93 (Chorus Send) - Effect send level

  **High-Resolution 14-bit Controllers (paired MSB/LSB):**
  - CC0/32 (Bank Select MSB/LSB) - Select sound banks
  - CC1/33 (Modulation MSB/LSB) - High-res modulation
  - CC7/39 (Volume MSB/LSB) - High-res volume
  - CC10/42 (Pan MSB/LSB) - High-res panning

  **Switch Controllers (0/127 on/off):**
  - CC64-69 (Sustain, Portamento, Sostenuto, Soft, Legato, Hold2)
  - CC80-83 (General Purpose buttons)

  **Data Entry:**
  - CC6/38 (Data Entry MSB/LSB) - For RPN/NRPN editing
  - CC96-97 (Data Increment/Decrement)
  - CC98-101 (NRPN/RPN LSB/MSB) - Registered/Non-registered parameters

  **Mode Messages (120-127):**
  - CC120 (All Sound Off)
  - CC121 (Reset All Controllers)
  - CC123 (All Notes Off)
  - CC124-127 (Omni/Mono/Poly mode)

- **TODO Data Model**:
  ```python
  @dataclass(frozen=True)
  class CCAutomation:
      """CC automation for a track."""
      cc_number: int  # 0-127
      points: Tuple[AutomationPoint, ...]  # Time-series data

  @dataclass(frozen=True)
  class AutomationPoint:
      """Single automation point."""
      tick: int  # Absolute tick position
      value: int  # 0-127 (or 0-16383 for 14-bit)
      curve_type: str = "linear"  # "linear", "stepped", "bezier"

  # Add to Track model:
  cc_automation: Tuple[CCAutomation, ...] = ()
  ```

- **TODO Piano Roll UI**:
  - **Automation Lane System**:
    - Show/hide automation lanes below note grid
    - Lane selector dropdown (select which CC to edit)
    - Multiple lanes visible simultaneously (stacked)
  - **Drawing Tools**:
    - Pencil tool for drawing CC curves
    - Line tool for ramps (fade in/out)
    - Freehand mouse drawing for smooth curves
    - Step sequencer mode for rhythmic modulation
  - **Visual Representation**:
    - Filled area graph (0-127 range)
    - Color-coded by CC type (mod=blue, expression=red, etc.)
    - Grid lines at 25%, 50%, 75% values
    - Snap to grid option for rhythmic CC changes
  - **Editing**:
    - Click-drag to adjust values
    - Multi-select automation points
    - Copy/paste automation curves
    - Reset to default value (64 for center, 0 for off)

#### ❌ Program Change (0xC0)
**Current Status**: NOT IMPLEMENTED
- **Description**: Select instrument/preset (0-127)
- **Use Cases**: Change sounds mid-song, multi-timbral arrangements
- **TODO Data Model**:
  - Add `program_number: int = 0` to Track model
  - Add `ProgramChange` events at specific ticks for mid-song changes
  - Store bank select (CC0/32) + program number together
- **TODO Piano Roll UI**:
  - Track header dropdown for selecting program/preset
  - Timeline markers showing program changes
  - "Insert Program Change" button at playhead position
  - Visual indicator when program changes occur

#### ❌ Channel Pressure/Aftertouch (0xD0)
**Current Status**: NOT IMPLEMENTED
- **Description**: Global pressure for entire channel (not per-note)
- **Difference from Poly Aftertouch**: Applies to all notes, not individual notes
- **TODO Data Model**:
  - Store as CC-like automation: `channel_pressure: Tuple[AutomationPoint, ...]`
  - Track-level pressure curve (not per-note)
- **TODO Piano Roll UI**:
  - Dedicated automation lane labeled "Channel Pressure"
  - Same drawing tools as CC automation
  - Visual feedback showing pressure affecting all active notes

#### ❌ Pitch Bend (0xE0)
**Current Status**: NOT IMPLEMENTED
- **Description**: 14-bit pitch wheel data (-8192 to +8191, center=0)
- **Use Cases**: Vibrato, glissando, pitch slides, guitar bends
- **TODO Data Model**:
  ```python
  @dataclass(frozen=True)
  class PitchBendAutomation:
      points: Tuple[PitchBendPoint, ...]
      range_semitones: int = 2  # Bend range (+/- semitones)

  @dataclass(frozen=True)
  class PitchBendPoint:
      tick: int
      value: int  # -8192 to +8191 (14-bit)
      curve_type: str = "linear"

  # Add to Track model:
  pitch_bend: Optional[PitchBendAutomation] = None
  ```

- **TODO Piano Roll UI**:
  - **Automation Lane**:
    - Centered at 0 (no bend)
    - Range: -2 to +2 semitones by default (configurable)
    - Scale marks at -1, 0, +1 semitones
  - **Drawing Tools**:
    - Smooth curve drawing (important for natural bends)
    - Reset to center (0) button
    - Bend range selector (±1, ±2, ±12 semitones)
  - **Visual Feedback**:
    - Show pitch bend curve overlaid on notes
    - Display actual resulting pitch (e.g., "C4 → C#4")
    - Vibrato presets (sine wave generator)
  - **Editing**:
    - Click-drag to create pitch bends
    - Snap to semitone increments option
    - Copy/paste bend curves between notes

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

#### ❌ Timing Clock (0xF8)
**Current Status**: NOT IMPLEMENTED
- **Description**: 24 clocks per quarter note for sync
- **Use Cases**: Sync with external gear, drum machines, arpeggiators
- **TODO Data Model**: Add MIDI clock send/receive settings to Song
- **TODO UI**: "Sync to MIDI Clock" checkbox in settings

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

#### ❌ Key Signature (0xFF 0x59)
**Current Status**: NOT IMPLEMENTED
- **Description**: Key and scale (e.g., C major, A minor)
- **Use Cases**: Display correct accidentals, scale-aware note snapping
- **TODO Data Model**: Add `key_signature: Tuple[int, int]` to Song/MeasureMetadata
  - First int: -7 to +7 (flats to sharps)
  - Second int: 0=major, 1=minor
- **TODO Piano Roll UI**:
  - Highlight scale notes in piano roll (in-key notes brighter)
  - "Snap to Scale" option when drawing notes
  - Key signature indicator in toolbar

#### ❌ Lyrics (0xFF 0x05)
**Current Status**: NOT IMPLEMENTED
- **TODO**: Add lyrics track/lane for vocal notation

#### ❌ Marker (0xFF 0x06)
**Current Status**: NOT IMPLEMENTED
- **Description**: Named markers at specific times (intro, verse, chorus, etc.)
- **TODO Data Model**: Add `Marker` model with tick position and name
- **TODO UI**: Timeline markers with editable names

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

#### ❌ MIDI Input (Recording)
**Current Status**: NOT IMPLEMENTED (MIDIHandler is stub only)
- **TODO**:
  - Implement MIDIHandler using `rtmidi` library
  - Real-time note recording to Piano Roll
  - CC learning/recording
  - Input quantization
  - Metronome/click track during recording
  - Count-in before recording
  - Overdub vs replace recording modes

#### ❌ MIDI Output (Playback to External Devices)
**Current Status**: NOT IMPLEMENTED
- **TODO**:
  - Send note on/off to external synths
  - Send CC automation to hardware
  - Send pitch bend, aftertouch
  - MIDI clock sync output
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
- **Linear**: Straight line between points
- **Stepped**: No interpolation, jumps instantly
- **Bezier**: Smooth curves with control handles
- **Exponential**: Natural fade curves

#### Velocity Editor Enhancements
**Current**: Velocity stored, but no visual editor
- **TODO**:
  - Velocity lane showing vertical bars per note
  - Color gradient on notes (velocity = brightness)
  - Velocity painting tool (brush over notes to paint velocity)
  - Velocity humanization (randomize slightly for realism)
  - Velocity scaling (scale all selected notes by percentage)
  - Crescendo/diminuendo tool (ramp velocity over selection)

---

### Data Model Changes Summary

**New Models Needed**:
```python
@dataclass(frozen=True)
class AutomationPoint:
    tick: int
    value: int  # or float for normalized 0.0-1.0
    curve_type: str = "linear"

@dataclass(frozen=True)
class CCAutomation:
    cc_number: int  # 0-127
    points: Tuple[AutomationPoint, ...]

@dataclass(frozen=True)
class PitchBendAutomation:
    points: Tuple[AutomationPoint, ...]  # value: -8192 to +8191
    range_semitones: int = 2

@dataclass(frozen=True)
class Marker:
    tick: int
    name: str
    color: Tuple[int, int, int] = (255, 255, 0)

@dataclass(frozen=True)
class MIDILearnMapping:
    cc_number: int
    target_type: str  # "track_volume", "track_pan", "plugin_param", etc.
    target_id: str  # Track name or plugin parameter path
    min_value: float = 0.0
    max_value: float = 1.0
```

**Updates to Existing Models**:
```python
@dataclass(frozen=True)
class Note:
    # Existing fields...
    note: int
    start: float
    duration: float
    velocity: int = 100

    # NEW FIELDS:
    release_velocity: int = 127
    aftertouch_curve: Optional[Tuple[AutomationPoint, ...]] = None

@dataclass(frozen=True)
class Track:
    # Existing fields...
    name: str
    notes: Tuple[Note, ...]
    volume: float
    pan: float

    # NEW FIELDS:
    midi_channel: int = 0  # 0-15
    program_number: int = 0  # 0-127
    bank_msb: int = 0  # CC0
    bank_lsb: int = 0  # CC32
    cc_automation: Tuple[CCAutomation, ...] = ()
    pitch_bend: Optional[PitchBendAutomation] = None
    channel_pressure: Tuple[AutomationPoint, ...] = ()

@dataclass(frozen=True)
class Song:
    # Existing fields...
    name: str
    bpm: float
    tracks: Tuple[Track, ...]

    # NEW FIELDS:
    measure_metadata: Optional[Tuple[MeasureMetadata, ...]] = None  # Already planned
    key_signature: Tuple[int, int] = (0, 0)  # C major default
    markers: Tuple[Marker, ...] = ()
    midi_learn_mappings: Tuple[MIDILearnMapping, ...] = ()
    send_midi_clock: bool = False
    receive_midi_clock: bool = False
```

---

### Implementation Priority

**Phase 1 (Current Plan)**: Per-measure time signature and tempo
**Phase 2 (HIGH)**: Velocity editor + CC automation infrastructure
**Phase 3 (HIGH)**: Pitch bend automation
**Phase 4 (MEDIUM)**: Real-time MIDI input/output
**Phase 5 (MEDIUM)**: MIDI learn and controller mapping
**Phase 6 (LOW)**: MPE support
**Phase 7 (LOW)**: Advanced features (lyrics, markers, SysEx)

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

