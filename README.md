# MusicLibrarySolver

This Script is designed as companion software for people with large music collections to assist them in managing missing metadata, finding redundant tracks, redundant albums, etc. 

It also prints out statistics based on the entire music library. (Total files, total audio files, corrupt files, total albums, total duration of all tracks, etc.)

It is recommended to use this script in conjunction with a Music Player such as Strawberry.

# KEY FEATURES AND USAGE

    music_stats.py directory [-h] [--verbose] [--log-output LOG_OUTPUT] [--list-unknown-artist] [--list-unknown-album-artist] [--list-unknown-album] [--normalize-metadata-capitalization] [--list-redundant-tracks] [--list-redundant-albums] [--list-all-albums] [--remove-desktop-ini-files] [--fix-missing-album-artist-by-folder] [--fix-missing-album-by-folder] [--fix-missing-artist-by-folder] [--num-threads NUM_THREADS]
                      
positional arguments:
    directory
        Directory to scan. It is recommended to run the script from the same hard drive that the music library lives on for faster performance.

--log-output LOG_OUTPUT:

    The script will log its output to a file specified by the user. It is recommended to always use this when running any command that changes metadata to keep
    a running log of what metadata was changed.

--list-redundant-albums:

    This script assumes a base level of file organization. It assumes that a series of files sharing a directory and metadata tags will belong to the same album.

    For example,

    /MusicLibrary/EpicArtist/EpicAlbum

     or

    /MusicLibrary/EpicAlbum

    All files in EpicAlbum sharing an album tag will be assumed to belong to the same album. If it sees files sharing an album spread across different directories, it will list them as potentially redundant.

    /MusicLibrary/EpicAlbum

    /MusicLibrary/EpicAlbum (Copy)

    Can also be used to point out multi-disc albums missing the disc tag. For example:

    /MusicLibrary/EpicAlbumDisk1

    /MusicLibrary/EpicAlbumDisk2

    Will be marked as potentially redundant if the files in each directory does not have the disc index tagged. The output will provide file paths to allow the user to tag the files.

--normalize-metadata-capitalization:

    This script implements features to enforce a uniform capitalization scheme across all metadata tags. The script will enforce a "Title Case" scheme across all tabs, with exceptions.

    Words "a", "an", "and", "as", "at", "but", "by", "for", "in", "nor", "of", "on", "or", "the", "up" will be set to lower case.

    Roman Numerals ('I', 'II', 'III', 'IV', 'V', 'VI', etc.) will all be set to upper case.

    Words that are already set to ALL CAPS will remain in all caps.

    Examples:
    
    your gold teeth ii -> Your Gold Teeth II
    black and gold -> Black and Gold
    MFDOOM -> MFDOOM (No Change)

    This isn't perfect, but works for 99% of tags. In my library, the only thing I needed to manually change back was 2Pac. (2Pac -> 2pac) Once the script concludes, it will print a list to the user of all tags changed.

--fix-missing-album-artist-by-folder, --fix-missing-album-by-folder, --fix-missing-artist-by-folder:

    As the script runs, it will log any files that are missing key metadata. Once the script finished running, it will prompt the user for the missing tags and apply it to all files in the containing folder.

    if --normalize-metadata-capitalization is set, it will normalize the capitalization scheme before applying changes.

    After the user has entered the tag, the script will confirm the entered tag is correct before applying. Should the user enter a typo, they can opt to not apply tags.

--list-unknown-artist, --list-unknown-album-artist, --list-unknown-album:

    lists the file paths of tracks with missing metadata once the script concludes without prompting the user to change them. It is recommended to use these flags before running the fix flags.

--list-all-albums:

    The script will keep track of all albums as it runs, and print out a formatted list of albums once concluded.

--verbose:

    Script will pump each file as it parses to the console, instead of using a TQDM bar. This will slow down the script marginally.

--remove-desktop-ini-files:

    Removes all Windows ".ini" files from all directories, recursively, and keeps a running total of all ini files removed. This is only useful to Linux/Mac users.

--num-threads NUM_THREADS:

    The user can manually override the total number of threads the script can open. By default, the script will open 2x the number of cores of the hardware. This can slow 
    the script down for large libraries, but leave resources available for other software on the machine.
                        
