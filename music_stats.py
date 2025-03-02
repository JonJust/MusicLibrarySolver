#!/usr/bin/env python3

import argparse
import ffmpeg
from mutagen import File
import re
from dataclasses import dataclass, field
import zlib
from typing import List

@dataclass
class Track:
    file_path: str
    artist: str
    album_artist: str
    album: str
    file_size: int
    crc: int

def compute_crc32(file_path):
    """
    Compute the 32-bit CRC of a file.

    :param file_path: Path to the file.
    :return: 32-bit CRC as an integer, or None if computation fails.
    """
    buf_size = 65536  # Read in chunks of 64KB
    crc = 0
    try:
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(buf_size)
                if not data:
                    break
                crc = zlib.crc32(data, crc)
        return crc & 0xFFFFFFFF  # Ensure unsigned 32-bit integer
    except Exception as e:
        print(f"Error computing CRC for {file_path}: {e}", file=sys.stderr)
        return None

def get_duration(file_path):
    """
    Get the duration of a media file in seconds.

    :param file_path: Path to the media file.
    :return: Duration in seconds, or None if retrieval fails.
    """
    try:
        probe = ffmpeg.probe(file_path)
        duration = float(probe['format']['duration'])
        return duration
    except (ffmpeg.Error, KeyError, ValueError):
        return None  # Return None if we can't get a valid duration

def get_file_size(file_path):
    """
    Get the file size in bytes.

    :param file_path: Path to the file.
    :return: File size in bytes.
    """
    return os.path.getsize(file_path)

def truncate_file_name(file_name, max_length=30):
    """
    Truncate a string to a fixed length and append '...' if needed.

    :param file_name: The original file name.
    :param max_length: Maximum allowed length.
    :return: Truncated file name.
    """
    if len(file_name) > max_length:
        return file_name[:max_length - 3] + '...'
    return file_name

def get_metadata(file_path):
    """
    Extract metadata (artist, album artist, album) from a media file.

    :param file_path: Path to the media file.
    :return: Tuple of (artist, album_artist, album, corrupt), each can be None.
    """
    try:
        audio_file = File(file_path, easy=True)
        if audio_file:
            artist = audio_file.get('artist', [None])[0]
            album_artist = audio_file.get('albumartist', [None])[0]
            album = audio_file.get('album', [None])[0]
            return (
                str(artist) if artist is not None else None,
                str(album_artist) if album_artist is not None else None,
                str(album) if album is not None else None,
                False
            )
    except Exception as e:
        #print(f"Error reading metadata for {file_path}: {e}", file=sys.stderr) # Screws up tqdm
        if e:
            return None, None, None, True

    return None, None, None, False


def is_roman_numeral(word):
    """
    Check if a word is a valid Roman numeral.

    :param word: The word to check.
    :return: True if it's a Roman numeral, False otherwise.
    """
    roman_numerals = {
        'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
        'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII',
        'XIX', 'XX', 'XXX', 'XL', 'L', 'LX', 'LXX', 'LXXX', 'XC',
        'C', 'CC', 'CCC', 'CD', 'D', 'DC', 'DCC', 'DCCC', 'CM',
        'M', 'MM', 'MMM'
    }
    return word.upper() in roman_numerals

def normalize_capitalization(text, exceptions):
    """
    Normalize the capitalization of a text string with exceptions,
    preserving all-caps words, Roman numerals, brackets, dashes, and slashes.

    :param text: The text to normalize.
    :param exceptions: A set of exception words to keep lowercase.
    :return: Normalized text.
    """
    if not text:
        return text

    # Pattern to match bracketed substrings
    pattern = r'(\[.*?\]|\(.*?\)|\{.*?\})'
    parts = re.split(pattern, text)

    normalized_parts = []
    for part in parts:
        if not part:
            continue
        # Check if this part is bracketed
        if (part.startswith('(') and part.endswith(')')) or \
           (part.startswith('[') and part.endswith(']')) or \
           (part.startswith('{') and part.endswith('}')):
            # Identify the bracket type
            opening = part[0]
            closing = part[-1]
            inner_text = part[1:-1]
            # Normalize the inner text
            normalized_inner = normalize_capitalization_inner(inner_text, exceptions)
            # Reconstruct the bracketed part
            normalized_part = f"{opening}{normalized_inner}{closing}"
            normalized_parts.append(normalized_part)

        else:
            # Normalize the non-bracketed part
            normalized_non_bracket = normalize_capitalization_inner(part, exceptions)
            normalized_parts.append(normalized_non_bracket)

    return ''.join(normalized_parts)

