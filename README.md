# Clipit

Clipit (previously named Grabit) is a command-line tool that allows you to download web pages, extract their readable content, convert it to Markdown, and save it locally.

It's ideal for archiving articles, blog posts, or any web content you may want to save forever and ever. It works well for feeding web content into LLMs too.

I'm using it to save bookmarks in [Obsidian](https://obsidian.md/), so you'll see a lot of focus in this area (the YAML front matter, the domain subdirectory, etc.). But it's flexible enough to be used in other contexts as well.


| It gets you from this                                                              | to this                                                                          |
|------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| ![Raw html](https://vladiliescu.net/clipit-web-downloader/img/before.png "Before") | ![Markdown](https://vladiliescu.net/clipit-web-downloader/img/after.png "After") |



## Features

- **Download and convert web pages to Markdown**: Fetches the content from a URL and converts it into clean Markdown format
- **Supports multiple output formats**: Save content as Markdown, readable or raw HTML, or just send it to stdout so you can pipe it into another app
- **Customizable output**: Include YAML front matter, page titles, source links, and control the output directory structure. This is especially useful for integrating with knowledge management systems such as [Obsidian](https://obsidian.md/)
- **Uses Readability.js**: Extracts the main content from web pages for cleaner outputs (requires Node.js to be installed)
- **Supports Reddit posts**: Clipit now handles Reddit (both text & link) posts (including comments)

## Installation

1. Ensure [uv](https://docs.astral.sh/uv/) is installed
2. Ensure [Node.js](https://nodejs.org/) is installed (optional, required for Readability.js, see below for options)
3. Install **clipit** as a [global uv tool](https://docs.astral.sh/uv/concepts/tools/) (recommended, see below for an alternative)

```sh
uv tool install clipit
```

4. Run **clipit** as any other CLI app  

```sh
clipit -f stdout.md https://vladiliescu.net
```

Alternatively, if you don't want to install it, you can just run it with uvx: `uvx clipit -f stdout.md https://vladiliescu.net`. Keep in mind that this will cause **uv** to check for dependency updates every time you run it, causing you to lose 1-2 precious seconds every time you save something 🥶. 

## Usage

```sh
clipit [OPTIONS] URL
```

### Options

- `--yaml-frontmatter / --no-yaml-frontmatter`: Include YAML front matter with metadata, useful for saving & viewing content in [Obsidian](https://obsidian.md) (default: `enabled`).
- `--include-title / --no-include-title`: Include the page title as an H1 heading. A bit redundant when rendering the YAML frontmatter, but I like it anyway (default: `enabled`).
- `--include-source / --no-include-source`: Include the page source URL at the top of the document. Also a bit redundant when rendering the YAML frontmatter, but this one I don't like so much (default: `disabled`).
- `--user-agent TEXT`: Set a custom User-Agent to be used for retrieving web pages (default: `Clipit/<version>`).
- `--fallback-title TEXT`: Fallback title if no title is found. Use `{date}` for the current date (default: `Untitled {date}`).
- `--bookmark-on-failure`: Save a Markdown bookmark if downloading fails, without asking for confirmation. Without this option, interactive terminals offer a bookmark prompt and noninteractive commands exit with the download error.
- `--title TEXT`: Title for the bookmark fallback. Prompts in interactive terminals when omitted; otherwise uses the URL hostname.
- `--notes TEXT`: Markdown notes for the bookmark fallback. Prompts in interactive terminals when omitted; otherwise leaves notes empty.
- `--use-readability-js / --no-use-readability-js`: Use Readability.js for processing pages. Disabling it will result in **some** processing courtesy of [ReadabiliPy](https://github.com/alan-turing-institute/ReadabiliPy), but it doesn't look so great to be honest (requires Node.js, default: `enabled`).
- `--create-domain-subdir / --no-create-domain-subdir`: Save the resulting files in a subdirectory named after the domain. Useful when saving a **lot** of bookmarks in the same Obsidian vault (default: `enabled`).
- `--overwrite / --no-overwrite`: Overwrite existing files (default: `disabled`).
- `--download-images / --no-download-images`: Download article images and use local references in Markdown and readable HTML (default: `disabled`). Images are stored in a directory named after the article, beside the saved document.
- `--download-folder TEXT`: Set an image-directory template when downloading images. Relative paths start at the working directory; `${domain}` is the page's domain and `${file_name}` is the sanitized article filename without its extension. Markdown and readable HTML use paths relative to the saved document. The library's `clip()` and `clip_and_save()` methods accept the same template as `download_folder`; `clip()` uses the working directory as its document directory unless `output_dir` is supplied.
- `-f, --format [md|stdout.md|html|raw.html]`: Output format(s) to save the content in. Most useful are `md`, which saves the content to a Markdown file, and `stdout.md` which simply outputs the raw content so you can pipe it to something else, like the clipboard or Simon Willison's [llm cli](https://github.com/simonw/llm). Can be specified multiple times (default: `md`).


### Examples

- **Save article images in a separate attachments directory:**
```sh
clipit --download-images --download-folder './attachments/${domain}/${file_name}' https://example.com/article
```

Use single quotes so the shell passes the template unchanged. This saves the document under `example.com/` and its images under `attachments/example.com/<article title>/`. Omit `--download-folder` to keep images beside the document in its article directory. Existing archives are not moved; use `--overwrite` to update an existing note's image references. Files no longer referenced by a note are not deleted.

- **Fall back to a bookmark when a page cannot be downloaded:**
```sh
clipit https://example.com/article --bookmark-on-failure
```

- **Supply bookmark details without prompts, including in scripts:**
```sh
clipit https://example.com/article --bookmark-on-failure --title "Reading list" --notes "Read this later."
```

The normal download is always attempted first. Title and notes apply only to the bookmark fallback. Bookmarks follow the existing metadata, directory, and overwrite options. If YAML front matter is disabled, the bookmark includes a source link so the URL is preserved. File output falls back to `.md`, including when HTML was requested; `-f stdout.md` prints the bookmark instead. Prompts and download diagnostics go to stderr. Only download failures trigger the fallback; extraction and file-writing errors still fail normally.

- **Save a web page as Markdown with the default options:**
```sh
clipit https://example.com/article
```

- **Save as both Markdown and readable HTML:**
```sh
clipit -f md -f html https://example.com/article
```

- **Set a custom User-Agent:**
```sh
clipit --user-agent "MyCustomAgent/1.0" https://example.com/article
```

- **Output markdown content to stdout:**
```sh
clipit -f stdout.md https://example.com/article
```

- **Output markdown content to clipboard (MacOS):**
```sh
clipit -f stdout.md https://example.com/article | pbcopy
```

- **Disable YAML front matter and include source URL:**
```sh
clipit --no-yaml-frontmatter --include-source https://example.com/article
```

- **Save files in the working directory, without creating a domain subdirectory:**
```sh
clipit --no-create-domain-subdir https://example.com/article
```

## Requirements

- [uv](https://docs.astral.sh/uv/) (for running the script)
- [Node.js](https://nodejs.org) (if using Readability.js)

### License

**Clipit**, a tool for archiving web content, copyright (C) 2025  **Vlad Iliescu**

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. See the [LICENSE](./LICENSE) for details.
