import enum
import os
import shutil
import subprocess

import sublime
import sublime_plugin


@enum.unique
class Formatter(enum.Enum):
    """
    Formatters supported by this plugin.
    """
    ClangFormat = enum.auto()
    Prettier = enum.auto()
    AutoPep8 = enum.auto()

    def __str__(self):
        if self is Formatter.ClangFormat:
            return 'clang-format'
        elif self is Formatter.Prettier:
            return 'prettier'
        elif self is Formatter.AutoPep8:
            return 'autopep8'


# List of possible names the formatters may have.
if os.name == 'nt':
    FORMATTERS = {
        Formatter.ClangFormat: ['clang-format.bat', 'clang-format.exe'],
        Formatter.Prettier: ['prettier.cmd', 'prettier.exe'],
        Formatter.AutoPep8: ['autopep8.cmd', 'autopep8.exe'],
    }
else:
    FORMATTERS = {
        Formatter.ClangFormat: ['clang-format'],
        Formatter.Prettier: ['prettier'],
        Formatter.AutoPep8: ['autopep8'],
    }

# List of languages supported for use with the formatters.
LANGUAGES = {
    Formatter.ClangFormat: ['C', 'C++', 'Objective-C', 'Objective-C++', 'Java'],
    Formatter.Prettier: ['JavaScript', 'JavaScript (Babel)'],
    Formatter.AutoPep8: ['Python'],
}


def is_supported_language(formatter, view):
    """
    Check if the syntax of the given view is of a supported language for the given formatter.
    """
    (syntax, _) = os.path.splitext(view.settings().get('syntax'))
    supported = any(syntax.endswith(lang) for lang in LANGUAGES[formatter])

    return supported and bool(view.file_name())


def formatter_type(view):
    """
    Return the type of formatter to use for the given view, if any.
    """
    if is_supported_language(Formatter.ClangFormat, view):
        return Formatter.ClangFormat
    elif is_supported_language(Formatter.Prettier, view):
        return Formatter.Prettier
    elif is_supported_language(Formatter.AutoPep8, view):
        return Formatter.AutoPep8
    return None


def get_project_setting(formatter, setting_key):
    """
    Load a project setting from the active window, with environment variable expansion for string
    settings.
    """
    project_data = sublime.active_window().project_data()
    if not project_data or ('settings' not in project_data):
        return None

    settings = project_data['settings']
    if 'format' not in project_data['settings']:
        return None

    settings = settings['format']

    if formatter:
        formatter = str(formatter)
        if formatter not in settings:
            return None

        settings = settings[formatter]

    if setting_key not in settings:
        return None

    setting = settings[setting_key]

    if isinstance(setting, str):
        return os.path.expandvars(setting)

    return setting


def find_binary(formatter, directory, view):
    """
    Search for one of a list of binaries in the given directory or on the system PATH. Return the
    first valid binary that is found.
    """
    binaries = FORMATTERS[formatter]

    is_directory = lambda d: d and os.path.isdir(d) and os.access(d, os.R_OK)
    is_binary = lambda f: f and os.path.isfile(f) and os.access(f, os.X_OK)

    # First search through the given directory for any of the binaries.
    for binary in (binaries if is_directory(directory) else []):
        binary = os.path.join(directory, binary)
        if is_binary(binary):
            return binary

    # Then fallback onto the system PATH.
    for binary in binaries:
        binary = shutil.which(binary)
        if is_binary(binary):
            return binary

    # Otherwise, fallback onto formatter-specific common locations.
    if formatter is Formatter.Prettier:
        for project_path in view.window().folders():
            if view.file_name().startswith(project_path):
                project_path = os.path.join(project_path, 'node_modules', '.bin')
                break
        else:
            project_path = None

        for binary in (binaries if is_directory(project_path) else []):
            binary = os.path.join(project_path, binary)
            if is_binary(binary):
                return binary

    return None


