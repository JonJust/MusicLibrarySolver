import os, sys
import ffmpeg

def parse_cue(cue_path):
    """Parse a .cue file and return album metadata and track list with details."""
    album_info = {
        "album": None,
        "album_artist": None,
        "tracks": [],  # will be a list of track dicts
        "year": None,
        "genre": None,
        "comment": None,
        "disc_id": None,
    }
    current_file = None  # current audio file path for tracks
    current_track = None
    cue_dir = os.path.dirname(cue_path)

    # Helper to strip quotes from a value string
    def strip_quotes(s):
        s = s.strip()
        if (len(s) >= 2) and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
            s = s[1:-1]
        return s

    with open(cue_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(';'):
                continue  # skip empty lines or comments
            # Split the line into command and rest (at the first whitespace)
            parts = line.split(maxsplit=1)
            cmd = parts[0].upper()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if cmd == "REM":
                # REM lines: format 'REM FIELD value'
                if not arg:
                    continue
                rem_parts = arg.split(maxsplit=1)
                field = rem_parts[0].upper()
                value = rem_parts[1] if len(rem_parts) > 1 else ""
                value = strip_quotes(value)
                # Store known REM fields in album_info
                if field in ("DATE", "YEAR"):
                    album_info["year"] = value
                elif field == "GENRE":
                    album_info["genre"] = value
                elif field == "COMMENT":
                    album_info["comment"] = value
                elif field == "DISCID":
                    album_info["disc_id"] = value
                else:
                    # Unhandled REM fields can be stored in a generic dict if needed
                    # (Not specifically used further in this script)
                    pass

            elif cmd == "PERFORMER":
                value = strip_quotes(arg)
                if current_track is None:
                    # Album artist (global performer before any track)
                    album_info["album_artist"] = value
                else:
                    # Track-specific artist/performer
                    current_track["artist"] = value

            elif cmd == "TITLE":
                value = strip_quotes(arg)
                if current_track is None:
                    # Album title (global title)
                    album_info["album"] = value
                else:
                    # Track title
                    current_track["title"] = value

            elif cmd == "FILE":
                # Parse the file path and type
                # Format: FILE "filename.ext" WAVE
                file_part = arg
                file_type = None
                if file_part.startswith('"'):
                    # Find the matching closing quote for the filename
                    end_quote = file_part.find('"', 1)
                    file_path_str = file_part[1:end_quote] if end_quote != -1 else file_part[1:]
                    rest = file_part[end_quote + 1:].strip() if end_quote != -1 else ""
                    if rest:
                        file_type = rest.split()[0]  # e.g., WAVE, MP3, etc.
                else:
                    # No quotes, filename is first token
                    tokens = file_part.split(maxsplit=1)
                    file_path_str = tokens[0]
                    file_type = tokens[1] if len(tokens) > 1 else None
                # Construct full path relative to cue file directory
                audio_path = os.path.join(cue_dir, file_path_str)
                current_file = audio_path
                # Check file existence
                if not os.path.isfile(current_file):
                    raise FileNotFoundError(f"Audio file not found: {current_file}")
                # We do not reset track numbering here; tracks may continue numbering across files.
                # (If the cue is multi-file and numbering restarts, handle naming conflicts later if needed.)

            elif cmd == "TRACK":
                # Finish the previous track entry (if any)
                # (In this implementation, tracks are appended when their data is complete, 
                # but we could finalize previous track here if needed.)
                # Start a new track
                track_parts = arg.split()
                if len(track_parts) >= 2:
                    track_num_str = track_parts[0]
                    track_type = track_parts[1]  # e.g., AUDIO
                else:
                    track_num_str = track_parts[0] if track_parts else arg
                    track_type = None
                # Normalize track number (keep as string and int)
                try:
                    track_num = int(track_num_str)
                except ValueError:
                    # If track number is not purely numeric (unlikely in standard cues), ignore non-numeric part
                    track_num = int(''.join(filter(str.isdigit, track_num_str)) or 0)
                # Create new track dict
                current_track = {
                    "number": track_num,
                    "title": None,
                    "artist": None,
                    "index0": None,
                    "index1": None,
                    "pregap": None,
                    "postgap": None,
                    "file": current_file
                }
                album_info["tracks"].append(current_track)

            elif cmd == "INDEX":
                if current_track is None:
                    continue  # index outside of track (should not happen in well-formed cue)
                index_parts = arg.split()
                if len(index_parts) != 2:
                    continue
                index_num = index_parts[0]
                time_str = index_parts[1]
                # Convert mm:ss:ff to seconds (float) or store frames
                try:
                    mm, ss, ff = map(int, time_str.split(':'))
                except ValueError:
                    # Malformed time, skip
                    continue
                frame_number = mm * 60 * 75 + ss * 75 + ff  # total frames from start of file
                seconds = frame_number / 75.0
                if index_num == "01":
                    current_track["index1"] = seconds
                elif index_num == "00":
                    current_track["index0"] = seconds
                # (Ignoring any index >01, as those are sub-indexes not used for splitting)

            elif cmd == "PREGAP":
                # PREGAP specified (mm:ss:ff of silence before this track's INDEX 01)
                if current_track is not None:
                    try:
                        mm, ss, ff = map(int, arg.split(':'))
                    except ValueError:
                        continue
                    frames = mm * 60 * 75 + ss * 75 + ff
                    current_track["pregap"] = frames / 75.0
            elif cmd == "POSTGAP":
                if current_track is not None:
                    try:
                        mm, ss, ff = map(int, arg.split(':'))
                    except ValueError:
                        continue
                    frames = mm * 60 * 75 + ss * 75 + ff
                    current_track["postgap"] = frames / 75.0
            # (Other commands like CATALOG, ISRC, FLAGS, etc. can be handled if needed, but are not used for extraction.)
    return album_info


def extract_tracks(album_info, output_dir):
    """Use ffmpeg to extract tracks according to the parsed album_info."""
    tracks = album_info["tracks"]
    if not tracks:
        return  # No tracks to process

    os.makedirs(output_dir, exist_ok=True)
    total_tracks = len(tracks)

    # Determine audio properties (sample rate, channels) for silence generation
    # We'll use ffprobe via ffmpeg.probe to get stream info from the first track's file.
    sample_rate = None
    channels = None
    first_file = tracks[0]["file"]
    try:
        # Use ffmpeg.probe to get audio stream info (requires ffprobe/ffmpeg installed)
        probe = ffmpeg.probe(first_file)
        for stream in probe.get('streams', []):
            if stream.get('codec_type') == 'audio':
                sample_rate = int(stream.get('sample_rate', 0)) or None
                channels = int(stream.get('channels', 0)) or None
                break
    except ffmpeg.Error:
        pass  # If probing fails, we'll fall back to defaults

    # Default to common values if not found
    if sample_rate is None:
        sample_rate = 44100
    if channels is None:
        channels = 2

    for track in tracks:
        track_num = track["number"]
        title = track.get("title") or f"Track {track_num}"
        artist = track.get("artist") or album_info.get("album_artist") or ""
        album = album_info.get("album") or ""
        album_artist = album_info.get("album_artist") or artist  # if album artist missing, use track artist
        year = album_info.get("year") or ""
        genre = album_info.get("genre") or ""
        comment = album_info.get("comment") or ""
        disc_id = album_info.get("disc_id") or ""

        # Calculate start and end times for the track's audio segment within its file
        start_time = track["index1"] if track["index1"] is not None else 0.0
        # Determine end time by looking at the next track in the same file
        # By default, end at next track's index1 or end-of-file for last track.
        end_time = None
        # Find the next track that uses the same file (tracks are in order, so next in list might be same file or different file)
        for nxt in album_info["tracks"]:
            if nxt is track:
                continue
            if nxt["file"] == track["file"] and nxt["number"] > track_num:
                # next track on the same file (assuming track numbers increase)
                # Use its index0 if available (pregap in file) or index1 otherwise.
                if nxt["index0"] is not None:
                    end_time = nxt["index0"]
                else:
                    end_time = nxt["index1"]
                break
        # If not found, this track is last in its file; we'll use file's duration as end.
        if end_time is None:
            # Probe duration of the file or leave None to let ffmpeg read till end
            try:
                if "duration" in locals():  # use cached probe if available (not implemented here for each track)
                    file_duration = float(probe.get('format', {}).get('duration'))
                else:
                    file_duration = float(ffmpeg.probe(track["file"])['format']['duration'])
            except Exception:
                file_duration = None
            end_time = file_duration

        # Compute duration for ffmpeg (if end_time known)
        duration = None
        if end_time is not None:
            # Ensure end_time is after start_time
            if end_time < start_time:
                end_time = start_time
            duration = end_time - start_time

        # Determine pregap and postgap durations to add (if any)
        pregap_duration = 0.0
        postgap_duration = 0.0
        # If explicit PREGAP specified, use it (not stored in file)&#8203;:contentReference[oaicite:12]{index=12}
        if track.get("pregap") is not None:
            pregap_duration = track["pregap"]
        elif track.get("index0") is not None and track["index0"] < start_time:
            # If an index0 exists, treat the gap between index0 and index1 as pregap
            pregap_duration = start_time - track["index0"]
        # If explicit POSTGAP specified, use it (not in file)
        if track.get("postgap") is not None:
            postgap_duration = track["postgap"]
        # (No need to handle index of next track as postgap here, since we assigned end_time accordingly)

        # Prepare ffmpeg input streams
        main_audio = ffmpeg.input(track["file"], ss=start_time, t=duration)  # main audio segment
        audio_stream = main_audio.audio  # get the audio stream (for files that might have video, though unlikely here)
        segments = []
        # Pregap: generate silence segment if needed
        if pregap_duration > 0:
            silence = ffmpeg.input(
                'anullsrc=r={}:cl={}'.format(sample_rate, "stereo" if channels == 2 else f"{channels}c"),
                format='lavfi',
                duration=pregap_duration
            )
            segments.append(silence.audio)
        # Main audio segment
        segments.append(audio_stream)
        # Postgap: generate silence segment if needed
        if postgap_duration > 0:
            silence2 = ffmpeg.input(
                'anullsrc=r={}:cl={}'.format(sample_rate, "stereo" if channels == 2 else f"{channels}c"),
                format='lavfi',
                duration=postgap_duration
            )
            segments.append(silence2.audio)

        # Concatenate segments if there are multiple, otherwise use single segment
        if len(segments) > 1:
            # Use ffmpeg concat filter to join audio segments&#8203;:contentReference[oaicite:13]{index=13}
            concat_audio = ffmpeg.concat(*segments, v=0, a=1)
            output_stream = concat_audio
        else:
            output_stream = segments[0]

        # Construct output file name
        # Zero-pad track number to at least 2 digits (if total tracks >= 10)
        num_width = 2 if total_tracks >= 10 else 1
        track_num_str = str(track_num).zfill(num_width)
        # Make a safe file name component from title
        safe_title = "".join(c if c.isalnum() or c in " _-." else "_" for c in title)
        ext = os.path.splitext(track["file"])[1]  # use original file extension (e.g., .flac, .wav)
        output_filename = f"{track_num_str} - {safe_title}{ext}"
        output_path = os.path.join(output_dir, output_filename)

        # Prepare metadata for ffmpeg output
        metadata_kwargs = {
            # Using ffmpeg metadata keys (lowercase)&#8203;:contentReference[oaicite:14]{index=14}&#8203;:contentReference[oaicite:15]{index=15}
            "metadata": f"title={title}",
            "metadata:g:0": f"artist={artist}",
            "metadata:g:1": f"album={album}",
            "metadata:g:2": f"album_artist={album_artist}",
            "metadata:g:3": f"track={track_num}/{total_tracks}",
        }
        if year := album_info.get("year"):
            metadata_kwargs["metadata:g:4"] = f"date={year}"
        if genre := album_info.get("genre"):
            metadata_kwargs["metadata:g:5"] = f"genre={genre}"
        # Combine comment and DiscID if both present
        comment_text = comment
        if disc_id:
            # If there's an existing comment, append DiscID; otherwise, use DiscID as comment
            if comment_text:
                comment_text = f"{comment_text} | DiscID: {disc_id}"
            else:
                comment_text = f"DiscID: {disc_id}"
        if comment_text:
            metadata_kwargs["metadata:g:6"] = f"comment={comment_text}"

        # Set up the output with metadata and run ffmpeg
        try:
            (output_stream
             .output(output_path, **metadata_kwargs)
             .overwrite_output()  # overwrite if file exists
             .run(quiet=True)  # run FFmpeg
             )
        except ffmpeg.Error as e:
            raise RuntimeError(f"FFmpeg failed to process track {track_num}: {e}")
    # End of track loop

def main():
    if len(sys.argv) < 2:
        print("Usage: python cue_split.py <path/to/file.cue>")
        sys.exit(1)
    cue_file = sys.argv[1]
    album_data = parse_cue(cue_file)
    out_dir = os.path.splitext(os.path.basename(cue_file))[0]  # directory named after cue file (without extension)
    extract_tracks(album_data, out_dir)
    print(f"Tracks extracted to folder: {out_dir}")

if __name__ == "__main__":
    main()
