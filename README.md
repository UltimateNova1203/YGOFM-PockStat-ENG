# Yu-Gi-Oh! Forbidden Memories PocketStation Translation Patch
After watching one too many Jon_Oh videos of Forbidden Memories, I got intrigued to find out if there was an english translation patch for the PocketStation app, which of course there was none. Since there are quite a few cards locked behind the PocketStation, it would be nice if it was translated so one can more easily navigate the app. I took it upon myself to figure out the apps inner workings, just enough to shove a list of 722 card names into it and hopefully get it to display.

# Patching
If you wish to patch this yourself, you can follow the below instructions. Otherwise, grab the save file from the Releases tab and insert it into your PocketStation memory card (via homebrew, or another application).

Note that this app requires 6 Blocks to be free on your PocketStation, versus the original's 4 Blocks. Currently, there is only a translation for English card names, and the app will target a NTSC-U region save. If someone would like to contribute a full list of cards in another language, I can have that added to the repository and create variants for other regions.

1. Dump your PocketStation App save from your memory card. The patch expects it to be a RAW save dump from the memory card, without the header. If you have a .MCS file, you will need to remove the MCS header from the file with a hex editor. 0x0h-0x7Fh (or everything before SC). [MemcardRex](https://github.com/ShendoXT/memcardrex) can export a RAW save that is compatible. I've used the extension .GME for the save.
2. Apply the `YGO-FM - Graphics + Region (USA).bps` patch to the original PocketStation App save.
3. Rename the patched save to `BASLUSP01411-YUGIOH.gme`.
4. Run the python script to patch in the translated names. Usage is as follows `python3 ./YGOFM-NamePatch.py ./BASLUSP01411-YUGIOH.gme Card-list.txt`
5. Import the raw save into your MemoryCard (whether that's vanilla or a PocketStation directly, your choice).
6. Enjoy the heart of the cards.

# Screenshots
![PocketStation Launcher Image](https://github.com/UltimateNova1203/YGOFM-PockStat-ENG/blob/main/Screenshots/01%20Launcher.png)
![Title Screen](https://github.com/UltimateNova1203/YGOFM-PockStat-ENG/blob/main/Screenshots/02%20Title.png)
![Main Menu](https://github.com/UltimateNova1203/YGOFM-PockStat-ENG/blob/main/Screenshots/03%20Menu.png)
![Bag View](https://github.com/UltimateNova1203/YGOFM-PockStat-ENG/blob/main/Screenshots/04%20Bag.png)