def normalize_capitalization_inner(text, exceptions):
    """
    Helper function to normalize capitalization for a segment of text.

    :param text: The text segment to normalize.
    :param exceptions: A set of exception words to keep lowercase.
    :return: Normalized text segment.
    """
    if not text:
        return text

    # Split by whitespace, keeping delimiters
    words = re.split(r'(\s+)', text)
    normalized_words = []
    for i, word in enumerate(words):
        if word.isspace():
            # Keep the whitespace as-is
            normalized_words.append(word)
            continue

        # Handle words with dashes or slashes
        if '-' in word or '/' in word:
            # Determine which separators are present
            separators = []
            if '-' in word:
                separators.append('-')
            if '/' in word:
                separators.append('/')

            # To handle multiple different separators, process one separator at a time
            for sep in separators:
                if sep in word:
                    subwords = word.split(sep)
                    normalized_subwords = []
                    for j, subword in enumerate(subwords):
                        # Check if the subword is in exceptions and not the first subword
                        if j != 0 and subword.lower() in exceptions:
                            normalized_subwords.append(subword.lower())
                            continue

                        # Check if the subword is all uppercase or a Roman numeral
                        if subword.isupper() or is_roman_numeral(subword):
                            normalized_subwords.append(subword)
                            continue

                        # Otherwise, capitalize the first letter and lowercase the rest
                        normalized_subwords.append(subword.capitalize())

                    # Rejoin the subwords with the separator
                    word = sep.join(normalized_subwords)
            normalized_words.append(word)
            continue

        lower_word = word.lower()
        # Check if the word is in exceptions and not the first word
        if i != 0 and lower_word in exceptions:
            normalized_words.append(lower_word)
            continue

        # Check if the word is all uppercase or a Roman numeral
        if word.isupper() or is_roman_numeral(word):
            normalized_words.append(word)
            continue

        # Otherwise, capitalize the first letter and lowercase the rest
        normalized_words.append(word.capitalize())

    return ''.join(normalized_words)

def get_unique_log_filename(current_working_dir, log_type, date_stamp, scanned_dir_basename):
    """
    Generate a unique log filename by appending an incrementing suffix if necessary.

    :param current_working_dir: The directory where the log file will be saved.
    :param log_type: Type of log (e.g., "unknown_artist", "updated_metadata").
    :param date_stamp: Date string in "YYYY-MM-DD" format.
    :param scanned_dir_basename: Basename of the directory being scanned.
    :return: Unique log file path.
    """
    # Start with suffix _0
    filename = f"{scanned_dir_basename}_{log_type}_{date_stamp}_0.txt"
    filepath = os.path.join(current_working_dir, filename)
    counter = 1
    # Increment suffix until an available filename is found
    while os.path.exists(filepath):
        filename = f"{scanned_dir_basename}_{log_type}_{date_stamp}_{counter}.txt"
        filepath = os.path.join(current_working_dir, filename)
        counter += 1
    return filepath

def log_missing_metadata(file_list, log_type):
    """
    Log files with missing metadata to a uniquely named text file.

    :param file_list: List of file paths with missing metadata.
    :param log_type: Type of missing metadata (e.g., "unknown_artist").
    """

    print(f"====================== FILES MISSING METADATA ({log_type}) =============================")
    if file_list:
        for file_path in file_list:
            print(f"{file_path}")
    else:
        print("No files missing metadata.")

def log_normalized_metadata(normalized_updates):
    """
    Log metadata normalization updates to a uniquely named text file.

    :param normalized_updates: List of normalization updates.
    """

    print(f"====================== NORMALIZED METADATA =============================")
    if normalized_updates:
        for update in normalized_updates:
            file_path = update['file_path']
            update_field = update['field']
            original = update['original']
            updated = update['updated']
            print(f"{update_field} | '{original}' -> '{updated}' | {file_path}: ")
    else:
        print("No tracks changed.")

def log_redundant_tracks(redundant_tracks):
    """
    Log redundant (duplicate) tracks to a uniquely named text file and print to console.

    :param redundant_tracks: List of tuples containing duplicate Track pairs.
    """
    if not redundant_tracks:
        print("No redundant tracks found.")
        return

    print(f"====================== REDUNDANT TRACKS =============================")

    for track1, track2 in redundant_tracks:
        print(f"Duplicate Pair:")
        print(f"1. {track1.file_path}")
        print(f"   Artist: {track1.artist}")
        print(f"   Album Artist: {track1.album_artist}")
        print(f"   Album: {track1.album}")
        print(f"   File Size: {track1.file_size} bytes\n")

        print(f"2. {track2.file_path}")
        print(f"   Artist: {track2.artist}")
        print(f"   Album Artist: {track2.album_artist}")
        print(f"   Album: {track2.album}")
        print(f"   File Size: {track2.file_size} bytes")
        print("-" * 80 + "")


def log_redundant_albums(album_tree):
    """
    Log all redundant albums to a text file in a human-readable format.

    :param album_tree: Dictionary representing the album tree.
    """

    print(f"============== POSSIBLE REDUNDANT ALBUMS =============================")

    for album in album_tree.values():

        if len(album.redundant) > 0:
            print(f"Album Name : {album.album_name}")
            print(f"Artist     : {album.artist}")
            print(f"Path       : {album.path}")
            print(f"Track Count: {album.track_count}")

            for redundant_album in album.redundant:
                print(f"\nAlbum Name : {redundant_album.album_name}")
                print(f"Artist     : {redundant_album.artist}")
                print(f"Path       : {redundant_album.path}")
                print(f"Track Count: {redundant_album.track_count}")

            print("=" * 80)

# Used for printing relative path of file
def eliminate_common_prefix(rootpath: str, filepath: str) -> str:
    root_len = len(rootpath)
    return "/" + filepath[root_len:] + "/"

def truncate_string(s, max_length=25):
    """
    Truncate a string to a maximum length, appending '...' if truncated.

    :param s: The string to truncate.
    :param max_length: The maximum allowed length of the string.
    :return: The truncated string.
    """
    if len(s) > max_length:
        return s[:max_length - 3] + "..."
    return s


