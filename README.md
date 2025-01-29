# Grabit

Grabit is a command-line tool that allows you to download web pages, extract their readable content, convert it to Markdown, and save it locally.

It's ideal for archiving articles, blog posts, or any web content you may want to save forever and ever. It works well for feeding web content into LLMs too.

I'm using it to save bookmarks in [Obsidian](https://obsidian.md/), so you'll see a lot of focus in this area (the YAML front matter, the domain subdirectory, etc.). But it's flexible enough to be used in other contexts as well.


| It gets you from this                                    | to this                                     |
|-------------------------------------------|-------------------------------------------|
| ![Raw html](https://vladiliescu.net/grabit-web-downloader/img/before.png "Before") | ![Markdown](https://vladiliescu.net/grabit-web-downloader/img/after.png "After") |



## Features

- **Download and convert web pages to Markdown**: Fetches the content from a URL and converts it into clean Markdown format
- **Supports multiple output formats**: Save content as Markdown, readable or raw HTML, or just send it to stdout so you can pipe it into another app
- **Customizable output**: Include YAML front matter, page titles, source links, and control the output directory structure. This is especially useful for integrating with knowledge management systems such as [Obsidian](https://obsidian.md/)
- **Uses Readability.js**: Extracts the main content from web pages for cleaner outputs (requires Node.js to be installed)
- **Supports Reddit posts**: Grabit now handles Reddit (both text & link) posts (including comments)

## Installation

- Ensure [uv](https://docs.astral.sh/uv/) is installed
- Ensure [Node.js](https://nodejs.org/) is installed (optional, required for Readability.js, see below for options)
- Download [grabit.py](https://github.com/vladiliescu/grabit/releases/latest/download/grabit.py) to a local folder on your machine, e.g. `~/scripts`.

## Usage

```sh
uv run -q <download-path>/grabit.py [OPTIONS] URL
```

### Options

- `--yaml-frontmatter / --no-yaml-frontmatter`: Include YAML front matter with metadata, useful for saving & viewing content in [Obsidian](https://obsidian.md) (default: `enabled`).
- `--include-title / --no-include-title`: Include the page title as an H1 heading. A bit redundant when rendering the YAML frontmatter, but I like it anyway (default: `enabled`).
- `--include-source / --no-include-source`: Include the page source URL at the top of the document. Also a bit redundant when rendering the YAML frontmatter, but this one I don't like so much (default: `disabled`).
- `--user-agent TEXT`: Set a custom User-Agent to be used for retrieving web pages (default: `Grabit/<version>`).
- `--fallback-title TEXT`: Fallback title if no title is found. Use `{date}` for the current date (default: `Untitled {date}`).
- `--use-readability-js / --no-use-readability-js`: Use Readability.js for processing pages. Disabling it will result in **some** processing courtesy of [ReadabiliPy](https://github.com/alan-turing-institute/ReadabiliPy), but it doesn't look so great to be honest (requires Node.js, default: `enabled`).
- `--create-domain-subdir / --no-create-domain-subdir`: Save the resulting files in a subdirectory named after the domain. Useful when saving a **lot** of bookmarks in the same Obsidian vault (default: `enabled`).
- `--overwrite / --no-overwrite`: Overwrite existing files.(default: `disabled`).
- `-f, --format [md|stdout.md|html|raw.html]`: Output format(s) to save the content in. Most useful are `md`, which saves the content to a Markdown file, and `stdout.md` which simply outputs the raw content so you can pipe it to something else, like the clipboard or Simon Willison's [llm cli](https://github.com/simonw/llm). Can be specified multiple times (default: `md`).


### Examples

- **Save a web page as Markdown with the default options:**
```sh
uv run grabit.py https://example.com/article
```

- **Save as both Markdown and readable HTML:**
```sh
uv run grabit.py -f md -f html https://example.com/article
```

- **Set a custom User-Agent:**
```sh
uv run grabit.py --user-agent "MyCustomAgent/1.0" https://example.com/article 
```

- **Output markdown content to stdout:**
```sh
uv run -q grabit.py -f stdout.md https://example.com/article
```
Note the `-q` flag to suppress uv's output.

- **Output markdown content to clipboard (MacOS):**
```sh
uv run -q grabit.py -f stdout.md https://example.com/article | pbcopy
```

- **Disable YAML front matter and include source URL:**
```sh
uv run grabit.py --no-yaml-frontmatter --include-source https://example.com/article
```

- **Save files in the working directory, without creating a domain subdirectory:**
```sh
uv run grabit.py --no-create-domain-subdir https://example.com/article
```

## Requirements

- [uv](https://docs.astral.sh/uv/) (for running the script)
- [Node.js](https://nodejs.org) (if using Readability.js)

### License

**Grabit**, a tool for archiving web content, copyright (C) 2025  **Vlad Iliescu**

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. See the [LICENSE](./LICENSE) for details.

