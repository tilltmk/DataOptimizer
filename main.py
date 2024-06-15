import os
import hashlib
from collections import defaultdict
import tkinter as tk
from tkinter import scrolledtext, ttk
import customtkinter as ctk
from CTkListbox import *
from tkinter.filedialog import askdirectory
import zipfile
import json

# Setzen des Standard-Themas
ctk.set_appearance_mode("System")

# Hashing-Funktion
def hash_file(filepath):
    hash_obj = hashlib.md5()
    with open(filepath, 'rb') as file:
        while chunk := file.read(8192):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

# Methode zum Erstellen einer Baumstruktur von Ordnern
def map_folder_structure(path):
    folder_tree = defaultdict(dict)
    for root, dirs, files in os.walk(path):
        # Entferne das Basisverzeichnis aus dem Pfad
        relative_root = os.path.relpath(root, path)
        folder_tree[relative_root] = {
            "dirs": sorted(dirs),
            "files": sorted(files)
        }
    return folder_tree

# Methode zum Berechnen des Prozentsatzes der übereinstimmenden Unterordner
def calculate_similarity_percentage(folder1, folder2):
    set1 = set(folder1.keys())
    set2 = set(folder2.keys())
    common_folders = set1 & set2
    if not set1 and not set2:
        return 100
    return len(common_folders) / min(len(set1), len(set2)) * 100

# Methode zum Überprüfen, ob die Anzahl der Unterordner ±25% gleich ist
def is_folder_count_similar(folder1, folder2):
    count1 = len(folder1)
    count2 = len(folder2)
    lower_bound = 0.75 * count1
    upper_bound = 1.25 * count1
    return lower_bound <= count2 <= upper_bound

# Methode zum Vergleichen der Baumstruktur zweier Ordner
def compare_folder_structures(tree1, tree2):
    similar_folders = []
    for folder in tree1:
        if folder in tree2 and tree1[folder] == tree2[folder]:
            similar_folders.append(folder)
    return similar_folders

# Klasse zum Finden von Duplikaten
class DuplicateFinder:
    def __init__(self):
        self.files_by_hash = {}
        self.files_by_size = {}
        self.files_by_name = {}
        self.files_by_date = {}

    def find_duplicates(self, folder, methods=["hash"]):
        index_file = os.path.join(folder, "index.json")
        if os.path.exists(index_file):
            with open(index_file, "r") as f:
                self.files_by_hash, self.files_by_size, self.files_by_name, self.files_by_date = json.load(f)
        else:
            for root, _, files in os.walk(folder):
                for file in files:
                    path = os.path.join(root, file)
                    if "hash" in methods:
                        file_key = hash_file(path)
                        self.files_by_hash.setdefault(file_key, []).append(path)
                    if "size" in methods:
                        file_key = os.path.getsize(path)
                        self.files_by_size.setdefault(file_key, []).append(path)
                    if "name" in methods:
                        file_key = file
                        self.files_by_name.setdefault(file_key, []).append(path)
                    if "date" in methods:
                        file_key = os.path.getmtime(path)
                        self.files_by_date.setdefault(file_key, []).append(path)

            with open(index_file, "w") as f:
                json.dump([self.files_by_hash, self.files_by_size, self.files_by_name, self.files_by_date], f)
        
        duplicates = {}
        if "hash" in methods:
            duplicates.update({hash: paths for hash, paths in self.files_by_hash.items() if len(paths) > 1})
        if "size" in methods:
            duplicates.update({size: paths for size, paths in self.files_by_size.items() if len(paths) > 1})
        if "name" in methods:
            duplicates.update({name: paths for name, paths in self.files_by_name.items() if len(paths) > 1})
        if "date" in methods:
            duplicates.update({date: paths for date, paths in self.files_by_date.items() if len(paths) > 1})
        
        return duplicates

class FolderManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Folder Manager")
        self.geometry("800x600")

        # Hinzufügen der Tabs
        self.tab_control = ctk.CTkTabview(self)
        self.tab_control.pack(expand=1, fill="both")

        self.create_folder_tab = self.tab_control.add("Verzeichnisse Erstellen")
        self.remove_duplicates_tab = self.tab_control.add("Duplikate Entfernen")
        self.file_size_tab = self.tab_control.add("Dateien Nach Größe")
        self.merge_folders_tab = self.tab_control.add("Ähnliche Ordner Verschmelzen")

        self.setup_create_folder_tab()
        self.setup_remove_duplicates_tab()
        self.setup_file_size_tab()
        self.setup_merge_folders_tab()

        self.is_night_mode = False
        self.setup_theme_switch_button()

    def setup_merge_folders_tab(self):
        label_frame = ctk.CTkFrame(self.merge_folders_tab)
        label_frame.pack(pady=10, padx=10, fill='x')

        label = ctk.CTkLabel(label_frame, text="Ziel Pfad:")
        label.pack(side=tk.LEFT, padx=5)

        self.merge_target_path_entry = ctk.CTkEntry(label_frame, width=400)
        self.merge_target_path_entry.pack(side=tk.LEFT, padx=5)

        browse_button = ctk.CTkButton(label_frame, text="Durchsuchen", fg_color="#FF0000", hover_color="#CC0000", text_color="#FFFFFF", command=self.browse_directory_merge)
        browse_button.pack(side=tk.LEFT, padx=5)

        button_frame = ctk.CTkFrame(self.merge_folders_tab)
        button_frame.pack(pady=10, padx=10, fill='x')

        scan_button = ctk.CTkButton(button_frame, text="Ähnliche Ordner Finden", fg_color="#FF0000", hover_color="#CC0000", text_color="#FFFFFF", command=self.scan_similar_folders)
        scan_button.pack(side=tk.LEFT, padx=5)

        merge_button = ctk.CTkButton(button_frame, text="Ausgewählte Verschmelzen", fg_color="#FF0000", hover_color="#CC0000", text_color="#FFFFFF", command=self.merge_selected_folders)
        merge_button.pack(side=tk.LEFT, padx=5)

        self.similar_folders_listbox = CTkListbox(self.merge_folders_tab, multiple_selection=True)
        self.similar_folders_listbox.pack(pady=10, padx=10, fill="both", expand=True)

    def browse_directory_merge(self):
        folder_selected = askdirectory()
        self.merge_target_path_entry.delete(0, tk.END)
        self.merge_target_path_entry.insert(0, folder_selected)

    def scan_similar_folders(self):
        target_path = self.merge_target_path_entry.get().strip()
        if not target_path:
            ctk.CTkMessageBox.show_warning(title="Warnung", message="Bitte geben Sie einen Ziel Pfad an.")
            return

        all_folders = [os.path.join(target_path, d) for d in os.listdir(target_path) if os.path.isdir(os.path.join(target_path, d))]

        folder_structures = {folder: map_folder_structure(folder) for folder in all_folders}
        similar_groups = []

        for i, folder1 in enumerate(all_folders):
            common_group = [folder1]
            for folder2 in all_folders[i + 1:]:
                if is_folder_count_similar(folder_structures[folder1], folder_structures[folder2]):
                    similarity = calculate_similarity_percentage(folder_structures[folder1], folder_structures[folder2])
                    if similarity >= 60:
                        common_group.append(folder2)
            if len(common_group) > 1:
                similar_groups.append(common_group)

        self.similar_folders_listbox.delete(0, tk.END)
        for group in similar_groups:
            display_text = " <-> ".join(group)
            self.similar_folders_listbox.insert(tk.END, display_text)

    def merge_folders(self, folder1, folder2):
        for root, dirs, files in os.walk(folder2):
            relative_path = os.path.relpath(root, folder2)
            dest_path = os.path.join(folder1, relative_path)
            try:
                os.makedirs(dest_path, exist_ok=True)
            except OSError as e:
                self.output_terminal.insert(tk.END, f"Fehler beim Erstellen des Ordners {dest_path}: {e}\n")
                continue

            for file in files:
                src_file = os.path.join(root, file)
                dest_file = os.path.join(dest_path, file)
                try:
                    if not os.path.exists(dest_file):
                        os.rename(src_file, dest_file)
                        self.output_terminal.insert(tk.END, f"Verschoben: {src_file} -> {dest_file}\n")
                    else:
                        self.output_terminal.insert(tk.END, f"Übersprungen (Datei existiert bereits): {src_file}\n")
                except OSError as e:
                    self.output_terminal.insert(tk.END, f"Fehler beim Verschieben der Datei {src_file}: {e}\n")
            self.update_idletasks()

        try:
            os.rmdir(folder2)
            self.output_terminal.insert(tk.END, f"Gelöscht: {folder2}\n")
        except OSError as e:
            self.output_terminal.insert(tk.END, f"Ordner konnte nicht gelöscht werden (nicht leer oder keine Berechtigung): {folder2}\nFehler: {e}\n")
        self.update_idletasks()

    def merge_selected_folders(self):
        selected_items = self.similar_folders_listbox.curselection()
        if not selected_items:
            ctk.CTkMessageBox.show_warning(title="Warnung", message="Bitte wählen Sie Ordner zum Verschmelzen aus.")
            return

        for index in selected_items:
            display_text = self.similar_folders_listbox.get(index)
            folders = display_text.split(' <-> ')
            primary_folder = folders[0]
            for folder in folders[1:]:
                self.merge_folders(primary_folder, folder)

        ctk.CTkMessageBox.show_info(title="Info", message="Ordner wurden erfolgreich verschmolzen.")

    def setup_theme_switch_button(self):
        theme_switch_btn = ctk.CTkButton(self, text="Nacht/Tag Modus", fg_color="#FF0000", hover_color="#CC0000", text_color="#FFFFFF", command=self.toggle_theme)
        theme_switch_btn.pack(pady=10)

    def toggle_theme(self):
        self.is_night_mode = not self.is_night_mode
        if self.is_night_mode:
            ctk.set_appearance_mode("Dark")
            self.output_terminal.config(background='black', foreground='green')
            self.output_terminal_duplicates.config(background='black', foreground='green')
        else:
            ctk.set_appearance_mode("Light")
            self.output_terminal.config(background='white', foreground='black')
            self.output_terminal_duplicates.config(background='white', foreground='black')

    def browse_directory(self):
        folder_selected = askdirectory()
        self.base_path_entry.delete(0, tk.END)
        self.base_path_entry.insert(0, folder_selected)

    def browse_directory_target(self):
        folder_selected = askdirectory()
        self.target_path_entry.delete(0, tk.END)
        self.target_path_entry.insert(0, folder_selected)

    def browse_directory_size(self):
        folder_selected = askdirectory()
        self.size_scan_path_entry.delete(0, tk.END)
        self.size_scan_path_entry.insert(0, folder_selected)

    def setup_create_folder_tab(self):
        label_frame = ctk.CTkFrame(self.create_folder_tab)
        label_frame.pack(pady=10, padx=10, fill='x')

        label = ctk.CTkLabel(label_frame, text="Basis Pfad:")
        label.pack(side=tk.LEFT, padx=5)

        self.base_path_entry = ctk.CTkEntry(label_frame, width=400)
        self.base_path_entry.pack(side=tk.LEFT, padx=5)

        browse_button = ctk.CTkButton(label_frame, text="Durchsuchen", fg_color="#FF0000", hover_color="#CC0000", text_color="#FFFFFF", command=self.browse_directory)
        browse_button.pack(side=tk.LEFT, padx=5)

        self.folder_list_text = ctk.CTkTextbox(self.create_folder_tab, height=10, width=400, wrap='word')
        self.folder_list_text.pack(pady=10, padx=10, fill='both', expand=True)

        button_frame = ctk.CTkFrame(self.create_folder_tab)
        button_frame.pack(pady=10, padx=10, fill='x')

        create_button = ctk.CTkButton(button_frame, text="Verzeichnisse Erstellen", fg_color="#FF0000", hover_color="#CC0000", text_color="#FFFFFF", command=self.create_folders)
        create_button.pack(side=tk.LEFT, padx=5)

        self.progress_bar = ctk.CTkProgressBar(button_frame, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, padx=5, fill='x', expand=True)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(button_frame, text="0%")
        self.progress_label.pack(side=tk.LEFT, padx=5)

        terminal_frame = ctk.CTkFrame(self.create_folder_tab)
        terminal_frame.pack(pady=10, padx=10, fill='both', expand=True)

        self.output_terminal = scrolledtext.ScrolledText(terminal_frame, height=10, width=400, background='black', foreground='green', font=('Arial', 10, 'bold'))
        self.output_terminal.pack(pady=5, padx=5, fill='both', expand=True)

    def setup_remove_duplicates_tab(self):
        label_frame = ctk.CTkFrame(self.remove_duplicates_tab)
        label_frame.pack(pady=10, padx=10, fill='x')

        label = ctk.CTkLabel(label_frame, text="Ziel Pfad:")
        label.pack(side=tk.LEFT, padx=5)

        self.target_path_entry = ctk.CTkEntry(label_frame, width=400)
        self.target_path_entry.pack(side=tk.LEFT, padx=5)

        browse_button = ctk.CTkButton(label_frame, text="Durchsuchen", fg_color="#FF0000", hover_color="#CC0000", text_color="#FFFFFF", command=self.browse_directory_target)
        browse_button.pack(side=tk.LEFT, padx=5)

        button_frame = ctk.CTkFrame(self.remove_duplicates_tab)
        button_frame.pack(pady=10, padx=10, fill='x')

        scan_button = ctk.CTkButton(button_frame, text="Duplikate Finden", fg_color="#FF0000", hover_color="#CC0000", text_color="#FFFFFF", command=self.scan_duplicates)
        scan_button.pack(side=tk.LEFT, padx=5)

        self.duplicate_method_listbox = tk.Listbox(button_frame, selectmode=tk.MULTIPLE)
        for method in ["hash", "size", "name", "date"]:
            self.duplicate_method_listbox.insert(tk.END, method)
        self.duplicate_method_listbox.pack(side=tk.LEFT, padx=5)

        self.progress_bar_duplicates = ctk.CTkProgressBar(button_frame, mode='determinate')
        self.progress_bar_duplicates.pack(side=tk.LEFT, padx=5, fill='x', expand=True)
        self.progress_bar_duplicates.set(0)

        self.progress_label_duplicates = ctk.CTkLabel(button_frame, text="0%")
        self.progress_label_duplicates.pack(side=tk.LEFT, padx=5)

        terminal_frame = ctk.CTkFrame(self.remove_duplicates_tab)
        terminal_frame.pack(pady=10, padx=10, fill='both', expand=True)

        self.output_terminal_duplicates = scrolledtext.ScrolledText(terminal_frame, height=10, width=400, background='black', foreground='green', font=('Arial', 10, 'bold'))
        self.output_terminal_duplicates.pack(pady=5, padx=5, fill='both', expand=True)

    def setup_file_size_tab(self):
        label_frame = ctk.CTkFrame(self.file_size_tab)
        label_frame.pack(pady=10, padx=10, fill='x')

        label = ctk.CTkLabel(label_frame, text="Ziel Pfad:")
        label.pack(side=tk.LEFT, padx=5)

        self.size_scan_path_entry = ctk.CTkEntry(label_frame, width=400)
        self.size_scan_path_entry.pack(side=tk.LEFT, padx=5)

        browse_button = ctk.CTkButton(label_frame, text="Durchsuchen", fg_color="#FF0000", hover_color="#CC0000", text_color="#FFFFFF", command=self.browse_directory_size)
        browse_button.pack(side=tk.LEFT, padx=5)

        button_frame = ctk.CTkFrame(self.file_size_tab)
        button_frame.pack(pady=10, padx=10, fill='x')

        scan_button = ctk.CTkButton(button_frame, text="Dateien Scannen", fg_color="#FF0000", hover_color="#CC0000", text_color="#FFFFFF", command=self.scan_files_by_size)
        scan_button.pack(side=tk.LEFT, padx=5)

        self.progress_bar_files_by_size = ctk.CTkProgressBar(button_frame, mode='determinate', fg_color="#FF0000", progress_color="#CC0000", border_color="#FF0000")
        self.progress_bar_files_by_size.pack(side=tk.LEFT, padx=5, fill='x', expand=True)
        self.progress_bar_files_by_size.set(0)

        self.progress_label_files_by_size = ctk.CTkLabel(button_frame, text="0%")
        self.progress_label_files_by_size.pack(side=tk.LEFT, padx=5)

        self.size_var = tk.StringVar(value="MB")
        size_options = ttk.Combobox(button_frame, textvariable=self.size_var, values=["Bytes", "KB", "MB", "GB"])
        size_options.pack(side=tk.LEFT, padx=5)

        self.files_tree = ttk.Treeview(self.file_size_tab, columns=("filepath", "size"), show="headings")
        self.files_tree.heading("filepath", text="Dateipfad")
        self.files_tree.heading("size", text="Größe")
        self.files_tree.pack(pady=10, padx=10, fill='both', expand=True)

        button_option_frame = ctk.CTkFrame(self.file_size_tab)
        button_option_frame.pack(pady=10, padx=10, fill='x')

        compress_button = ctk.CTkButton(button_option_frame, text="Zusammenfassen und Komprimieren", fg_color="#FF0000", hover_color="#CC0000", text_color="#FFFFFF", command=self.compress_files)
        compress_button.pack(side=tk.LEFT, padx=5)

        delete_button = ctk.CTkButton(button_option_frame, text="Löschen (permanent)", fg_color="#FF0000", hover_color="#CC0000", text_color="#FFFFFF", command=self.delete_files_permanently)
        delete_button.pack(side=tk.LEFT, padx=5)

    def create_folders(self):
        base_path = self.base_path_entry.get().strip()
        if not base_path:
            ctk.CTkMessageBox.show_warning(title="Warnung", message="Bitte geben Sie einen Basis Pfad an.")
            return

        folder_list = self.folder_list_text.get("1.0", tk.END).strip().split('\n')
        total_folders = len(folder_list)
        self.progress_bar.set(0)

        for i, folder in enumerate(folder_list):
            folder_path = os.path.join(base_path, folder.strip())
            os.makedirs(folder_path, exist_ok=True)
            progress = (i + 1) / total_folders * 100
            self.progress_bar.set(progress / 100)
            self.progress_label.configure(text=f"{progress:.0f}%")
            self.update_idletasks()
            self.output_terminal.insert(tk.END, f"Erstellt: {folder_path}\n")

    def scan_duplicates(self):
        target_path = self.target_path_entry.get().strip()
        if not target_path:
            ctk.CTkMessageBox.show_warning(title="Warnung", message="Bitte geben Sie einen Ziel Pfad an.")
            return

        methods = [self.duplicate_method_listbox.get(i) for i in self.duplicate_method_listbox.curselection()]
        if not methods:
            ctk.CTkMessageBox.show_warning(title="Warnung", message="Bitte wählen Sie mindestens eine Methode zum Finden von Duplikaten aus.")
            return

        duplicate_finder = DuplicateFinder()
        duplicates = duplicate_finder.find_duplicates(target_path, methods)
        total_files = sum(len(paths) for paths in duplicates.values())
        self.progress_bar_duplicates.set(0)

        progress_count = 0
        for file_key, paths in duplicates.items():
            self.output_terminal_duplicates.insert(tk.END, f"Duplikate für {file_key}:\n")
            for path in paths:
                self.output_terminal_duplicates.insert(tk.END, f"  {path}\n")
                progress_count += 1
                progress = (progress_count / total_files) * 100
                self.progress_bar_duplicates.set(progress / 100)
                self.progress_label_duplicates.configure(text=f"{progress:.0f}%")
                self.update_idletasks()

    def scan_files_by_size(self):
        target_path = self.size_scan_path_entry.get().strip()
        if not target_path:
            ctk.CTkMessageBox.show_warning(title="Warnung", message="Bitte geben Sie einen Ziel Pfad an.")
            return

        self.files_tree.delete(*self.files_tree.get_children())
        files_with_sizes = []
        file_count = 0
        for root, _, files in os.walk(target_path):
            file_count += len(files)
            
        progress_count = 0
        for root, _, files in os.walk(target_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(file_path)
                    files_with_sizes.append((file_path, size))
                except OSError as e:
                    print(f"Fehler beim Abrufen der Dateigröße: {e}")

                progress_count += 1
                progress = (progress_count / file_count) * 100
                self.progress_bar_files_by_size.set(progress / 100)
                self.progress_label_files_by_size.configure(text=f"{progress:.0f}%")
                self.update_idletasks()

        for file_path, size in sorted(files_with_sizes, key=lambda x: x[1], reverse=True):
            display_size = self.convert_size(size)
            self.files_tree.insert("", "end", values=(file_path, display_size))

    def convert_size(self, size):
        size_unit = self.size_var.get()
        if size_unit == "KB":
            return f"{size / 1024:.2f} KB"
        elif size_unit == "MB":
            return f"{size / (1024 * 1024):.2f} MB"
        elif size_unit == "GB":
            return f"{size / (1024 * 1024 * 1024):.2f} GB"
        else:
            return f"{size} Bytes"

    def compress_files(self):
        selected_files = [self.files_tree.item(item)['values'][0] for item in self.files_tree.selection()]
        if not selected_files:
            ctk.CTkMessageBox.show_warning(title="Warnung", message="Bitte wählen Sie Dateien zum Komprimieren aus.")
            return

        zip_filename = "compressed_files.zip"
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for file in selected_files:
                zipf.write(file, os.path.basename(file))

        ctk.CTkMessageBox.show_info(title="Info", message=f"Erfolgreich komprimiert in {zip_filename}.")

    def delete_files_permanently(self):
        selected_files = [self.files_tree.item(item)['values'][0] for item in self.files_tree.selection()]
        if not selected_files:
            ctk.CTkMessageBox.show_warning(title="Warnung", message="Bitte wählen Sie Dateien zum Löschen aus.")
            return

        for file in selected_files:
            try:
                os.remove(file)
            except OSError as e:
                print(f"Fehler beim Löschen der Datei: {e}")

        ctk.CTkMessageBox.show_info(title="Info", message="Erfolgreich gelöscht.")

if __name__ == "__main__":
    app = FolderManagerApp()
    app.mainloop()