def log_all_albums(album_tree, root_path):
    """
    Log all albums to a text file, sorted alphabetically by album_artist.
    Each line in the text file will have the format:
    <album_artist> <artist> <album> <path> <track_count>

    Metadata strings longer than 25 characters are truncated with '...'.

    :param root_path: Root directory music library lives in. Used to clip out root dir from album paths.
    :param album_tree: Dictionary representing the album tree.
    """

    # Collect all albums (primary and redundant)
    all_albums = []

    for album in album_tree.values():
        # Primary album
        all_albums.append({
            'album_artist': album.album_artist,
            'artist': album.artist,
            'album': album.album_name,
            'path': album.path,
            'track_count': album.track_count
        })
        # Redundant albums
        for redundant in album.redundant:
            all_albums.append({
                'album_artist': redundant.album_artist,
                'artist': redundant.artist,
                'album': redundant.album_name,
                'path': redundant.path,
                'track_count': redundant.track_count
            })

    # Sort the albums alphabetically by album_artist, then by artist, then by album
    all_albums_sorted = sorted(
        all_albums,
        key=lambda x: (x['album_artist'].lower(), x['artist'].lower(), x['album'].lower())
    )

    # Define column widths
    COLUMN_WIDTHS = {
        'album_artist': 25,
        'artist': 25,
        'album': 25,
        'track_count': 11,
        'path': 95
    }

    # Write Header
    header = (
        f"{'\nALBUM ARTIST'.ljust(COLUMN_WIDTHS['album_artist'])} | "
        f"{'ALBUM'.ljust(COLUMN_WIDTHS['album'])} | "
        f"{'ARTIST'.ljust(COLUMN_WIDTHS['artist'])} | "
        f"{'TRACK COUNT'.ljust(COLUMN_WIDTHS['track_count'])} | "
        f"{'PATH'.ljust(COLUMN_WIDTHS['path'])}"
    )
    print(header)
    print("=" * (sum(COLUMN_WIDTHS.values()) + 9))  # 9 for separators and spaces

    # Write Album Entries
    for album in all_albums_sorted:
        # Truncate metadata strings if necessary
        album_artist = truncate_string(album['album_artist'], COLUMN_WIDTHS['album_artist'])
        artist = truncate_string(album['artist'], COLUMN_WIDTHS['artist'])
        album_name = truncate_string(album['album'], COLUMN_WIDTHS['album'])
        path = truncate_string(eliminate_common_prefix(root_path, album['path'])[1:], COLUMN_WIDTHS['path'])  # Optional: Truncate path if needed

        # Format each line with fixed-width columns
        line = (
            f"{album_artist.ljust(COLUMN_WIDTHS['album_artist'])} | "
            f"{album_name.ljust(COLUMN_WIDTHS['album'])} | "
            f"{artist.ljust(COLUMN_WIDTHS['artist'])} | "
            f"{'Tracks: ' + str(album['track_count']).ljust(COLUMN_WIDTHS['track_count'] - 8)} | "
            f"{path.ljust(COLUMN_WIDTHS['path'])}"
        )
        print(line)



def find_redundant_tracks(crc_map):
    """
    Identify redundant (duplicate) tracks based on CRC and file size.

    :param crc_map: Dictionary mapping CRC values to lists of Tracks.
    :return: Tuple of (list of redundant Track pairs, count of duplicates).
    """
    redundant_tracks = []
    duplicates_count = 0

    for crc, tracks in crc_map.items():
        if len(tracks) < 2:
            continue  # No duplicates if less than 2 tracks share the CRC

        # Compare each track with every other track in the list
        for i in range(len(tracks)):
            for j in range(i + 1, len(tracks)):
                track1 = tracks[i]
                track2 = tracks[j]
                if track1.file_size == track2.file_size:
                    # Further verify by comparing metadata fields
                    if (track1.artist == track2.artist and
                        track1.album_artist == track2.album_artist and
                        track1.album == track2.album):
                        redundant_tracks.append((track1, track2))
                        duplicates_count += 1

    return redundant_tracks, duplicates_count

def normalize_and_save_metadata(file_path, artist, album_artist, album, exceptions, normalized_updates, verbose):
    """
    Normalize metadata capitalization and save changes if necessary.

    :param verbose: Prints to console if set
    :param file_path: Path to the media file.
    :param artist: Original artist metadata.
    :param album_artist: Original album artist metadata.
    :param album: Original album metadata.
    :param exceptions: Set of exception words.
    :param normalized_updates: List to append normalization updates.
    """
    updated = False
    try:
        audio_file = File(file_path, easy=True)
        if not audio_file and verbose:
            print(f"Cannot open file for metadata editing: {file_path}", file=sys.stderr)
            return

        # Normalize Artist
        if artist:
            normalized_artist = normalize_capitalization(artist, exceptions)
            if normalized_artist != artist:
                audio_file['artist'] = normalized_artist
                updated = True
                if verbose:
                    print(f"Normalized Artist: '{artist}' -> '{normalized_artist}'")
                    normalized_updates.append({
                        'file_path': file_path,
                        'field': 'Artist',
                        'original': artist,
                        'updated': normalized_artist
                    })

        # Normalize Album Artist
        if album_artist:
            normalized_album_artist = normalize_capitalization(album_artist, exceptions)
            if normalized_album_artist != album_artist:
                audio_file['albumartist'] = normalized_album_artist
                updated = True
                if verbose:
                    print(f"Normalized Album Artist: '{album_artist}' -> '{normalized_album_artist}'")
                normalized_updates.append({
                    'file_path': file_path,
                    'field': 'Album Artist',
                    'original': album_artist,
                    'updated': normalized_album_artist
                })

        # Normalize Album
        if album:
            normalized_album = normalize_capitalization(album, exceptions)
            if normalized_album != album:
                audio_file['album'] = normalized_album
                updated = True
                if verbose:
                    print(f"Normalized Album: '{album}' -> '{normalized_album}'")
                normalized_updates.append({
                    'file_path': file_path,
                    'field': 'Album',
                    'original': album,
                    'updated': normalized_album
                })

        if updated:
            audio_file.save()
            if verbose:
                print(f"Metadata updated for file: {file_path}")

    except Exception as e:
        if verbose:
            print(f"Error normalizing metadata for {file_path}: {e}", file=sys.stderr)

