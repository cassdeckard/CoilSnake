#! /usr/bin/env python
import Tkinter
from functools import partial
import logging
from subprocess import Popen
from threading import Thread
from Tkinter import *
import tkFileDialog
import tkMessageBox
import tkSimpleDialog
import ttk
import os

from PIL import ImageTk

from coilsnake.ui import information, gui_util
from coilsnake.ui.common import decompile_rom, compile_project, upgrade_project, setup_logging, decompile_script
from coilsnake.ui.fun import get_fun_title
from coilsnake.ui.gui_preferences import CoilSnakePreferences
from coilsnake.ui.gui_util import browse_for_rom, browse_for_project, open_folder, set_entry_text
from coilsnake.ui.information import coilsnake_about
from coilsnake.ui.progressbar import GuiProgressBar
from coilsnake.util.common.project import PROJECT_FILENAME
from coilsnake.util.common.assets import asset_path


log = logging.getLogger(__name__)


class CoilSnakeGui(object):
    def __init__(self):
        self.preferences = CoilSnakePreferences()
        self.preferences.load()
        self.components = []
        self.progress_bar = None

    # Preferences functions

    def toggle_titles(self):
        self.preferences["title"] = not self.preferences["title"]
        self.preferences.save()

    def set_emulator_exe(self):
        emulator_exe = tkFileDialog.askopenfilename(
            parent=self.root,
            title="Select an Emulator Executable",
            initialfile=self.preferences["emulator"])
        if emulator_exe:
            self.preferences["emulator"] = emulator_exe
            self.preferences.save()

    # GUI update functions

    def clear_console(self):
        self.console.delete(1.0, END)
        self.console.see(END)

    def disable_all_components(self):
        for component in self.components:
            component["state"] = DISABLED

    def enable_all_components(self):
        for component in self.components:
            component["state"] = NORMAL

    # GUI popup functions

    def about_menu(self):
        about_menu = Toplevel(self.root)

        photo = ImageTk.PhotoImage(file=asset_path(["images", "logo.png"]))
        about_label = Label(about_menu, image=photo)
        about_label.photo = photo
        about_label.pack(side=LEFT, expand=1)

        about_right_frame = ttk.Frame(about_menu)
        Label(about_right_frame,
              text=coilsnake_about(),
              height=15,
              anchor="w",
              justify="left",
              bg="white",
              borderwidth=5,
              relief=GROOVE).pack(fill=BOTH, expand=1, side=TOP)
        Button(about_right_frame, text="Toggle Alternate Titles", command=self.toggle_titles).pack(fill=BOTH, expand=1)
        Button(about_right_frame, text="Close", command=about_menu.destroy).pack(fill=BOTH, expand=1)

        about_right_frame.pack(side=LEFT, fill=BOTH, expand=1)

        about_menu.resizable(False, False)
        about_menu.title("About CoilSnake {}".format(information.VERSION))

    def run_rom(self, entry):
        rom_filename = entry.get()
        if not self.preferences["emulator"]:
            tkMessageBox.showerror(parent=self.root,
                                   title="Error",
                                   message="""Emulator executable not specified.
Please specify it in the Preferences menu.""")
        elif rom_filename:
            Popen([self.preferences["emulator"], rom_filename])
    
    def edit_project(self, entry):
        project_path = entry.get()
        if not self.preferences["java"]:
            tkMessageBox.showerror(parent=self.root,
                                   title="Error",
                                   message="""Java executable not specified.
Please specify it in the Preferences menu.""")
        elif project_path:
            Popen([self.preferences["java"], "-jar", asset_path(["bin", "EbProjEdit.jar"]),
                   os.path.join(project_path, PROJECT_FILENAME)])

    # Actions

    def do_decompile(self, rom_entry, project_entry):
        rom = rom_entry.get()
        project = project_entry.get()

        if rom and project:
            # Update the GUI
            self.clear_console()
            self.disable_all_components()

            self.progress_bar.set(0)
            thread = Thread(target=self._do_decompile_help, args=(rom, project))
            thread.start()

    def _do_decompile_help(self, rom, project):
        try:
            decompile_rom(rom_filename=rom, project_path=project, progress_bar=self.progress_bar)
        except Exception as inst:
            log.exception("Error")

        self.progress_bar.set(0)
        self.enable_all_components()

    def do_compile(self, project_entry, base_rom_entry, rom_entry):
        base_rom = base_rom_entry.get()
        rom = rom_entry.get()
        project = project_entry.get()

        if base_rom and rom and project:
            # Update the GUI
            self.clear_console()
            self.disable_all_components()

            # Reset the progress bar
            self.progress_bar.set(0)

            thread = Thread(target=self._do_compile_help, args=(project, base_rom, rom))
            thread.start()

    def _do_compile_help(self, project, base_rom, rom):
        try:
            compile_project(project, base_rom, rom, progress_bar=self.progress_bar)
        except Exception as inst:
            log.exception("Error")

        self.progress_bar.set(0)
        self.enable_all_components()

    def do_upgrade(self, rom_entry, project_entry):
        rom = rom_entry.get()
        project = project_entry.get()

        if rom and project:
            # Update the GUI
            self.clear_console()
            self.disable_all_components()

            self.progress_bar.set(0)
            thread = Thread(target=self._do_upgrade_help, args=(rom, project))
            thread.start()

    def _do_upgrade_help(self, rom, project):
        try:
            upgrade_project(project_path=project, base_rom_filename=rom, progress_bar=self.progress_bar)
        except Exception as inst:
            log.exception("Error")

        self.progress_bar.set(0)
        self.enable_all_components()

    def do_decompile_script(self, rom_entry, project_entry):
        rom = rom_entry.get()
        project = project_entry.get()

        if rom and project:
            # Update the GUI
            self.clear_console()
            self.disable_all_components()
            self.progress_bar.cycle_animation()

            thread = Thread(target=self._do_decompile_script_help, args=(rom, project))
            thread.start()

    def _do_decompile_script_help(self, rom, project):
        try:
            decompile_script(rom_filename=rom, project_path=project, progress_bar=self.progress_bar)
        except Exception as inst:
            log.exception("Error")

        self.progress_bar.stop_cycle_animation()
        self.enable_all_components()

    def main(self):
        self.create_gui()
        self.root.mainloop()

    def create_gui(self):
        self.root = Tk()
        if self.preferences["title"]:
            self.root.wm_title(get_fun_title() + " " + information.VERSION)
        else:
            self.root.wm_title("CoilSnake " + information.VERSION)

        self.create_menubar()

        notebook = ttk.Notebook(self.root)

        decompile_frame = self.create_decompile_frame(notebook)
        notebook.add(decompile_frame, text="Decompile")

        compile_frame = self.create_compile_frame(notebook)
        notebook.add(compile_frame, text="Compile")

        upgrade_frame = self.create_upgrade_frame(notebook)
        notebook.add(upgrade_frame, text="Upgrade")

        decompile_script_frame = self.create_decompile_script_frame(notebook)
        notebook.add(decompile_script_frame, text="Decompile Script")

        notebook.pack(fill=BOTH, expand=1)

        progress_bar_component = ttk.Progressbar(self.root, orient=HORIZONTAL, mode='determinate')
        progress_bar_component.pack(fill=BOTH, expand=1)
        self.progress_bar = GuiProgressBar(progress_bar_component)

        console_frame = Frame(self.root)
        scrollbar = Scrollbar(console_frame)
        self.console = Text(console_frame, width=80, height=8)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.console.pack(fill=X)
        scrollbar.config(command=self.console.yview)
        self.console.config(yscrollcommand=scrollbar.set)
        console_frame.pack(fill=X, expand=1)

        class StdoutRedirector(object):
            def __init__(self, textarea):
                self.textarea = textarea

            def write(self, str):
                self.textarea.insert(END, str)
                self.textarea.see(END)

            def flush(self):
                pass

        self.console_stream = StdoutRedirector(self.console)
        sys.stdout = self.console_stream
        sys.stderr = self.console_stream

        setup_logging(quiet=False, verbose=False)

    def create_menubar(self):
        menubar = Menu(self.root)

        # Preferences pulldown menu
        prefMenu = Menu(menubar, tearoff=0)
        prefMenu.add_command(label="Emulator Executable",
                             command=self.set_emulator_exe)
        menubar.add_cascade(label="Preferences", menu=prefMenu)

        # Tools pulldown menu
        toolsMenu = Menu(menubar, tearoff=0)
        toolsMenu.add_command(label="Expand ROM to 32 MBit",
                              command=partial(gui_util.expand_rom, self.root))
        toolsMenu.add_command(label="Expand ROM to 48 MBit",
                              command=partial(gui_util.expand_rom_ex, self.root))
        toolsMenu.add_command(label="Add Header to ROM",
                              command=partial(gui_util.add_header_to_rom, self.root))
        toolsMenu.add_command(label="Remove Header from ROM",
                              command=partial(gui_util.strip_header_from_rom, self.root))
        toolsMenu.add_command(label="Extract EarthBound Dialogue to Project",
                              command=self.do_decompile_script)
        menubar.add_cascade(label="Tools", menu=toolsMenu)

        # Help menu
        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.about_menu)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def create_decompile_frame(self, notebook):
        self.decompile_fields = dict()

        decompile_frame = ttk.Frame(notebook)
        self.add_title_label_to_frame(text="Decompile a ROM to create a new project.", frame=decompile_frame)

        profile_selector_init = self.add_profile_selector_to_frame(frame=decompile_frame,
                                                                   tab="decompile",
                                                                   fields=self.decompile_fields)

        input_rom_entry = self.add_rom_fields_to_frame(name="ROM", frame=decompile_frame)
        self.decompile_fields["rom"] = input_rom_entry
        project_entry = self.add_project_fields_to_frame(name="Output Directory", frame=decompile_frame)
        self.decompile_fields["output_directory"] = project_entry

        profile_selector_init()

        def decompile_tmp():
            self.do_decompile(input_rom_entry, project_entry)

        decompile_button = Button(decompile_frame, text="Decompile", command=decompile_tmp)
        decompile_button.pack(fill=BOTH, expand=1)
        self.components.append(decompile_button)

        return decompile_frame

    def create_compile_frame(self, notebook):
        self.compile_fields = dict()

        compile_frame = ttk.Frame(notebook)
        self.add_title_label_to_frame(text="Compile a project to create a new ROM.", frame=compile_frame)

        profile_selector_init = self.add_profile_selector_to_frame(frame=compile_frame,
                                                                   tab="compile",
                                                                   fields=self.compile_fields)

        base_rom_entry = self.add_rom_fields_to_frame(name="Base ROM", frame=compile_frame)
        self.compile_fields["base_rom"] = base_rom_entry
        project_entry = self.add_project_fields_to_frame(name="Project", frame=compile_frame)
        self.compile_fields["project"] = project_entry
        output_rom_entry = self.add_rom_fields_to_frame(name="Output ROM", frame=compile_frame)
        self.compile_fields["output_rom"] = output_rom_entry

        profile_selector_init()

        def compile_tmp():
            self.do_compile(project_entry, base_rom_entry, output_rom_entry)

        compile_button = Button(compile_frame, text="Compile", command=compile_tmp)
        compile_button.pack(fill=BOTH, expand=1)
        self.components.append(compile_button)

        return compile_frame

    def create_upgrade_frame(self, notebook):
        upgrade_frame = ttk.Frame(notebook)
        self.add_title_label_to_frame(text="Upgrade a project created using an older version of CoilSnake.",
                                       frame=upgrade_frame)

        rom_entry = self.add_rom_fields_to_frame(name="Base ROM", frame=upgrade_frame)
        project_entry = self.add_project_fields_to_frame(name="Project", frame=upgrade_frame)

        def upgrade_tmp():
            self.do_upgrade(rom_entry, project_entry)

        self.upgrade_button = Button(upgrade_frame, text="Upgrade", command=upgrade_tmp)
        self.upgrade_button.pack(fill=BOTH, expand=1)
        self.components.append(self.upgrade_button)

        return upgrade_frame

    def create_decompile_script_frame(self, notebook):
        decompile_script_frame = ttk.Frame(notebook)
        self.add_title_label_to_frame(text="Decompile a ROM's script to an already existing project.",
                                      frame=decompile_script_frame)

        input_rom_entry = self.add_rom_fields_to_frame(name="ROM", frame=decompile_script_frame)
        project_entry = self.add_project_fields_to_frame(name="Project", frame=decompile_script_frame)

        def decompile_script_tmp():
            self.do_decompile_script(input_rom_entry, project_entry)

        button = Button(decompile_script_frame, text="Decompile Script", command=decompile_script_tmp)
        button.pack(fill=BOTH, expand=1)
        self.components.append(button)

        return decompile_script_frame

    def add_title_label_to_frame(self, text, frame):
        Label(frame, text=text, justify=CENTER, height=2).pack(fill=BOTH, expand=1)

    def add_profile_selector_to_frame(self, frame, tab, fields):
        profile_frame = ttk.Frame(frame)

        Label(profile_frame, text="Profile:", width=13).pack(side=LEFT, fill=BOTH, expand=1)

        def tmp_select(profile_name):
            for field_id in fields:
                set_entry_text(entry=fields[field_id],
                               text=self.preferences.get_profile_value(tab, profile_name, field_id))

        profile_var = StringVar(profile_frame)

        profile = OptionMenu(profile_frame, profile_var, "", command=tmp_select)
        profile["width"] = 26
        profile.pack(side=LEFT, fill=BOTH, expand=1)
        self.components.append(profile)

        def tmp_reload_options(selected_profile_name=None):
            profile["menu"].delete(0, END)
            for profile_name in sorted(self.preferences.get_profiles(tab)):
                if not selected_profile_name:
                    selected_profile_name = profile_name
                profile["menu"].add_command(label=profile_name,
                                            command=Tkinter._setit(profile_var, profile_name, tmp_select))
            profile_var.set(selected_profile_name)
            tmp_select(selected_profile_name)

        def tmp_new():
            profile_name = tkSimpleDialog.askstring("New Profile Name", "Specify the name of the new profile.")
            if profile_name:
                self.preferences.add_profile(tab, profile_name)
                tmp_reload_options(profile_name)
                self.preferences.save()

        def tmp_save():
            profile_name = profile_var.get()
            for field_id in fields:
                self.preferences.set_profile_value(tab, profile_name, field_id, fields[field_id].get())
            self.preferences.save()

        def tmp_delete():
            if self.preferences.count_profiles(tab) <= 1:
                tkMessageBox.showerror(parent=self.root,
                                       title="Error",
                                       message="Cannot delete the only profile.")
            else:
                self.preferences.delete_profile(tab, profile_var.get())
                tmp_reload_options()
                self.preferences.save()

        button = Button(profile_frame, text="Save", width=5, command=tmp_save)
        button.pack(side=LEFT, fill=BOTH, expand=1)
        self.components.append(button)

        button = Button(profile_frame, text="Delete", width=5, command=tmp_delete)
        button.pack(side=LEFT, fill=BOTH, expand=1)
        self.components.append(button)

        button = Button(profile_frame, text="New", width=5, command=tmp_new)
        button.pack(side=LEFT, fill=BOTH, expand=1)
        self.components.append(button)

        profile_frame.pack()

        return tmp_reload_options

    def add_rom_fields_to_frame(self, name, frame):
        rom_frame = ttk.Frame(frame)

        Label(rom_frame, text="{}:".format(name), width=13, justify=RIGHT).pack(side=LEFT, fill=BOTH, expand=1)
        rom_entry = Entry(rom_frame, width=30)
        rom_entry.pack(side=LEFT, fill=BOTH, expand=1)
        self.components.append(rom_entry)

        def browse_tmp():
            browse_for_rom(self.root, rom_entry)

        def run_tmp():
            self.run_rom(rom_entry)

        button = Button(rom_frame, text="Browse...", command=browse_tmp, width=6)
        button.pack(side=LEFT, fill=BOTH, expand=1)
        self.components.append(button)

        button = Button(rom_frame, text="Run", command=run_tmp, width=5)
        button.pack(side=LEFT, fill=BOTH, expand=1)
        self.components.append(button)

        button = Button(rom_frame, text="", width=5, state=DISABLED, takefocus=False, border=0)
        button.pack(side=LEFT, fill=BOTH, expand=1)
        button.lower()

        rom_frame.pack()

        return rom_entry

    def add_project_fields_to_frame(self, name, frame):
        project_frame = ttk.Frame(frame)

        Label(project_frame, text="{}:".format(name), width=13, justify=RIGHT).pack(side=LEFT)
        project_entry = Entry(project_frame, width=30)
        project_entry.pack(side=LEFT, fill=BOTH, expand=1)
        self.components.append(project_entry)

        def browse_tmp():
            browse_for_project(self.root, project_entry, save=True)

        def open_tmp():
            open_folder(project_entry)

        def edit_tmp():
            self.edit_project(project_entry)

        button = Button(project_frame, text="Browse...", command=browse_tmp, width=6)
        button.pack(side=LEFT, fill=BOTH, expand=1)
        self.components.append(button)

        button = Button(project_frame, text="Open", command=open_tmp, width=5)
        button.pack(side=LEFT, fill=BOTH, expand=1)
        self.components.append(button)

        button = Button(project_frame, text="Edit", command=edit_tmp, width=5)
        button.pack(side=LEFT, fill=BOTH, expand=1)
        self.components.append(button)

        project_frame.pack()

        return project_entry


def main():
    gui = CoilSnakeGui()
    sys.exit(gui.main())