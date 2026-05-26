import os
import subprocess
import textwrap
import winreg
import glob
import re

#exe shit
def launch_model_editor(model_editor_bat):
    model_editor_bat = os.path.abspath(model_editor_bat)
    game_dir = os.path.dirname(model_editor_bat)

    env = os.environ.copy()

    # Make sure ModelEditor can find DLLs beside the game/editor files.
    extra_paths = [
        game_dir,
        os.path.join(game_dir, "bin"),
        os.path.join(game_dir, "dll"),
        os.path.join(game_dir, "tools"),
    ]

    existing_path = env.get("PATH", "")
    env["PATH"] = os.pathsep.join(extra_paths + [existing_path])

    # Avoid PyInstaller/Python environment weirdness leaking into the editor.
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)

    subprocess.Popen(
        ["cmd.exe", "/c", model_editor_bat],
        cwd=game_dir,
        env=env,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

def get_steam_install_path():
    """Locate the primary Steam installation path from the Windows Registry."""
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")
        install_path, _ = winreg.QueryValueEx(key, "InstallPath")
        return install_path
    except Exception:
        return None

def get_all_steam_library_paths(steam_path):
    """Parses libraryfolders.vdf to find all Steam library locations."""
    libs = [steam_path] # Always include primary
    vdf_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
    
    if os.path.exists(vdf_path):
        try:
            with open(vdf_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Use regex to find all "path" entries in the vdf file
                paths = re.findall(r'"path"\s+"(.*?)"', content)
                for p in paths:
                    libs.append(p.replace('\\\\', '\\'))
        except Exception:
            pass
    return libs

def auto_detect_environment():
    """Attempts to find ModelEditor.bat and the Staging Area."""
    steam_path = get_steam_install_path()
    if not steam_path:
        return None, None

    # 1. Find ModelEditor.bat (Checking all libraries)
    model_editor_bat = None
    library_paths = get_all_steam_library_paths(steam_path)
    
    for lib in library_paths:
        target = os.path.join(lib, "steamapps", "common", "Transport Fever 2", "ModelEditor.bat")
        if os.path.exists(target):
            model_editor_bat = target
            break
            
    # 2. Find Staging Area (Usually in primary userdata)
    staging_dir = None
    userdata_root = os.path.join(steam_path, "userdata")
    if os.path.exists(userdata_root):
        # 1066780 is the appID for TF2
        search_pattern = os.path.join(userdata_root, "*", "1066780", "local", "staging_area")
        matches = glob.glob(search_pattern)
        if matches:
            staging_dir = matches[0]

    return model_editor_bat, staging_dir

def build_tf2_mod_environment():
    print("=== Transport Fever 2 Asset Setup Automator ===\n")
    
    # --- AUTOMATIC PATH DETECTION ---
    model_editor_bat, staging_dir = auto_detect_environment()

    # ModelEditor.bat Logic
    if not model_editor_bat:
        model_editor_bat = input("Could not auto-detect ModelEditor.bat. Please enter full path: ").strip().strip('"\'')
    else:
        print(f"[*] Found ModelEditor.bat: {model_editor_bat}")

    # Staging Area Logic
    if not staging_dir:
        staging_dir = input("Could not auto-detect Staging Area. Please enter full path: ").strip().strip('"\'')
    else:
        print(f"[*] Found Staging Area: {staging_dir}")

    # --- AUTOMATIC APPDATA DETECTION (Moved up to check for settings file existence) ---
    user_data_dir = os.getenv('APPDATA')
    if not user_data_dir:
        user_data_dir = os.path.expanduser(r"~\AppData\Roaming")
    
    if not os.path.exists(user_data_dir):
        print(f"[-] Could not automatically verify AppData path at: {user_data_dir}")
        user_data_dir = input("Please manually enter the full path to your AppData\\Roaming folder: ").strip().strip('"\'')
    else:
        print(f"[*] Auto-detected AppData directory: {user_data_dir}")
        
    tf2_appdata_dir = os.path.join(user_data_dir, "Transport Fever 2")
    settings_file = os.path.join(tf2_appdata_dir, "model_editor_settings.lua")

    # 2. Automated Initialization Check
    if not os.path.exists(settings_file):
        if os.path.exists(model_editor_bat):
            print("\n[+] 'model_editor_settings.lua' not found. Launching Model Editor to generate baseline settings...")
            launch_model_editor(model_editor_bat)
            input("\n[!] Close the Model Editor window once it opens, then press ENTER here to continue...")
        else:
            print("[-] Error: Cannot launch ModelEditor.bat to generate settings (Path invalid).")
            return
    else:
        print("[*] Found existing 'model_editor_settings.lua'. Skipping baseline run.")

    # 3. Request Mod Details
    print("\n--- Mod Metadata ---")
    mod_name = input("Enter Mod Name (e.g., Custom_Train [No need for version]): ").strip().strip('"\'') 
    mod_name = mod_name.removesuffix('_1\'').removesuffix('_2\'').removesuffix('_3\'').removesuffix('_4\'').removesuffix('_5\'').removesuffix('_6\'')
    mod_tag = input("Enter Mod Tag/Author ID: ").strip().strip('"\'')
    mod_desc = input("Enter Mod Description: [or leave blank to skip] ").strip().strip('"\'')
    
    print("\n--- Mod Tags ---")
    print("Common tags: Asset, Script Mod, Locomotive, Building, Station, Misc. Full list: https://wiki.transportfever2.com/doku.php?id=modding:modtags")
    tags_input = input("Enter asset tags separated by commas (e.g., Track, Industry): [you can leave this blank, but highly recommended to fill out before publishing] ").strip()

    print("\n--- Asset Type Configuration ---")
    type_map = {
        "1": "ASSET_DEFAULT", "2": "ASSET_TRACK", "3": "INDUSTRY", 
        "4": "STREET_STATION", "5": "STREET_STATION_CARGO", 
        "6": "RAIL_STATION", "7": "RAIL_STATION_CARGO", 
        "8": "HARBOR", "9": "HARBOR_CARGO", 
        "10": "AIRPORT", "11": "AIRPORT_CARGO", 
        "12": "STREET_DEPOT", "13": "RAIL_DEPOT", 
        "14": "WATER_DEPOT", "15": "TOWN_BUILDING", 
        "16": "STREET_CONSTRUCTION"
    }
    
    print("Select a Construction Type:")
    for key, value in type_map.items():
        print(f"  {key}: {value}")
    
    choice = input("\nEnter number (or custom string): ").strip() or "1"
    con_type = type_map.get(choice, choice)
    
    #Availability
    year_from = input("Enter Start Year (e.g., 1850): ").strip() or "1850"
    year_to = input("Enter End Year (0 for unlimited): ").strip() or "0"
    print("\nPlease note: The construction type and availability years will be set in the generated .con file, but you may need to further customize it after generation depending on your asset's needs:https://wiki.transportfever2.com/doku.php?id=modding:constructionbasics")
    
    # 4 Parse tags and format them into a valid Lua string array format
    tags_list = [t.strip() for t in tags_input.split(',')] if tags_input else ["Placeholder1", "Placeholder2"]
    lua_formatted_tags = ", ".join(f'"{tag}"' for tag in tags_list)

    # 5. Request Required Paths
    print("\n--- Directories ---")
    fbx_dir = input("Enter FBX Import Path (where your .fbx models are saved): ").strip().strip('"\'')

    # 6. Create the strictly formatted mod folder
    mod_folder_name = f"{mod_name}_1"
    mod_path = os.path.join(staging_dir, mod_folder_name)
    os.makedirs(mod_path, exist_ok=True)
    print(f"\n[+] Created mod directory: {mod_path}")

    # 7. Generate the primary mod.lua
    mod_lua_content = textwrap.dedent(f"""\
        function data()
        return {{
            info = {{
                minorVersion = 0,
                severityAdd = "NONE",
                severityRemove = "WARNING",
                name = _("{mod_name}"),
                description = _("{mod_desc}"),
                authors = {{
                    {{
                        name = "{mod_tag}",
                        role = "CREATOR",
                    }},
                }},
                tags = {{ {lua_formatted_tags} }},
            }},
            options = {{
            }},
        }}
        end
    """)
    mod_lua_path = os.path.join(mod_path, "mod.lua")
    with open(mod_lua_path, "w") as f:
        f.write(mod_lua_content)
    print(f"[+] Generated mod.lua at: {mod_lua_path}")

    # 8. Generate the base Construction (.con) file
    con_dir = os.path.join(mod_path, "res", "construction", "asset", mod_name)
    os.makedirs(con_dir, exist_ok=True)
    con_lua_path = os.path.join(con_dir, f"{mod_name}.con")
    
    con_lua_content = textwrap.dedent(f"""\
        function data()
        return {{
            type = "ASSET_DEFAULT",
            description = {{
                name = _("{mod_name} Asset"),
                description = _("A custom asset object."),
                icon = "ui/construction/asset/{mod_name}/{mod_name}.tga"
            }},
            availability = {{
                yearFrom = 1850,
                yearTo = 0,
            }},
            buildMode = "MULTI",
            categories = {{ "misc" }},
            order = 1,
            skipCollision = true,
            autoRemovable = false,
            updateFn = function(params)
                local result = {{ }}
                result.models = {{
                    {{
                        id = "asset/{mod_name}.mdl",
                        -- Identity matrix: places the object exactly as modeled
                        transf = {{ 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1 }}
                    }}
                }}
                result.terrainAlignmentLists = {{
                    {{
                        type = "EQUAL",
                        faces =  {{ }}
                    }}
                }}
                return result
            end
        }}
        end
    """)
    with open(con_lua_path, "w") as f:
        f.write(con_lua_content)
    print(f"[+] Generated construction script at: {con_lua_path}")

    # 9. Targeted Lua configuration modification (without clearing existing options)
    safe_fbx_dir = fbx_dir.replace('\\', '/')
    user_data_diractual = os.path.dirname(staging_dir)  
    safe_user_data_dir = user_data_diractual.replace('\\', '/')
    
    try:
        with open(settings_file, "r", encoding="utf-8") as f:
            lua_content = f.read()

        # Target only the path definitions using regex to preserve everything else
        updated_content = re.sub(r'importFbxPath\s*=\s*["\'].*?["\']', f'importFbxPath = "{safe_fbx_dir}"', lua_content)
        updated_content = re.sub(r'userDataPath\s*=\s*["\'].*?["\']', f'userDataPath = "{safe_user_data_dir}"', updated_content)

        with open(settings_file, "w", encoding="utf-8") as f:
            f.write(updated_content)
        print(f"[+] Successfully injected your custom paths into 'model_editor_settings.lua' without clearing options.")
        
    except Exception as e:
        print(f"[-] Error processing settings file natively: {e}")
        print("[*] Reverting to creating a default custom settings file...")
        settings_lua_content = textwrap.dedent(f"""\
            function data()
            return {{
                importFbxPath = "{safe_fbx_dir}",
                userDataPath = "{safe_user_data_dir}",
            }}
            end
        """)
        os.makedirs(tf2_appdata_dir, exist_ok=True)
        with open(settings_file, "w", encoding="utf-8") as f:
            f.write(settings_lua_content)

    # 10. Execute ModelEditor.bat again
    print("\n[+] Re-launching Transport Fever 2 Model Editor with injected parameters...")
    try:
        launch_model_editor(model_editor_bat)
        print("Done! Select your mod folder from the dropdown in the UI and hit 'Import' to grab the FBX.")
    except Exception as e:
        print(f"[-] Error launching Model Editor: {e}")

if __name__ == "__main__":
    build_tf2_mod_environment()