def prompt_fix_metadata(missing_folders, metadata_type, exceptions, media_extensions):
    """
    Prompt the user to fix missing metadata for each folder.

    :param missing_folders: List of folder paths with missing metadata.
    :param metadata_type: Type of metadata missing ('album_artist', 'album', 'artist').
    :param exceptions: Set of exception words.
    :param media_extensions: Set of supported audio file extensions.
    """
    for folder in missing_folders:
        print("=" * 80)
        print(f"Metadata '{metadata_type.replace('_', ' ').capitalize()}' missing for tracks in {folder}.")
        print("Affected files:")
        # Gather all relevant files in the folder with missing metadata
        affected_files = []
        for file_path in os.listdir(folder):
            full_path = os.path.join(folder, file_path)
            if os.path.isfile(full_path) and not file_path.startswith('.'):
                # Check if the specific metadata is missing
                artist, album_artist, album, corrupt = get_metadata(full_path)
                if corrupt:
                    print(f"Error: file '{file_path}' is corrupt!")
                else:
                    if metadata_type == 'album_artist' and not album_artist:
                        affected_files.append(full_path)
                    elif metadata_type == 'album' and not album:
                        affected_files.append(full_path)
                    elif metadata_type == 'artist' and not artist:
                        affected_files.append(full_path)

        if not affected_files:
            print("No affected files found.")
            continue

        for file in affected_files:
            print(f"- {file}")

        user_input = input(f"Enter {metadata_type.replace('_', ' ').capitalize()} to fix. (Return blank to cancel): ").strip()
        if not user_input:
            print("No changes made.")
            continue

        # Normalize user input
        normalized_input = normalize_capitalization(user_input, exceptions)
        print(f"{metadata_type.replace('_', ' ').capitalize()} will be set to '{normalized_input}'. Is that OK? (Y/n)")
        confirmation = input().strip().lower()
        if confirmation == 'n':
            print("Changes canceled.")
            continue

        # Apply changes
        for file_path in affected_files:
            # Check if the file extension is supported
            file_extension = os.path.splitext(file_path)[1][1:].lower()  # Get extension without dot
            if file_extension not in media_extensions:
                print(f"Skipping unsupported file format for {file_path}")
                continue

            try:
                audio_file = File(file_path, easy=True)
                if not audio_file:
                    print(f"Cannot open file for metadata editing: {file_path}", file=sys.stderr)
                    continue

                if metadata_type == 'album_artist':
                    audio_file['albumartist'] = normalized_input
                    audio_file.save()
                    print(f"Set Album Artist for {file_path} to '{normalized_input}'")
                elif metadata_type == 'album':
                    audio_file['album'] = normalized_input
                    audio_file.save()
                    print(f"Set Album for {file_path} to '{normalized_input}'")
                elif metadata_type == 'artist':
                    audio_file['artist'] = normalized_input
                    audio_file.save()
                    print(f"Set Artist for {file_path} to '{normalized_input}'")
            except Exception as e:
                print(f"Error setting {metadata_type.replace('_', ' ').capitalize()} for {file_path}: {e}", file=sys.stderr)

def update_status_bar(status_bar, file_name, total_files, total_size, total_duration):
    """
    Update the progress bar with current file information.

    :param status_bar: tqdm progress bar instance.
    :param file_name: Name of the current file.
    :param total_files: Total number of media files processed.
    :param total_size: Total size of media files processed in bytes.
    :param total_duration: Total duration of media files processed in seconds.
    """
    total_size_gb = total_size / (1000**3)  # Decimal GB
    total_size_gib = total_size / (1024**3)  # Binary GiB
    total_duration_hms = f"(h:m:s) {int(total_duration // 3600)}:{int((total_duration % 3600) // 60)}:{int(total_duration % 60)}"
    truncated_file_name = truncate_file_name(file_name, max_length=30)

    status_bar.set_postfix({
        "Files": total_files,
        "Size": f"{total_size_gb:.2f} GB / {total_size_gib:.2f} GiB",
        "Duration": total_duration_hms,
        "Song": truncated_file_name
    })
    status_bar.update(1)

def build_crc_map(all_tracks):
    """
    Build a CRC map from a list of Tracks.

    :param all_tracks: List of Track instances.
    :return: Tuple of (crc_map, crc_collision_count).
    """
    crc_map = defaultdict(list)
    crc_collision_count = 0

    for track in all_tracks:
        if track.crc is None:
            continue  # Skip tracks with failed CRC computation
        if crc_map[track.crc]:
            crc_collision_count += 1
        crc_map[track.crc].append(track)

    return crc_map, crc_collision_count

@dataclass
class Album:
    album_name: str
    artist: str
    path: str
    album_artist: str
    track_count: int = 1
    redundant: List['Album'] = field(default_factory=list)

def extract_all_albums(album_tree):
    """
    Extracts all albums from an album tree, including redundant albums.
    """
    album_list = []
    for album in album_tree.values():
        album_list.append(album)
        album_list.extend(album.redundant)  # Add redundant albums separately
    return album_list


