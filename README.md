# Code Formatting Plugin for Sublime Text 3 & 4

Sublime Text plugin for formatting code. Supports the following formatters:
* [autopep8](https://github.com/hhatto/autopep8)
* [clang-format](https://clang.llvm.org/docs/ClangFormat.html)
* [gn](https://gn.googlesource.com/gn)
* [prettier](https://prettier.io/)
* [rustfmt](https://docs.rs/rustfmt/latest/rustfmt/)

## Usage

Once installed, this plugin may be used via the Command Palette or right-click context menu. To
format a file via the Command Palette, open the palette and enter "Format File". Similarly,
right-click on a file to see "Format File" in the context menu.

By default, the entire file will be formatted. However, if any selections are active, and the
formatter supports formatting selections, only those selections will be formatted.

Note: `autopep8` and `prettier` only support formatting a single selection. If there are multiple
selections added, only the first non-empty selection will be formatted.

This plugin may also be used to format code automatically when a file is saved. See
[Settings](#Settings).

## Settings

This plugin may be configured via [project settings](https://www.sublimetext.com/docs/3/projects.html).
The following settings may be used:

```json
{
    "folders": [],
    "settings": {
        "format": {
            "environment": {
                "KEY": "VALUE"
            },
            "autopep8": {
                "path": "$HOME/workspace/tools",
                "on_save": true
            },
            "clang-format": {
                "path": "$HOME/workspace/tools",
                "on_save": true
            },
            "gn": {
                "path": "$HOME/workspace/tools",
                "on_save": true
            },
            "prettier": {
                "path": "$HOME/workspace/tools",
                "on_save": false
            },
            "rustfmt": {
                "path": "$HOME/workspace/tools",
                "on_save": true
            }
        }
    }
}
```

* `environment` - Extra environment variables to set before running a formatter. Each environment
  variable may contain other environment variables in their value, such as `$HOME`.
* `{formatter}/path` - The directory containing the binary to use for that formatter. By default,
  the plugin will search the `$PATH` for the binary. May contain environment variables in the path,
  such as `$HOME`.
* `{formatter}/on_save` - Configure the plugin to automatically format a file with a formatter when
  it is saved. Disabled by default. May be set to `true`, `false`, or an array of project folder
  names for which the setting should be enabled.

For example, to enable the `on_save` setting for a specific folder:

```json
{
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
        "format": {
            "clang-format": {
                "on_save": [
                    "MyFolder"
                ]
            }
        }
    }
}
```
