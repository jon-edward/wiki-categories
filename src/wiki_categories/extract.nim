import std/streams
import std/strformat
import std/strutils

import regex
import zip/gzipfiles

const stringRe = r"'[^'\\]*(?:\\.[^'\\]*)*'"
const integerRe = r"\d+"
const floatRe = r"\d+\.\d+"


type CategoryLink* = tuple[clFrom: uint32, clTo: string, isArticle: bool]


iterator extractCategoryLinks*(fileStream: GzFileStream): CategoryLink = 
    let categoryLinksRe = re2(fmt"\(({integerRe}),({stringRe}),(?:{stringRe},)" & r"{4}'((?:page)|(?:subcat))'\)", {regexArbitraryBytes})

    iterator parseLine(line: string): CategoryLink = 
        for hit in line.findAll(categoryLinksRe):
            let clFrom = line[hit.group(0)].parseInt.uint32
            let clTo = line[hit.group(1)].unescape(prefix="'", suffix="'")
            let isArticle = line[hit.group(2)] == "page"

            yield (clFrom: clFrom, clTo: clTo, isArticle: isArticle)
    
    for line in fileStream.lines:
        for hit in parseLine(line):
            yield hit


type Page* = tuple[id: uint32, title: string, isArticle: bool]


iterator extractPages*(fileStream: GzFileStream): Page = 
    let pagesRe = re2(fmt"\(({integerRe}),((?:14)|(?:0))," & 
        fmt"({stringRe}),0," & 
        fmt"{integerRe},{floatRe}," & 
        fmt"{stringRe},{stringRe}," & 
        fmt"{integerRe},{integerRe}," & 
        fmt"{stringRe},(?:{stringRe}|NULL)\)")
    
    iterator parseLine(line: string): Page = 
        for hit in line.findAll(pagesRe):
            let id = line[hit.group(0)].parseInt.uint32
            let isArticle = line[hit.group(1)] == "0"
            let title = line[hit.group(2)].unescape(prefix="'", suffix="'")

            yield (id: id, title: title, isArticle: isArticle)

    for line in fileStream.lines:
        for hit in parseLine(line):
            yield hit
