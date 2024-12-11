# MusicLibrarySolver

This script is designed to help people wrangle large music collections. It can be used to count tracks, calucalte total duration of a music library, calculate file size, point out missing metadata, normalize the metadata capitalization scheme across the collection, identify redundant tracks, and much more. 

#USAGE

USAGE: music_stats.py [-h] [--verbose] [--list-unknown-artist]
                      [--list-unknown-album-artist] [--list-unknown-album]
                      [--normalize-metadata-capitalization]
                      [--list-redundant-tracks]
                      [--fix-missing-album-artist-by-folder]
                      [--fix-missing-album-by-folder]
                      [--fix-missing-artist-by-folder]
                      [--list-redundant-album] [--list-all-albums]
                      [--remove-desktop-ini-files]
                      directory

positional arguments:
  directory             Directory to scan

options:
  --verbose             Print each file as it is being processed
  
  --list-unknown-artist
                        List files with missing artist metadata (List provided as text file)
                        
  --list-unknown-album-artist
                        List files with missing album artist metadata (List provided as text file)
                        
  --list-unknown-album  List files with missing album metadata (List provided as text file)
  
  --normalize-metadata-capitalization
                        Sets the metadata capitalization across all artists/albums/albumartists to Title Case

                        Note: There are a few expections to this flag. Roman Numerals will be
                        left all caps. Additionally, artists that already have their name in 
                        all caps (such as MF DOOM) will not be normalized. However, this flag
                        is pretty dumb overall. Use caution when using this flag. It works for
                        99% of artists/albums, but you may need to go back and manually fix the 
                        capitalization of a few tags.
                        
  --list-redundant-tracks
                        List all duplicate tracks in the directory (List provided as text file)

                        Note: All files are hashed into a 64 bit CRC and compared. Collisions may
                        occur with this method, but should be exceedingly rare.
                        
  --fix-missing-album-artist-by-folder
                        Interactively fix missing album artist metadata by folder

                        Note: This will build up a list of tracks missing an album artist,
                        and manually prompt the user to enter the metadata once the script
                        concludes. Do note that this feature is based on directory. Meaning,
                        it assumes that all files in the directory should share the metadata.

                        To be clear, this feature will only work for music collections already
                        ordered as such:
                        
                        collection/artist/album/tracks
                        
  --fix-missing-album-by-folder
                        Interactively fix missing album metadata by folder

                        Note: This will build up a list of tracks missing an album tags,
                        and manually prompt the user to enter the metadata once the script
                        concludes. Do note that this feature is based on directory. Meaning,
                        it assumes that all files in the directory should share the metadata.

                        To be clear, this feature will only work for music collections already
                        ordered as such:
                        
                        collection/artist/album/tracks
                        
  --fix-missing-artist-by-folder
                        Interactively fix missing artist metadata by folder

                        Note: This will build up a list of tracks missing an artist tag,
                        and manually prompt the user to enter the metadata once the script
                        concludes. Do note that this feature is based on directory. Meaning,
                        it assumes that all files in the directory should share the metadata.

                        To be clear, this feature will only work for music collections already
                        ordered as such:
                        
                        collection/artist/album/tracks
                        
  --list-redundant-album
                        List all redundant albums and save to a text file (List provided as text file)
                        
  --list-all-albums     List all albums and save to a text file
  
  --remove-desktop-ini-files
                        Remove all 'desktop.ini' files and report the count

                        Note: For whatever reason, Windows decides to put a pointless file 
                        called "desktop.ini" in every folder. This file serves no purpose
                        for Mac and Linux users. This switch will go through the entire directory
                        and rip out all desktop.ini files. This feature will only be useful
                        for non-windows users.

                        
#EXAMPLE OUTPUT