def merge_album_trees(album_trees):
    """
    Merges multiple album trees into a single album tree by flattening them into a list first,
    then inserting them one by one using insert_album.
    """
    merged_tree = {}
    all_albums = []

    # Flatten all trees into a list of albums
    for album_tree in album_trees:
        all_albums.extend(extract_all_albums(album_tree))

    # Insert all extracted albums into the merged tree
    for album in all_albums:
        insert_album(merged_tree, album.album_name, album.artist, album.path, album.album_artist, album.track_count)

    return merged_tree

def insert_album(album_tree, album_name, artist, folder_path, album_artist, track_count=1):
    """
    Insert an album into the album tree sorted by album_artist.

    :param album_tree: Dictionary representing the album tree.
    :param album_name: Name of the album.
    :param artist: Primary artist of the album.
    :param folder_path: Directory path of the album.
    :param album_artist: Album artist of the album.
    :param track_count: track count of album to be inserted
    :return: Tuple (is_new_album: bool, is_redundant: bool)
    """
    # Ensure album_name and album_artist are strings
    if not album_name or not album_artist:
        return False, False  # Cannot process without album or album_artist

    album_key = str(album_name).lower()
    album_artist_key = str(album_artist).lower()

    if album_key not in album_tree:
        # New album
        album_tree[album_key] = Album(
            album_name=album_name,
            artist=artist,
            album_artist=album_artist,
            track_count=track_count,
            path=folder_path
        )
        return True, False  # is_new_album, is_redundant
    else:
        existing_album = album_tree[album_key]
        if existing_album.album_artist.lower() == album_artist_key and existing_album.path == folder_path:
            # Exact match, increment track count
            existing_album.track_count += track_count
            return False, False
        elif existing_album.album_artist.lower() == album_artist_key and existing_album.path != folder_path:
            # Same album and album_artist but different path, check redundancy
            duplicate = False
            for redundant_album in existing_album.redundant:
                if redundant_album.path == folder_path:
                    redundant_album.track_count += track_count
                    duplicate = True

                    # Check if this redundant album has now grown larger than the base album
                    if redundant_album.track_count > existing_album.track_count:
                        # Swap base album with the larger redundant album
                        existing_album.album_name, redundant_album.album_name = redundant_album.album_name, existing_album.album_name
                        existing_album.artist, redundant_album.artist = redundant_album.artist, existing_album.artist
                        existing_album.album_artist, redundant_album.album_artist = redundant_album.album_artist, existing_album.album_artist
                        existing_album.path, redundant_album.path = redundant_album.path, existing_album.path
                        existing_album.track_count, redundant_album.track_count = redundant_album.track_count, existing_album.track_count
                    break

            if not duplicate:
                new_redundant = Album(
                    album_name=album_name,
                    artist=artist,
                    album_artist=album_artist,
                    track_count=track_count,
                    path=folder_path
                )
                existing_album.redundant.append(new_redundant)

                # Check if the new redundant album has more tracks than the base
                if new_redundant.track_count > existing_album.track_count:
                    # Swap the base album with the redundant album
                    existing_album.album_name, new_redundant.album_name = new_redundant.album_name, existing_album.album_name
                    existing_album.artist, new_redundant.artist = new_redundant.artist, existing_album.artist
                    existing_album.album_artist, new_redundant.album_artist = new_redundant.album_artist, existing_album.album_artist
                    existing_album.path, new_redundant.path = new_redundant.path, existing_album.path
                    existing_album.track_count, new_redundant.track_count = new_redundant.track_count, existing_album.track_count

                return False, True
            else:
                return False, False
        else:
            # Different album_artist with same album name, treat as separate album
            unique_key = f"{album_key}_{album_artist_key}"
            if unique_key not in album_tree:
                album_tree[unique_key] = Album(
                    album_name=album_name,
                    artist=artist,
                    album_artist=album_artist,
                    track_count=track_count,
                    path=folder_path
                )
                return True, False
            else:
                # Exact match in unique key
                album_tree[unique_key].track_count += track_count
                return False, False


def print_album_statistics(album_tree, list_redundant_albums):
    """
    Print statistics about total and redundant albums.

    :param list_redundant_albums: Lists redundant albums if set
    :param album_tree: Dictionary representing the album tree.
    """
    total_albums = 0
    redundant_albums = 0
    redundant_track_count = 0
    #redundant_total_size = 0
    #redundant_total_duration = 0.0

    for album in album_tree.values():
        total_albums += 1
        for redundant in album.redundant:
            redundant_albums += 1
            redundant_track_count += redundant.track_count
            #print(f"track count {redundant.track_count}, name {redundant.album_name}, path {redundant.path}")
            # If you have track durations and sizes per album, aggregate them here
            # For simplicity, these are left as placeholders
            # redundant_total_size += calculate_size(redundant)
            # redundant_total_duration += calculate_duration(redundant)

    print(f"Total number of albums: {total_albums}")
    if list_redundant_albums:
        print(f"Total number of possible redundant albums: {redundant_albums}")
        print(f"Track Count of possibly redundant albums: {redundant_track_count}")
        # Uncomment and implement later if tracking redundant album size
        # print(f"Redundant Albums Total Size: {humanize.naturalsize(redundant_total_size, binary=True)}")
        # print(f"Redundant Albums Total Duration: {humanize.precise delta(redundant_total_duration)}")