# EXAMPLE OUTPUT

    ============================== LIBRARY STATISTICS ==============================
    38 Files parsed in: 00:00:15 (h:m:s)
    
    Total Audio File Count:
    mp3: 22
    m4a: 5
    flac: 1
    
    Total Image File Count:
    jpeg: 10

    Total Video File Count:
    mpeg: 3

    Total Various File Count:
    txt: 2
    
    Corrupt files:1
        -Music/EpicAnimeMusic/OnePieceRap_4kids.flac
    
    Total number of files: 38
    Total number of music files: 28
    Total duration of supported audio files: 2:21:21
    Total size of supported audio files: 500.00 MB / 476.84 MiB
    Total number of albums: 3
    Total number of possible redundant albums: 1
    Redundant Album Track Count: 12
    
    ALBUM ARTIST             | ALBUM                                    | ARTIST                    | TRACK COUNT | DISC NUMBER | PATH
    ======================================================================================================================================================================================================================
    Epic Album Artist        | Epic Album                               | Epic Artist               | Tracks: 12  | Disc: 1 | /EpicArtist/EpicAlbumDisk1/
    Epic Album Artist        | Epic Album                               | Epic Artist               | Tracks: 10  | Disc: 2 | /EpicArtist/EpicAlbumDisk2/
    Guitar Man and Co.       | Shredding the GUITAR II                  | Guitar Man                | Tracks: 5  | Disc: 0 | /GuitarMan/TheGuitarAlbum/
    ============================= NORMALIZED METADATA ==============================
    Album | 'shredding the GUITAR II' -> 'Shredding the GUITAR II' | /GuitarMan/TheGuitarAlbum/Shrek_N_Roll.mp3:
    Album | 'shredding the GUITAR II' -> 'Shredding the GUITAR II' | /GuitarMan/TheGuitarAlbum/The_Shredshank_Redemption.mp3:
    Album | 'shredding the GUITAR II' -> 'Shredding the GUITAR II' | /GuitarMan/TheGuitarAlbum/Shrednado.mp3:
    Album | 'shredding the GUITAR II' -> 'Shredding the GUITAR II' | /GuitarMan/TheGuitarAlbum/Lord_of_the_SHRED.mp3:
    Album | 'shredding the GUITAR II' -> 'Shredding the GUITAR II' | /GuitarMan/TheGuitarAlbum/Shred_Wars_the_Empire_SHREDS_Back.mp3:
    ==================== FILES MISSING METADATA: unknown_artist ====================
    Music/EpicAnimeMusic/OnePieceRap_4kids.flac
    ================= FILES MISSING METADATA: unknown_album_artist =================
    Music/EpicAnimeMusic/OnePieceRap_4kids.flac
    ==================== FILES MISSING METADATA: unknown_album =====================
    Music/EpicAnimeMusic/OnePieceRap_4kids.flac
    ========================== REDUNDANT/MISTAGGED ALBUMS ==========================
    Note: Albums listed here are either redundant or missing disc tags
    --------------------------------------------------------------------------------
    Album Name : Epic Album
    Artist     : Epic Album Artist
    Path       : /EpicArtist/EpicAlbumDisk1/
    Track Count: 12
    
    Album Name : Epic Album
    Artist     : Epic Album Artist
    Path       : /EpicArtist (Copy)/EpicAlbumDisk1/
    Track Count: 12
    --------------------------------------------------------------------------------
    =============================== REDUNDANT TRACKS ===============================
    Note: Tracks listed here are found to have matching contents and metadata
    --------------------------------------------------------------------------------
    Duplicate Pair:
    1. /EpicArtist/EpicAlbumDisk1/OnePieceRap_Metal_Cover.mp3
       Artist: Epic Album Artist
       Album Artist: Epic Album Artist
       Album: Epic Album
       File Size: 5641564 bytes
    
    2. /EpicArtist (Copy)/EpicAlbumDisk1/OnePieceRap_Metal_Cover.mp3
       Artist: Epic Album Artist
       Album Artist: Epic Album Artist
       Album: Epic Album
       File Size: 5641564 bytes
    --------------------------------------------------------------------------------
