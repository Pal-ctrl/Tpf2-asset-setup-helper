# Transport Fever 2 Asset Setup Helper

A small Windows helper tool for **Transport Fever 2 asset modding**.

**v1.0.2 wipes model editor settings**

**v1.0.3 does not write tags correctly**


## What it does

This tool creates the basic mod files for simple asset mods and can set up the `model_editor_settings.lua` file if it does not already exist.

The aim is to streamline the early setup process before using the official Model Editor, especially the repetitive folder and Lua file setup.

It is designed to work with windows and steam... however if TPF2 is not downloaded throuh steam is will not automatically find the filepaths for you.

## Important notes

- This tool does **not** replace the official Model Editor.
- It is mainly intended for simple asset mods.
- It does **not** create the full internal model structure inside the mod folder, because the Model Editor should handle that when the FBX is named/exported correctly from Blender.
- **Please do not use it on mods that already exist in your staging area, as duplicate mod names may cause existing `.lua` or `.con` files to be overwritten.**
- The program edits local Transport Fever 2 configuration/mod files, so please check the paths before running it and back up anything important.

## Recommended workflow

1. Export/name your FBX correctly from Blender.
2. Run this helper tool.
3. Generate the basic mod files.
4. Import/save the model through the Model Editor.
5. Check or edit the generated mod files before publishing.

## Feedback

If you try it and run into issues, please open an issue on GitHub or let me know.
