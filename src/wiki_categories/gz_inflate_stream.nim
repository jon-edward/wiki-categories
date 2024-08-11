import std/streams

import zip/zlib


const chunk* = 16384


iterator gzInflateStream*(stream: Stream): string = 
    ## Based on http://zlib.net/zpipe.c
    
    var z: ZStream

    z.availIn = 0
    let wbits = MAX_WBITS + 16  # gzip wbits

    var status = inflateInit2(z, wbits.cint)

    case status
    of Z_OK: discard
    of Z_MEM_ERROR: raise newException(ZlibStreamError, "zlib out of memory")
    of Z_STREAM_ERROR: raise newException(ZlibStreamError, "invalid zlib stream parameter!")
    of Z_VERSION_ERROR: raise newException(ZlibStreamError, "zlib version mismatch!")
    else: raise newException(ZlibStreamError, "Unknown error(" & $status & ") : " & $z.msg)

    proc readInto[N: static[int], T](stream: Stream, buffer: var array[N, T]): cuint = 
        stream.readData(buffer.addr, buffer.len).cuint

    var inBuffer: array[chunk, char]
    var inBufferLen = stream.readInto(inBuffer)

    var outBuffer: array[chunk, char]
    
    template feedOutBuffer() = 
        z.availOut = chunk
        z.nextOut = cast[cstring](outBuffer.addr)
        
        var ret = inflate(z, Z_NO_FLUSH)

        case ret
        of Z_DATA_ERROR, Z_MEM_ERROR, Z_NEED_DICT:
            discard inflateEnd(z)
            raise newException(ZlibStreamError, "zlib encountered error while feeding output buffer")
        else:
            discard

        let have = chunk - z.availOut

        if have != 0:
            yield cast[string](outBuffer[0..<have])

    while inBufferLen != 0:
        # feed input buffer 

        z.availIn = inBufferLen
        z.nextIn = cast[cstring](inBuffer.addr)
        
        feedOutBuffer()
        while z.availOut == 0:
            feedOutBuffer()
        
        inBufferLen = stream.readInto(inBuffer)
    
    discard inflateEnd(z)
