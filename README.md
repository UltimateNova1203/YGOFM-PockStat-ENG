# Yu-Gi-Oh! Forbidden Memories PocketStation Translation Patch

After watching one too many Jon_Oh videos of Forbidden Memories, I got intrigued to find out if there was an english translation patch for the PocketStation app, which of course there was none. Since there are quite a few cards locked behind the PocketStation, it would be nice if it was translated so one can more easily navigate the app. I took it upon myself to figure out the apps inner workings, just enough to shove a list of 722 card names into it and hopefully get it to display.

| Region      | Progress                          | Completed         |
|-------------|-----------------------------------|-------------------|
| NTSC-U/C    |![](https://geps.dev/progress/100) | Everything        |
| PAL-English |![](https://geps.dev/progress/50)  | Graphics + Region |
| PAL-French  |![](https://geps.dev/progress/10)  | Region            |
| PAL-German  |![](https://geps.dev/progress/10)  | Region            |
| PAL-Italian |![](https://geps.dev/progress/10)  | Region            |
| PAL-Spanish |![](https://geps.dev/progress/10)  | Region            |

## Save Size

The original app's size was 4 Blocks. Due to the length of the translated card names, the new app size is now 6 Blocks.

I apologize for the increase in size, but without a full disassembly of the app, we really can't decrease the size more than it is. If a disassembly exists so we can re-arrange the app as we please, we could possibly get this down to only 5 Blocks.

## Patching

If you wish to patch this yourself, you can follow the below instructions. Otherwise, grab the save file from the Releases tab and insert it into your PocketStation memory card (via homebrew, or another application).

Note that this app requires 6 Blocks to be free on your PocketStation, versus the original's 4 Blocks. Currently, there is only a translation for English. If someone would like to contribute a full list of cards in another language, I can have that added to the repository.

This patch has tools that rely on Python v3.x, the Windows BAT files are untested.

1. Dump your PocketStation App Save from the memory card. The patch scripts assume it is a RAW Save dump, but there are flags for MCS Headered saves, or you can specify your own offset. [MemcardRex](https://github.com/ShendoXT/memcardrex) can export a RAW save that is compatible. I've used the extension .GME for the save.
2. Run the `decompile.sh` or `decompile.bat` script to decompile the ROM's graphics.
  a. If you wish to use your own graphics, you can edit the files in the ./textures folder
3. Run the `compile.sh` or `compile.bat` script to recompile the ROM's graphics, and apply the region/language's respective changes.
4. Rename the save file to your region's save name.
  a. NTSC-U/C: `BASLUSP01411-YUGIOH.gme`
  b. PAL-English: `BASLESP03947-YUGIOH.gme`
  c. PAL-French: `BASLESP03948-YUGIOH.gme`
  d. PAL-German: `BASLESP03949-YUGIOH.gme`
  e. PAL-Italian: `BASLESP03950-YUGIOH.gme`
  f. PAL-Spanish: `BASLESP03951-YUGIOH.gme`
5. Import the save into your memory card.
6. Enjoy the the translated app, or give the Card Lottery a try with the code `Right Right Left Right Left Left Right Left Start` while hovering the `Bag` menu entry.

## Screenshots

![PocketStation Launcher Image](https://github.com/UltimateNova1203/YGOFM-PockStat-ENG/blob/main/screenshots/launcher.gif)
![Title Screen](https://github.com/UltimateNova1203/YGOFM-PockStat-ENG/blob/main/screenshots/title.gif)
![Main Menu](https://github.com/UltimateNova1203/YGOFM-PockStat-ENG/blob/main/screenshots/menu.gif)
![Bag View](https://github.com/UltimateNova1203/YGOFM-PockStat-ENG/blob/main/screenshots/bag.gif)
