import os
import shutil
import subprocess

import sublime
import sublime_plugin

# List of possible names the clang-format binary may have
if os.name == 'nt':
    FORMATTERS = ['clang-format.bat', 'clang-format.exe']
else:
    FORMATTERS = ['clang-format']

# List of languages supported for use with clang-format
LANGUAGES = ['C', 'C++', 'Objective-C', 'Objective-C++', 'Java']

def is_supported_language(view):
    """
    Check if the syntax of the given view is of a supported language.
    """
    (syntax, _) = os.path.splitext(view.settings().get('syntax'))
    supported = any(syntax.endswith(lang) for lang in LANGUAGES)

    return supported and bool(view.file_name())

def get_project_setting(setting_key):
    """
    Load a project setting from the active window, with environment variable expansion for string
    settings.
    """
    project_data = sublime.active_window().project_data()
    if not project_data or ('settings' not in project_data):
        return None

    settings = project_data['settings']
    if 'clang_format' not in project_data['settings']:
        return None

    settings = settings['clang_format']
    if setting_key not in settings:
        return None

    setting = settings[setting_key]

    if isinstance(setting, str):
        return os.path.expandvars(setting)

    return setting

def find_binary(directory, binaries):
    """
    Search for one of a list of binaries in the given directory or on the system PATH. Return the
    first valid binary that is found.
    """
    is_directory = lambda d: d and os.path.isdir(d) and os.access(d, os.R_OK)
    is_binary = lambda f: f and os.path.isfile(f) and os.access(f, os.X_OK)

    # First search through the given directory for any of the binaries
    for binary in (binaries if is_directory(directory) else []):
        binary = os.path.join(directory, binary)
        if is_binary(binary):
            return binary

    # Then fallback onto the system PATH
    for binary in binaries:
        binary = shutil.which(binary)
        if is_binary(binary):
            return binary

    return None

def execute_command(command, working_directory, stdin=None):
    """
    Execute a command list in the given working directory, optionally piping in an input string.
    Returns the standard output of the command, or None if an error occurred.
    """
    startup_info = None

    # On Windows, prevent a command prompt from showing
    if os.name == 'nt':
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    try:
        encoding = 'utf-8'

        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=working_directory,
            startupinfo=startup_info,
        )

        if stdin:
            stdin = stdin.encode(encoding)

        (stdout, stderr) = process.communicate(input=stdin)

        if stderr:
            sublime.error_message('Error: ' + stderr.decode(encoding))
        elif stdout:
            return stdout.decode(encoding)

    except Exception as ex:
        sublime.error_message('Exception: ' + str(ex))

    return None

class FormatFileCommand(sublime_plugin.TextCommand):
    """
    Command to run clang-format on a file. If any selections are active, only those selections are
    formatted.

    This plugin by default loads clang-format from the system PATH. But because Sublime doesn't
    source ~/.zshrc or ~/.bashrc, any PATH changes made there will not be noticed. So, users may set
    "clang_format_directory" in their project's settings, and that directory is used instead of
    PATH. Example:

        {
            "folders": [],
            "settings": {
                "clang_format": {
                    "path": "$HOME/workspace/tools",
                }
            }
        }

    Any known environment variables in the setting's value will be expanded.
    """
    def __init__(self, *args, **kwargs):
        super(FormatFileCommand, self).__init__(*args, **kwargs)

        self.format_directory = get_project_setting('path')
        self.format = find_binary(self.format_directory, FORMATTERS)

    def run(self, edit, ignore_selections=False):
        command = [self.format, '-assume-filename', self.view.file_name()]

        if not ignore_selections:
            for region in [r for r in self.view.sel() if not r.empty()]:
                command.extend(['-offset', str(region.begin())])
                command.extend(['-length', str(region.size())])

        working_directory = os.path.dirname(self.view.file_name())

        region = sublime.Region(0, self.view.size())
        contents = self.view.substr(region)

        contents = execute_command(command, working_directory, stdin=contents)

        if contents:
            self.view.replace(edit, region, contents)

    def is_enabled(self):
        return is_supported_language(self.view)

    def is_visible(self):
        format_directory = get_project_setting('path')

        if format_directory != self.format_directory:
            self.format_directory = format_directory
            self.format = find_binary(format_directory, FORMATTERS)

        return bool(self.format)

class FormatFileListener(sublime_plugin.EventListener):
    """
    Plugin to run FormatFileCommand on a file when it is saved. This plugin is disabled by default.
    It may be enabled by setting |on_save| to true in project settings. Example:

        {
            "folders": [],
            "settings": {
                "clang_format": {
                    "on_save": true,
                }
            }
        }

    Alternatively, setting |on_save| to a list of folder names allows selectively enabling this
    plugin for those folders only. Example:

        {
            "folders": [
                {
                    "name": "MyFolder",
                    "path": "path/to/folder"
                }
            ],
            "settings": {
                "clang_format": {
                    "on_save": [
                        "MyFolder"
                    ],
                }
            }
        }
    """
    def on_pre_save(self, view):
        if not is_supported_language(view):
            return
        elif not self._is_enabled(view):
            return

        view.run_command('format_file', {'ignore_selections': True})

    def _is_enabled(self, view):
        format_on_save = get_project_setting('on_save')

        if isinstance(format_on_save, bool):
            return format_on_save
        elif not isinstance(format_on_save, list):
            return False

        folder_data = self._get_folder_data(view.window())
        file_name = view.file_name()

        return any(file_name.startswith(folder_data[f]) for f in format_on_save)

    def _get_folder_data(self, window):
        """
        Get a dictionary of project folders mapping folder names to the full path to the folder.
        """
        project_variables = window.extract_variables()
        project_data = window.project_data()

        project_path = project_variables['project_path']
        folder_data = {}

        for folder in project_data['folders']:
            if ('name' in folder) and ('path' in folder):
                path = os.path.join(project_path, folder['path'])
                folder_data[folder['name']] = path

        return folder_data
