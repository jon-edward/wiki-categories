# Package

version       = "0.1.0"
author        = "jon-edward"
description   = "A tool for collecting and manipulating the Wikipedia category tree."
license       = "MIT"
srcDir        = "src"
bin           = @["wiki_categories"]


# Dependencies

requires "nim >= 2.0.8"

requires "zip >= 0.3.1"
requires "regex >= 0.25.0"