# pksuperbox
 
PK Super Box is an application to replicate the features of "Pokémon Bank" and "Pokémon Home", but for the generation 1-3 Pokémon games as well as ROM hacks.

# Compatibility

Releases will have a `.exe` file bundled in. There's no guarantee it will be compatible with anything other than the version of Windows that I run. Anybody should be able to run it from source, with the only dependency being `pygame`. The `im_rip.py` script also depends on `PIL`.

# Supported games

Currently supported games are:

| Game | Languages | Revisions |
| ---- | --------- | --------- |
| **Vanilla** |||
| Pokémon Emerald | Eng, Jpn, Ger, Fre, Spa, Ita| All |
| Pokémon FireRed | Eng | All |
| Pokémon LeafGreen | Eng | All |
| Pokémon Ruby | Eng | All |
| Pokémon Crystal | Eng | All |
| Pokémon Blue | Eng | All |
| **ROM Hacks**|||
| Pokémon Crystal Clear | Eng | 2.5.8 |
| Pokémon Prism | Eng | 0.94.0237 |
| Pokémon Gold & Silver 97: Reforged | Eng | 6.0b |
| Pokémon CrystalLeaf | Eng | 1.4.1 |
| Pokémon Ruby Destiny: Reign of Legends | Eng | 4.1 |
| Pokémon Altair | Eng | - |
| Pokémon Sirius | Eng | - |
| Pokémon Vega | Eng, Jpn | - |
| Pokémon Brown | Eng | 2014 |

If you want a specific game to get support, or if you are an author that would like to get your hack supported, feel free to contact me.

# How to get images

By default, the app does NOT come with Pokémon sprites. You will have to either provide your own, or use `im_rip.py` to read them from legally-acquired ROM files.

To use `im_rip.py`:
1. Place your ROM files into `imrip/roms/`.
2. Run `python im_rip.py`
The script will extract the relevant images from the provided files for use in the app.