def format_elapsed_time(elapsed_seconds):
    hours = int(elapsed_seconds // 3600)
    minutes = int((elapsed_seconds % 3600) // 60)
    seconds = int(elapsed_seconds % 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


@dataclass
class ProcessingOptions:
    verbose: bool = False
    list_unknown_artist: bool = False
    list_unknown_album_artist: bool = False
    list_unknown_album: bool = False
    normalize_capitalization_flag: bool = False
    list_redundant_tracks: bool = False
    list_redundant_album: bool = False
    list_all_albums: bool = False
    fix_missing_album_artist: bool = False
    fix_missing_album: bool = False
    fix_missing_artist: bool = False
    remove_desktop_ini_files: bool = False

import os
import sys
import time
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class ProcessingBuffers:
    total_files: int = 0
    total_music_files: int = 0
    total_media_files: int = 0
    total_duration: float = 0.0
    total_size: int = 0
    desktop_ini_removed: int = 0
    various_file_count: int = 0
    supported_extensions: dict = field(default_factory=lambda: defaultdict(int))
    unsupported_extensions: dict = field(default_factory=lambda: defaultdict(int))
    missing_artist: list = field(default_factory=list)
    missing_album_artist: list = field(default_factory=list)
    missing_album: list = field(default_factory=list)
    normalized_updates: list = field(default_factory=list)
    folders_missing_artist: set = field(default_factory=set)
    folders_missing_album_artist: set = field(default_factory=set)
    folders_missing_album: set = field(default_factory=set)
    all_tracks: list = field(default_factory=list)
    album_tree: dict = field(default_factory=dict)
    total_albums: int = 0
    redundant_albums: int = 0
    corrupt_file_count: int = 0
    corrupt_files: list = field(default_factory=list)


def process_file_multithreaded(file_path, options:ProcessingOptions, media_extensions, buffers):
    """
    Processes a single file and updates the given buffers.
    """
    file_name = os.path.basename(file_path)
    ext = file_name.split('.')[-1].lower()

    if options.verbose:
        print(f"Processing file path {file_path}")

    buffers.total_files += 1

    if options.remove_desktop_ini_files and file_name.lower() == 'desktop.ini':
        try:
            if options.verbose:
                print(f"Removed: {file_path}")
            os.remove(file_path)
            buffers.desktop_ini_removed += 1
        except Exception as e:
            print(f"Error removing {file_path}: {e}", file=sys.stderr)
        return

    if ext in media_extensions:
        # new music file if the extension is valid
        buffers.total_music_files += 1

        # Increment file count and add to dictionary
        buffers.supported_extensions[ext] += 1

        # Initialize track data

        # Initialize track data
        artist, album_artist, album, corrupt = get_metadata(file_path)
        if corrupt:  # Don't try to faff with corrupt files
            buffers.corrupt_file_count += 1
            buffers.corrupt_files.append(file_path)
            return

        duration = get_duration(file_path) or 0
        file_size = get_file_size(file_path) or 0
        crc = compute_crc32(file_path)

        buffers.total_media_files += 1
        if duration is not None:
            buffers.total_duration += duration
        else:
            if options.verbose:
                print(f"Warning: Could not retrieve duration for {file_path}")

        buffers.total_size += file_size

        folder_path = os.path.dirname(file_path)
        if options.list_unknown_artist and not artist:
            buffers.missing_artist.append(file_path)
            buffers.folders_missing_artist.add(folder_path)
        if options.list_unknown_album_artist and not album_artist:
            buffers.missing_album_artist.append(file_path)
            buffers.folders_missing_album_artist.add(folder_path)
        if options.list_unknown_album and not album:
            buffers.missing_album.append(file_path)
            buffers.folders_missing_album.add(folder_path)

        # If we are fixing missing metadata, add the path to the respective list
        if options.fix_missing_artist and not artist:
            buffers.folders_missing_artist.add(folder_path)
        if options.fix_missing_album_artist and not album_artist:
            buffers.folders_missing_album_artist.add(folder_path)
        if options.fix_missing_album and not album:
            buffers.folders_missing_album.add(folder_path)

        # Normalize metadata capitalization if requested
        exceptions = {"a", "an", "and", "as", "at", "but", "by",
                      "for", "in", "nor", "of", "on", "or", "the", "up"}
        if options.normalize_capitalization_flag and (artist or album_artist or album):
            normalize_and_save_metadata(file_path, artist, album_artist, album,
                                        exceptions, buffers.normalized_updates, options.verbose)

        # Insert into the album tree
        if album and artist:
            is_new_album, is_redundant = insert_album(buffers.album_tree, album, artist, folder_path, album_artist)
            if is_new_album:
                buffers.total_albums += 1
            if is_redundant:
                buffers.redundant_albums += 1

        track = Track(
            file_path=file_path,
            artist=artist,
            album_artist=album_artist,
            album=album,
            file_size=file_size,
            crc=crc
        )
        buffers.all_tracks.append(track)
    else:
        buffers.various_file_count += 1
        buffers.unsupported_extensions[ext] += 1


def process_chunk_multithreaded(files_chunk, options, media_extensions, progress_queue):
    """
    Processes a chunk of files and returns a ProcessingBuffers object.
    """
    buffers = ProcessingBuffers()
    for i, file_path in enumerate(files_chunk):
        process_file_multithreaded(file_path, options, media_extensions, buffers)
        if i % 5 == 0:  # Update tqdm every 5 files
            progress_queue.put(5)
    return buffers

def process_directory(directory, options: ProcessingOptions):
    """
    Process the specified directory with multithreading.
    """
    thread_count = min(32, multiprocessing.cpu_count() * 2)
    if options.verbose:
        print(f"Using {thread_count} Threads")
    start_time = time.perf_counter()

    media_extensions = {'mp3', 'flac', 'wav', 'aac', 'ogg', 'm4a', 'wma', 'aiff', 'opus', 'alac'}

    all_files = [os.path.join(root, file) for root, _, files in os.walk(directory) for file in files if
                 not file.startswith('.')]
    chunk_size = max(1, len(all_files) // thread_count)
    file_chunks = [all_files[i:i + chunk_size] for i in range(0, len(all_files), chunk_size)]

    results = []

    progress_queue = multiprocessing.Queue()

    def tqdm_updater(total_files):
        # Don't display tqdm bar is using verbose mode.
        # (Constant prints break the bar)
        if options.verbose is False:
            with tqdm(total=total_files, unit="file") as status_bar:
                while True:
                    progress = progress_queue.get()
                    if progress is None:
                        break

                    # Ensure we don't exceed 100%
                    if status_bar.n + progress > total_files:
                        break
                    status_bar.update(progress)

    updater_thread = multiprocessing.Process(target=tqdm_updater, args=(len(all_files),))
    updater_thread.start()

    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = {executor.submit(process_chunk_multithreaded, chunk, options, media_extensions, progress_queue): chunk
                   for chunk in file_chunks}
        for future in as_completed(futures):
            results.append(future.result())

    progress_queue.put(None)  # Signal tqdm to stop
    updater_thread.join()

    # Aggregate results
    final_buffers = ProcessingBuffers()
    album_buffers = []
    for buffer in results:
        final_buffers.total_files += buffer.total_files
        final_buffers.total_music_files += buffer.total_music_files
        final_buffers.total_media_files += buffer.total_media_files
        final_buffers.total_duration += buffer.total_duration
        final_buffers.total_size += buffer.total_size
        final_buffers.desktop_ini_removed += buffer.desktop_ini_removed
        final_buffers.various_file_count += buffer.various_file_count
        final_buffers.corrupt_file_count += buffer.corrupt_file_count

        for ext, count in buffer.supported_extensions.items():
            final_buffers.supported_extensions[ext] += count
        for ext, count in buffer.unsupported_extensions.items():
            final_buffers.unsupported_extensions[ext] += count

        final_buffers.missing_artist.extend(buffer.missing_artist)
        final_buffers.missing_album_artist.extend(buffer.missing_album_artist)
        final_buffers.missing_album.extend(buffer.missing_album)
        final_buffers.folders_missing_artist.update(buffer.folders_missing_artist)
        final_buffers.folders_missing_album_artist.update(buffer.folders_missing_album_artist)
        final_buffers.folders_missing_album.update(buffer.folders_missing_album)
        final_buffers.all_tracks.extend(buffer.all_tracks)
        final_buffers.corrupt_files.extend(buffer.corrupt_files)
        final_buffers.normalized_updates.extend(buffer.normalized_updates)

        # Parse all albums into the final album buffer
        album_buffers.append(buffer.album_tree)

    final_buffers.album_tree = merge_album_trees(album_buffers)
    scanned_dir_basename = os.path.basename(os.path.normpath(directory))

    # Print album statistics and final summary
    print("\n" + "=" * 80)
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    formatted_time = format_elapsed_time(elapsed_time)
    print(f"{final_buffers.total_files} Files parsed in: {formatted_time} (h:m:s)")

    # Print count of audio files
    if final_buffers.total_music_files > 0:
        print("\nTotal Audio File Count:")
        for ext, count in final_buffers.supported_extensions.items():
            print(f"{ext}: {count}")

    # Print count of non audio files
    if final_buffers.various_file_count > 0:
        print("\nTotal Non-Audio File Count:")
        for ext, count in final_buffers.unsupported_extensions.items():
            print(f"{ext}: {count}")

    # Print corrupt files
    if final_buffers.corrupt_file_count > 0:
        print(f"\nCorrupt files:{final_buffers.corrupt_file_count}")
        for corrupt_file in final_buffers.corrupt_files:
            print(f"    -{corrupt_file}")

    total_size_gb = final_buffers.total_size / (1000 ** 3)  # Decimal GB
    total_size_gib = final_buffers.total_size / (1024 ** 3)  # Binary GiB
    total_duration_hms = f"{int(final_buffers.total_duration // 3600)}:{int((final_buffers.total_duration % 3600) // 60)}:{int(final_buffers.total_duration % 60)}"
    print(f"\nTotal number of files: {final_buffers.total_files}")
    print(f"Total number of music files: {final_buffers.total_music_files}")
    print(f"Total duration of supported audio files: {total_duration_hms}")
    print(f"Total size of supported audio files: {total_size_gb:.2f} GB / {total_size_gib:.2f} GiB")
    print_album_statistics(final_buffers.album_tree, options.list_redundant_album)

    if options.list_all_albums:
        log_all_albums(final_buffers.album_tree, scanned_dir_basename)
    if options.normalize_capitalization_flag: # Log normalized metadata updates
        log_normalized_metadata(final_buffers.normalized_updates)
    if options.list_unknown_artist: # Log missing metadata
        log_missing_metadata(final_buffers.missing_artist, "unknown_artist")
    if options.list_unknown_album_artist:
        log_missing_metadata(final_buffers.missing_album_artist, "unknown_album_artist")
    if options.list_unknown_album:
        log_missing_metadata(final_buffers.missing_album, "unknown_album")
    if options.list_redundant_album:
        log_redundant_albums(final_buffers.album_tree)
    if options.list_redundant_tracks: # Log redundant tracks
        # Build CRC map
        crc_map, crc_collision_count = build_crc_map(final_buffers.all_tracks)
        redundant_tracks, duplicates_count = find_redundant_tracks(crc_map)
        log_redundant_tracks(redundant_tracks)
        print(f"Total redundant track pairs found: {duplicates_count}")
        print(f"Total CRC collisions detected: {crc_collision_count}")

    # Handle interactive metadata fixing
    if options.fix_missing_album_artist or options.fix_missing_album or options.fix_missing_artist:
        exceptions = {"a", "an", "and", "as", "at", "but", "by",
                      "for", "in", "nor", "of", "on", "or", "the", "up"}

        if options.fix_missing_album_artist and final_buffers.folders_missing_album_artist:
            prompt_fix_metadata(
                missing_folders=list(final_buffers.folders_missing_album_artist),
                metadata_type='album_artist',
                exceptions=exceptions,
                media_extensions=media_extensions)

        if options.fix_missing_album and final_buffers.folders_missing_album:
            prompt_fix_metadata(
                missing_folders=list(final_buffers.folders_missing_album),
                metadata_type='album',
                exceptions=exceptions,
                media_extensions=media_extensions)

        if options.fix_missing_artist and final_buffers.folders_missing_artist:
            prompt_fix_metadata(
                missing_folders=list(final_buffers.folders_missing_artist),
                metadata_type='artist',
                exceptions=exceptions,
                media_extensions=media_extensions)

class Tee:
    def __init__(self, filename, mode="w"):
        self.file = open(filename, mode)
        self.stdout = sys.stdout  # Save original stdout

    def write(self, message):
        self.stdout.write(message)  # Print to console
        self.file.write(message)  # Write to file

    def flush(self):
        self.stdout.flush()
        self.file.flush()

    def close(self):
        self.file.close()


def is_valid_filename(filename):
    """Check if the filename is a valid Linux filename."""
    invalid_chars = r'<>:"/\\|?*'
    return not any(char in filename for char in invalid_chars) and filename.strip() != ""

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Recursively count files, calculate durations, log missing metadata, "
            "normalize metadata capitalization, identify redundant tracks, "
            "and interactively fix missing metadata."
        )
    )
    parser.add_argument("directory", help="Directory to scan")
    parser.add_argument("--verbose", action="store_true",
                        help="Print each file as it is being processed (slow)")
    parser.add_argument("--log-output", type=str,
                        help="Optional log file to save output.")
    parser.add_argument("--list-unknown-artist", action="store_true",
                        help="List files with missing artist metadata")
    parser.add_argument("--list-unknown-album-artist", action="store_true",
                        help="List files with missing album artist metadata")
    parser.add_argument("--list-unknown-album", action="store_true",
                        help="List files with missing album metadata")
    parser.add_argument("--normalize-metadata-capitalization", action="store_true",
                        help="Normalize metadata capitalization to title case.\n "
                             "Is aware of exception words and Roman Numerals.\n"
                             "Leaves tags alone if they are all-caps.\n"
                             "(ex. your gold teeth II -> Your Gold Teeth II)\n"
                             "(ex. simon and garfunkel -> Simon and Garfunkel)\n"
                             "(ex. MFDOOM -> MFDOOM)")
    parser.add_argument("--list-redundant-tracks", action="store_true",
                        help="List all duplicate tracks in the directory. (Based on contents of files)")
    parser.add_argument("--list-redundant-albums", action="store_true",
                        help="Finds and lists potential redundant albums. (Based on file paths)")
    parser.add_argument("--list-all-albums", action="store_true",
                        help="Lists all albums in directory based on metadata tags.")
    parser.add_argument("--remove-desktop-ini-files", action="store_true",
                        help="Remove all 'desktop.ini' files and report the count")
    parser.add_argument("--fix-missing-album-artist-by-folder", action="store_true",
                        help="Interactively fix missing album artist metadata by folder")
    parser.add_argument("--fix-missing-album-by-folder", action="store_true",
                        help="Interactively fix missing album metadata by folder")
    parser.add_argument("--fix-missing-artist-by-folder", action="store_true",
                        help="Interactively fix missing artist metadata by folder")
    args = parser.parse_args()

    # Validate the directory
    if not os.path.isdir(args.directory):
        print(f"The specified directory does not exist or is not a directory: {args.directory}", file=sys.stderr)
        sys.exit(1)

    tee = None
    if args.log_output:
        if is_valid_filename(args.log_output):
            tee = Tee(args.log_output)
            sys.stdout = tee  # Redirect stdout to tee
        else:
            print(f"Error: '{args.log_output}' is not a valid Linux filename.", file=sys.stderr)
            sys.exit(1)

    options=ProcessingOptions(
        verbose=args.verbose,
        list_unknown_artist=args.list_unknown_artist,
        list_unknown_album_artist=args.list_unknown_album_artist,
        list_unknown_album=args.list_unknown_album,
        normalize_capitalization_flag=args.normalize_metadata_capitalization,
        list_redundant_tracks=args.list_redundant_tracks,
        fix_missing_album_artist=args.fix_missing_album_artist_by_folder,
        fix_missing_album=args.fix_missing_album_by_folder,
        fix_missing_artist=args.fix_missing_artist_by_folder,
        list_redundant_album=args.list_redundant_albums,
        list_all_albums=args.list_all_albums,
        remove_desktop_ini_files=args.remove_desktop_ini_files
    )

    process_directory(
        directory=args.directory,
        options=options
    )

    if tee:
        sys.stdout = tee.stdout  # Restore original stdout
        tee.close()

if __name__ == "__main__":
    main()
