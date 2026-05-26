import os
import subprocess
import textwrap
import winreg
import glob
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ==========================================
# Base Code Logic (No GUI) --- core logic that can be used independently of the GUI.

#ensure bat editor is launched with correct environment variables to find game DLLs
def launch_model_editor(model_editor_bat):
    model_editor_bat = os.path.abspath(model_editor_bat)
    game_dir = os.path.dirname(model_editor_bat)

    env = os.environ.copy()

    extra_paths = [
        game_dir,
        os.path.join(game_dir, "bin"),
        os.path.join(game_dir, "dll"),
        os.path.join(game_dir, "tools"),
    ]

    existing_path = env.get("PATH", "")
    env["PATH"] = os.pathsep.join(extra_paths + [existing_path])
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)

    subprocess.Popen(
        ["cmd.exe", "/c", model_editor_bat],
        cwd=game_dir,
        env=env,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

#Find windows and steam install path via registry, then find all library folders to search for TPF2 and the editor. This is more robust than hardcoding paths or relying on the user to select them, but will still fall back to manual selection if anything goes wrong.
def get_steam_install_path():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")
        install_path, _ = winreg.QueryValueEx(key, "InstallPath")
        return install_path
    except Exception:
        return None

def get_all_steam_library_paths(steam_path):
    libs = [steam_path]
    vdf_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
    if os.path.exists(vdf_path):
        try:
            with open(vdf_path, 'r', encoding='utf-8') as f:
                content = f.read()
                paths = re.findall(r'"path"\s+"(.*?)"', content)
                for p in paths:
                    libs.append(p.replace('\\\\', '\\'))
        except Exception:
            pass
    return libs

def auto_detect_environment():
    steam_path = get_steam_install_path()
    if not steam_path:
        return None, None, None

    model_editor_bat = None
    library_paths = get_all_steam_library_paths(steam_path)
    for lib in library_paths:
        target = os.path.join(lib, "steamapps", "common", "Transport Fever 2", "ModelEditor.bat")
        if os.path.exists(target):
            model_editor_bat = target
            break
            
    staging_dir = None
    userdata_root = os.path.join(steam_path, "userdata")
    if os.path.exists(userdata_root):
        search_pattern = os.path.join(userdata_root, "*", "1066780", "local", "staging_area")
        matches = glob.glob(search_pattern)
        if matches:
            staging_dir = matches[0]

    # AppData Verification
    user_data_dir = os.getenv('APPDATA')
    if not user_data_dir:
        user_data_dir = os.path.expanduser(r"~\AppData\Roaming")
    tf2_appdata_dir = os.path.join(user_data_dir, "Transport Fever 2")
    

    return model_editor_bat, staging_dir, tf2_appdata_dir

def build_tf2_mod_environment_core(mod_name, mod_tag, mod_desc, tags_list, con_type, year_from, year_to, fbx_dir, severity_add, severity_remove, mod_version):
    """The main logic function that was previously running in the terminal."""
    
    # 1. Detect Environment
    model_editor_bat, staging_dir, tf2_appdata_dir = auto_detect_environment()

    # 2. Manual Fallbacks via GUI Popups if Auto-Detection Fails
    if not model_editor_bat or not os.path.exists(model_editor_bat):
        messagebox.showinfo("Manual Selection", "Could not automatically locate 'ModelEditor.bat'.\nPlease select it manually.")
        model_editor_bat = filedialog.askopenfilename(
            title="Select ModelEditor.bat", 
            filetypes=[("Batch Files", "ModelEditor.bat"), ("All Batch Files", "*.bat")]
        )
        if not model_editor_bat:
            raise Exception("ModelEditor.bat selection cancelled. Cannot proceed.")

    if not staging_dir or not os.path.exists(staging_dir):
        messagebox.showinfo("Manual Selection", "Could not automatically locate the TF2 'staging_area' directory.\nPlease select it manually.")
        staging_dir = filedialog.askdirectory(title="Select 'staging_area' Folder")
        if not staging_dir:
            raise Exception("Staging directory selection cancelled. Cannot proceed.")

    if not tf2_appdata_dir or not os.path.exists(tf2_appdata_dir):
        messagebox.showinfo("Manual Selection", "Could not automatically locate the Transport Fever 2 AppData directory.\nPlease select it manually.")
        tf2_appdata_dir = filedialog.askdirectory(title="Select 'Transport Fever 2' AppData Folder")
        if not tf2_appdata_dir:
            raise Exception("AppData directory selection cancelled. Cannot proceed.")
    settings_file = os.path.join(tf2_appdata_dir, "model_editor_settings.lua")

    # 3. Clean mod name
    mod_name_clean = mod_name.removesuffix('_1').removesuffix('_2').removesuffix('_3').removesuffix('_4').removesuffix('_5').removesuffix('_6')
    

    # 4. Format tags
    if not tags_list:
        tags_list = ["Track Asset", "Misc"]
    lua_formatted_tags = ", ".join(f'"{tag}"' for tag in tags_list)

    # 5. Create mod folder
    mod_folder_name = f"{mod_name_clean}_{mod_version}"
    mod_path = os.path.join(staging_dir, mod_folder_name)
    os.makedirs(mod_path, exist_ok=True)

    # 6. Generate mod.lua
    mod_lua_content = textwrap.dedent(f"""\
        function data()
        return {{
            info = {{
                minorVersion = 0,
                severityAdd = "{severity_add}",
                severityRemove = "{severity_remove}",
                name = _("{mod_name_clean}"),
                description = _("{mod_desc}"),
                authors = {{
                    {{
                        name = "{mod_tag}",
                        role = "CREATOR",
                    }},
                }},
                tags = {{{lua_formatted_tags}}},
            }},
            options = {{
            }},
        }}
        end
    """)
    mod_lua_path = os.path.join(mod_path, "mod.lua")
    with open(mod_lua_path, "w") as f:
        f.write(mod_lua_content)

    # 7. Generate construction file
    con_dir = os.path.join(mod_path, "res", "construction", "asset", mod_name_clean)
    os.makedirs(con_dir, exist_ok=True)
    con_lua_path = os.path.join(con_dir, f"{mod_name_clean}.con")
    
    con_lua_content = textwrap.dedent(f"""\
        function data()
        return {{
            type = "{con_type}",
            description = {{
                name = _("{mod_name_clean} Asset"),
                description = _("A custom asset object."),
                icon = "ui/construction/asset/{mod_name_clean}/{mod_name_clean}.tga"
            }},
            availability = {{
                yearFrom = {year_from},
                yearTo = {year_to},
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
                        id = "asset/{mod_name_clean}.mdl",
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

    # 8. Modify Lua Settings (Safely)
    safe_fbx_dir = fbx_dir.replace('\\', '/')
    user_data_diractual = os.path.dirname(staging_dir)  
    safe_user_data_dir = user_data_diractual.replace('\\', '/')
    
    try:
        with open(settings_file, "r", encoding="utf-8") as f:
            lua_content = f.read()
        updated_content = re.sub(r'importFbxPath\s*=\s*["\'].*?["\']', f'importFbxPath = "{safe_fbx_dir}"', lua_content)
        updated_content = re.sub(r'userDataPath\s*=\s*["\'].*?["\']', f'userDataPath = "{safe_user_data_dir}"', updated_content)
        with open(settings_file, "w", encoding="utf-8") as f:
            f.write(updated_content)
    except Exception:
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

    # 9. Launch Editor
    launch_model_editor(model_editor_bat)
    return f"Success! Generated '{mod_folder_name}' and injected paths.\nSelect your mod folder in the Editor UI to import."



# Code 2: GUI INTERFACE (Tkinter) =================================================================

class TF2AssetHelperGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TPF2 Asset Setup Helper")
        self.geometry("620x750")
        self.configure(padx=20, pady=20)
        
        # Lists based strictly on TF2 documentation/files
        self.asset_types = [
            "ASSET_DEFAULT", "ASSET_TRACK", "INDUSTRY", 
            "STREET_STATION", "STREET_STATION_CARGO", 
            "RAIL_STATION", "RAIL_STATION_CARGO", 
            "HARBOR", "HARBOR_CARGO", 
            "AIRPORT", "AIRPORT_CARGO", 
            "STREET_DEPOT", "RAIL_DEPOT", 
            "WATER_DEPOT", "TOWN_BUILDING", 
            "STREET_CONSTRUCTION"
        ]

         # Valid warning/severity configurations according to game spec
        self.severity_options = ["NONE", "WARNING", "CRITICAL"]

        #Allowed verssion numbers (for now just 1-9)
        self.version_options = [f"{i}" for i in range(1, 10)]
        
        # Allowed Tags based for TPF2
        self.available_tags = [
            "Temperate", "Dry", "Tropical", "Europe", "USA", "Asia", "Map", "Savegame",
            "Locomotive", "Wagon", "Multiple Unit", "Bus", "Truck", "Tram", "Ship", "Plane",
            "Train Station", "Cargo Station", "Bus Station", "Truck Station", "Tram Station",
            "Airport", "Passenger Harbor", "Cargo Harbor", "Track", "Street", "Bridge", "Depot",
            "Tunnel", "Signal", "Railroad Crossing", "Street Construction", "Train Depot",
            "Road Depot", "Tram Depot", "Shipyard", "Building", "Industry", "Town Building",
            "Asset", "Brush Asset", "Track Asset", "Misc", "Script Mod", "Car", "Person",
            "Animal", "Sound", "Shader", "Mission", "Campaign", "Localization"
        ]

        self.create_widgets()
        
    def create_widgets(self):
        row = 0
        
        # explicit weight handling. Column 1 will absorb all resizing stretching,
        # keeps Column 0 (the text labels) locked at their full natural pixel widths.
        self.grid_columnconfigure(0, weight=0, minsize=140)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)
        self.grid_columnconfigure(3, weight=0)

        # --- Metadata Section ---
        tk.Label(self, text="Mod Metadata", font=("Segoe UI", 12, "bold")).grid(row=row, column=0, columnspan=4, sticky="w", pady=(0, 10))
        row += 1

        tk.Label(self, text="Mod Name:").grid(row=row, column=0, sticky="w")
        self.ent_mod_name = tk.Entry(self)
        self.ent_mod_name.grid(row=row, column=1, pady=4, sticky="ew")
        
        # Keeping version dropdown neatly tucked onto column 2 and 3
        tk.Label(self, text="Version:").grid(row=row, column=2, sticky="e", padx=(15, 5))
        self.combo_mod_version_type = ttk.Combobox(self, values=self.version_options, width=4, state="readonly")
        self.combo_mod_version_type.set("1")
        self.combo_mod_version_type.grid(row=row, column=3, pady=4, sticky="w")
        row += 1
        
        tk.Label(self, text="Mod Author ID:").grid(row=row, column=0, sticky="w")
        self.ent_mod_tag = tk.Entry(self)
        self.ent_mod_tag.grid(row=row, column=1, columnspan=3, pady=4, sticky="ew")
        row += 1
        
        tk.Label(self, text="Description:").grid(row=row, column=0, sticky="w")
        self.ent_mod_desc = tk.Entry(self)
        self.ent_mod_desc.grid(row=row, column=1, columnspan=3, pady=4, sticky="ew")
        row += 1

        tk.Label(self, text="Install Warning:").grid(row=row, column=0, sticky="w")
        self.combo_seva_type = ttk.Combobox(self, values=self.severity_options, state="readonly")
        self.combo_seva_type.set("NONE")
        self.combo_seva_type.grid(row=row, column=1, columnspan=3, pady=4, sticky="ew")
        row += 1

        tk.Label(self, text="Deinstall Warning:").grid(row=row, column=0, sticky="w")
        self.combo_sevr_type = ttk.Combobox(self, values=self.severity_options, state="readonly")
        self.combo_sevr_type.set("WARNING")
        self.combo_sevr_type.grid(row=row, column=1, columnspan=3, pady=4, sticky="ew")
        row += 1
        
        # --- Type and Availability ---
        tk.Label(self, text="\nAsset Type & Availability", font=("Segoe UI", 12, "bold")).grid(row=row, column=0, columnspan=4, sticky="w", pady=(10, 10))
        row += 1
        
        tk.Label(self, text="Construction Type:").grid(row=row, column=0, sticky="w")
        self.combo_con_type = ttk.Combobox(self, values=self.asset_types, state="readonly")
        self.combo_con_type.set("ASSET_DEFAULT")
        self.combo_con_type.grid(row=row, column=1, columnspan=3, pady=4, sticky="ew")
        row += 1
        
        tk.Label(self, text="Start Year (e.g. 1850):").grid(row=row, column=0, sticky="w")
        self.ent_year_from = tk.Entry(self)
        self.ent_year_from.insert(0, "1850")
        self.ent_year_from.grid(row=row, column=1, columnspan=3, pady=4, sticky="ew")
        row += 1
        
        tk.Label(self, text="End Year (0 = forever):").grid(row=row, column=0, sticky="w")
        self.ent_year_to = tk.Entry(self)
        self.ent_year_to.insert(0, "0")
        self.ent_year_to.grid(row=row, column=1, columnspan=3, pady=4, sticky="ew")
        row += 1
        
        # --- Paths Section ---
        tk.Label(self, text="\nDirectories", font=("Segoe UI", 12, "bold")).grid(row=row, column=0, columnspan=4, sticky="w", pady=(10, 10))
        row += 1
        
        tk.Label(self, text="FBX Import Path:").grid(row=row, column=0, sticky="w")
        frame_fbx = tk.Frame(self)
        frame_fbx.grid(row=row, column=1, columnspan=3, sticky="ew")
        
        # Use pack inside the frame to stretch the entry box cleanly alongside the button
        self.ent_fbx_dir = tk.Entry(frame_fbx)
        self.ent_fbx_dir.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        tk.Button(frame_fbx, text="Browse...", command=self.browse_fbx).pack(side=tk.RIGHT)
        row += 1

        # --- Tags Section ---
        tk.Label(self, text="\nMod Tags (Able to select multiple)", font=("Segoe UI", 12, "bold")).grid(row=row, column=0, columnspan=4, sticky="w", pady=(10, 5))
        row += 1
        
        frame_tags = tk.Frame(self, padx=2, pady=2)
        frame_tags.grid(row=row, column=0, columnspan=4, sticky="ew")
        
        scrollbar = tk.Scrollbar(frame_tags, orient=tk.VERTICAL)
        self.listbox_tags = tk.Listbox(
            frame_tags, 
            selectmode=tk.MULTIPLE, 
            yscrollcommand=scrollbar.set, 
            height=9
        )
        scrollbar.config(command=self.listbox_tags.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox_tags.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        for tag in sorted(self.available_tags):
            # Added space formatting inside the items list to keep text indented away from margins
            self.listbox_tags.insert(tk.END, f"  {tag}")
            
        row += 1
        
        # --- Submit Button (Centered & Styled) ---
        submit_btn = tk.Button(
            self, 
            text="Generate Mod & Launch Editor", 
            font=("Segoe UI", 12, "bold"), 
            bg="#1976D2", 
            fg="white", 
            cursor="hand2", 
            command=self.submit
        )
        submit_btn.grid(row=row, column=0, columnspan=4, pady=25, ipadx=25, ipady=8, sticky="")

    def browse_fbx(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.ent_fbx_dir.delete(0, tk.END)
            self.ent_fbx_dir.insert(0, folder_selected)

    def submit(self):
        # Gather inputs
        mod_name = self.ent_mod_name.get().strip()
        mod_tag = self.ent_mod_tag.get().strip()
        mod_desc = self.ent_mod_desc.get().strip()
        con_type = self.combo_con_type.get()
        year_from = self.ent_year_from.get().strip() or "1850"
        year_to = self.ent_year_to.get().strip() or "0"
        fbx_dir = self.ent_fbx_dir.get().strip()
        severity_add = self.combo_seva_type.get()
        severity_remove = self.combo_sevr_type.get()
        mod_version = self.combo_mod_version_type.get().strip() or "1.0"
        
        # Gather tags (strip strings to account for visual item spaces)
        selected_indices = self.listbox_tags.curselection()
        tags_list = [self.listbox_tags.get(i).strip() for i in selected_indices]
        
        # Validation checks
        if not mod_name or not fbx_dir:
            messagebox.showwarning("Missing Information", "Please ensure 'Mod Name' and 'FBX Import Path' are filled out.")
            return
            
        # Trigger core script
        try:
            success_msg = build_tf2_mod_environment_core(
                mod_name=mod_name,
                mod_tag=mod_tag,
                mod_desc=mod_desc,
                tags_list=tags_list,
                con_type=con_type,
                year_from=year_from,
                year_to=year_to,
                fbx_dir=fbx_dir,
                severity_add=severity_add,
                severity_remove=severity_remove,
                mod_version=mod_version
            )
            messagebox.showinfo("Success", success_msg)
        except Exception as e:
            messagebox.showerror("Execution Error", f"An error occurred while generating the environment:\n\n{str(e)}")

if __name__ == "__main__":
    app = TF2AssetHelperGUI()
    app.mainloop()
