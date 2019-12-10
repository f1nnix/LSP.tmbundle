# Language server protocol support for TextMate 2

A brief implementation of LSP client using simple aysnc proxy server.

WIP, early pre-alfa. Yet not usable!

Currenly working:

* Completions

Based on [PurpleMyst/sansio-lsp-client](https://github.com/PurpleMyst/sansio-lsp-client).

## Python interpreter

As TextMate doesn't ship Python distribution with itself, it's need to specify prefered Python executable path to launch LSP proxy (`proxy/main.py`) and/or run it manually in desired venv.

## How it works

Due to TextMate can't run async code in command bundle, we need to run separate async server to communicate with Language server.

Here's brief scheme, how LSP plugin handles completion requests:

```
+-----------+
| TextMate  |
+-----------+
 |         ▲
 | (1) TextMate sends Completion request via socket 1
 |         |
 |         | (4) Textmate gets response via socket 1 and runs actions
 ▼         |
+------------------+
| LSP Proxy Client |
+------------------+
 |           ▲
 |           | (3) Proxy recieves response for (2) and sends via socket 2
 |           |
 | (2) Proxy recieves (1) and sends request to LSP server via socket 2
 ▼           |
+------------+
| LSP Server |
+------------+
```

## UI control

All UI inertactions are made in background via TM_DIALOG2 helper utility, which seems to be a standart way to show native modal windows in Textmate.

To get current `TM_DIALOG` executable path:

````bash
$ env | grep "DIALOG"
````

To list all avialable modal dialog options:

````bash
$ tm_dialog2 --help

usage: "$DIALOG" [--version] <command> [<args>]
10 commands registered:
	alert: Show an alert box.
	defaults: Register default values for user settings.
	filepanel: Shows an open file/folder or save file panel.
	help: Gives a brief list of available commands, or usage details for a specific command.
	images: Add image files as named images for use by other commands/nibs.
	menu: Presents a menu using the given structure
    ...
````
