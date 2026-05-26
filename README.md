Hi all,

I’ve made a small Windows helper tool for Transport Fever 2 asset modding:

It creates the basic mod files for simple asset mods and can set up the model_editor_settings.lua file if it does not already exist.

The aim is to streamline the early setup process before using the official Model Editor, especially the repetitive folder and Lua file setup.

A few important notes:

It does not replace the official Model Editor.
It is mainly intended for simple asset mods.
It does not create the full internal model structure inside the mod folder, because the Model Editor should handle that when the FBX is named/exported correctly from Blender.
Please do not use it on mods that already exist in your staging area, as duplicate mod names may cause existing Lua or .con files to be overwritten.
The program edits local Transport Fever 2 configuration/mod files, so please check the paths before running it and back up anything important.
