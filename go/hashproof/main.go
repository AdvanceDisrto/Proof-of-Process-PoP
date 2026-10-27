// Cross-language byte commitment. Only this byte-level protocol is interoperable;
// Go's json.Marshal is NOT asserted equivalent to Python's canonical JSON.
package main

import (
    "crypto/sha256"
    "encoding/hex"
    "fmt"
    "io"
    "os"
)
func main() {
    raw, err := io.ReadAll(io.LimitReader(os.Stdin, 1000001))
    if err != nil || len(raw) > 1000000 { fmt.Fprintln(os.Stderr,"bad receipt input"); os.Exit(2) }
    h:=sha256.New();h.Write([]byte("ITM-CONTENT-SHA256-v1\x00"));h.Write(raw)
    fmt.Println(hex.EncodeToString(h.Sum(nil)))
}

