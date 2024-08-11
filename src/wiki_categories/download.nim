import std/httpclient
import std/logging
import std/os
import std/streams
import std/strformat
import std/strutils
import std/times

from data import dataDir


var logger = newConsoleLogger()
addHandler(logger)

var client = newHttpClient()
client.headers = newHttpHeaders({"Accept-Encoding": "gzip"})


proc formatDecimal(val: float, unit: string = "", decimalPositions: int = 2): string = 
    let unit = if unit != "":
        " " & unit
    else:
        ""
    
    fmt"{val.formatFloat(ffDecimal, decimalPositions)}{unit}"


proc download*(url: string, dest: string = ""): string = 
    let filename = if dest == "":
        dataDir / url.split("/")[^1]
    else:
        dest

    info(fmt"Downloading {url} to {filename}")

    let headResponse = client.head(url)
    let contentLength = headResponse.headers.getOrDefault("Content-Length", @["-1"].HttpHeaderValues).parseInt
    
    if contentLength != -1:
        let fileDesc = if contentLength < 1000:
            formatDecimal(contentLength.float, "B")
        elif contentLength < 1000 * 1000:
            formatDecimal(contentLength.float / 1000, "KB")
        elif contentLength < 1000 * 1000 * 1000:
            formatDecimal(contentLength.float / (1000 * 1000), "MB")
        else:
            formatDecimal(contentLength.float / (1000 * 1000 * 1000), "GB")
             
        info("File size: " & fileDesc)

    let startTime = now()
    info(fmt"Start time: {startTime}")
    
    client.downloadFile(url, filename)

    let endTime = now()
    info(fmt"End time: {endTime}")

    let elapsedTime = endTime - startTime
    info(fmt"Elapsed time: {elapsedTime}")

    if contentLength != -1:
        let downloadSpeedDesc = formatDecimal((contentLength.float / elapsedTime.inSeconds.float) / (1000 * 1000), "MB/s")
        info("Average download speed: " & downloadSpeedDesc)
    
    filename