def execute_command(command, working_directory, stdin=None, extra_environment=None):
    """
    Execute a command list in the given working directory, optionally piping in an input string.
    Returns the standard output of the command, or None if an error occurred.
    """
    environment = os.environ.copy()
    startup_info = None

    # On Windows, prevent a command prompt from showing.
    if os.name == 'nt':
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    if extra_environment:
        for (key, value) in extra_environment.items():
            environment[key] = os.path.expandvars(value)

    try:
        encoding = 'utf-8'

        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startup_info,
            cwd=working_directory,
            env=environment,
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
    Command to format a file on demand. If any selections are active, only those selections are
    formatted.

    This plugin by default loads formatter binaries from the system $PATH. But because Sublime does
    not source ~/.zshrc or ~/.bashrc, any $PATH changes made there will not be noticed. So, users
    may set "path" settings for each formatter in their project's settings, and that directory is
    used instead of $PATH. Example:

        {
            "folders": [],
            "settings": {
                "format": {
                    "clang-format": {
                        "path": "$HOME/workspace/tools",
                    },
                    "prettier": {
                        "path": "$HOME/workspace/tools",
                    },
                }
            }
        }

    Any known environment variables in the settings' values will be expanded.
    """

    def __init__(self, *args, **kwargs):
        super(FormatFileCommand, self).__init__(*args, **kwargs)

        self.environment = get_project_setting(None, 'environment')
        self.formatter = formatter_type(self.view)
        self.binary = None

        if self.formatter is not None:
            path = get_project_setting(self.formatter, 'path')
            self.binary = find_binary(self.formatter, path, self.view)

    def run(self, edit, ignore_selections=False):
        if ignore_selections or (len(self.view.sel()) == 0):
            selected_regions = lambda: []
        else:
            selected_regions = lambda: [region for region in self.view.sel() if not region.empty()]

        command = [self.binary]

        if self.formatter is Formatter.ClangFormat:
            command.extend(['-assume-filename', self.view.file_name()])

            for region in selected_regions():
                command.extend(['-offset', str(region.begin())])
                command.extend(['-length', str(region.size())])

        elif self.formatter is Formatter.Prettier:
            command.extend(['--parser', 'babel'])

            for region in selected_regions():
                command.extend(['--range-start', str(region.begin())])
                command.extend(['--range-end', str(region.end())])
                break

        elif self.formatter is Formatter.AutoPep8:
            for region in selected_regions():
                (begin, _) = self.view.rowcol(region.begin())
                (end, _) = self.view.rowcol(region.end())
                command.extend(['--line-range', str(begin + 1), str(end + 1)])
                break

            command.append('-')

        working_directory = os.path.dirname(self.view.file_name())

        region = sublime.Region(0, self.view.size())
        contents = self.view.substr(region)

        contents = execute_command(
            command, working_directory, stdin=contents, extra_environment=self.environment)

        if contents:
            position = self.view.viewport_position()
            self.view.replace(edit, region, contents)

            # This is a bit of a hack. If the selection extends horizontally beyond the viewport,
            # the call to view.replace sometimes scrolls off to the right. This resets the viewport
            # position, but first sets the position to (0, 0) - otherwise the 'real' invocation
            # doesn't seem to have any effect.
            # https://github.com/sublimehq/sublime_text/issues/2560
            self.view.set_viewport_position((0, 0), False)
            self.view.set_viewport_position(position, False)

    def is_enabled(self):
        return self.binary is not None

    def is_visible(self):
        return self.binary is not None


class FormatFileListener(sublime_plugin.EventListener):
    """
    Plugin to run FormatFileCommand on a file when it is saved. This plugin is disabled by default.
    It may be enabled by setting |on_save| to true in each project settings. Example:

        {
            "folders": [],
            "settings": {
                "format": {
                    "clang-format": {
                        "on_save": true
                    },
                    "prettier": {
                        "on_save": false
                    }
                    "autopep8": {
                        "on_save": true
                    }
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
                "format": {
                    "clang-format": {
                        "on_save": [
                            "MyFolder"
                        ]
                    }
                }
            }
        }
    """

    def on_pre_save(self, view):
        formatter = formatter_type(view)

        if formatter is None:
            return
        elif not self._is_enabled(formatter, view):
            return

        view.run_command('format_file', {'ignore_selections': True})

    def _is_enabled(self, formatter, view):
        format_on_save = get_project_setting(formatter, 'on_save')

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
