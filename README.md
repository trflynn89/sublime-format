# Clang Format for Sublime Text 3

Sublime Text plugin for running [clang-format](https://clang.llvm.org/docs/ClangFormat.html) on
source files.

## Usage

Once installed, this plugin may be used via the Command Palette or right-click context menu. To
format a file via the Command Palette, open the palette and enter "Format File". Similarly,
right-click on a file to see "Format File" in the context menu.

By default, the entire file will be formatted. However, if any selections are active, only those
selections will be formatted.

This plugin may also be used to run `clang-format` when a file is saved. See [Settings](#Settings).

## Settings

This plugin may be configured via [project settings](https://www.sublimetext.com/docs/3/projects.html).
The following settings may be used:

```json
{
    "folders": [],
    "settings": {
        "clang_format": {
            "path": "$HOME/workspace/tools",
            "on_save": true,
        }
    }
}
```

* `path` - The directory containing the `clang-format` binary to use. By default, the plugin will
  search the `$PATH` for the binary.
* `on_save` - Configure the plugin to run `clang-format` when a file is saved. Disabled by default.
  May be set to `true`, `false`, or an array of project folder names for which the setting should be
  enabled.

For example, to enable the `on_save` setting for a specific folder:

```json
   "folders": [
        {
            "name": "MyFolder",
            "path": "path/to/folder"
        },
        {
            "name": "OtherFolder",
            "path": "path/to/other"
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
```
