// HelioOracle -- independent F# reference oracle for the Darwin Heliobiology numerical core.
//
// ADR-009 admission criteria for a foreign oracle:
//  (1) Written from docs/SIO_CORE_SPEC.md ONLY; never transliterated from Sounio (nothing under
//      sio/, src/ or the Sounio compiler tree was read while writing this project).
//  (2) Statically typed, immutable-by-default ML-family language (F#; values are immutable,
//      absent data is `float option`, never a sentinel number).
//  (3) Exact toolchain pinned: .NET SDK 9.0.300 / F# 9 (oracles/fsharp/global.json, rollForward=disable).
//  (4) Why a Sounio closed-form twin is not enough: both Sounio paths (main core and twin) share
//      the same compiler's f64 semantics and the same reading of the constants, so a common-mode
//      error would pass both; only a foreign implementation gives independence.
//
// Algorithms are the plain spec formulas: two-pass statistics, sort-based quantile,
// moment-formula DerSimonian-Laird. Correctness over cleverness.
module HelioOracle.Program

open System
open System.IO
open HelioOracle.Token

let private runCommand (toks: string list) : string list =
    match toks with
    | "helio" :: [ file ] -> Core.helio file
    | "calib" :: files when not files.IsEmpty -> Core.calib files
    | "meta" :: [ file ] -> Core.meta file
    | _ -> failwithf "unknown or malformed command: %s" (String.Join(" ", toks))

let private commandTokens (line: string) : string list =
    let body = match line.IndexOf '#' with | -1 -> line | i -> line.Substring(0, i)
    body.Split([| ' '; '\t'; '\r' |], StringSplitOptions.RemoveEmptyEntries) |> List.ofArray

let private run () : int =
    let path =
        match Environment.GetEnvironmentVariable "GATE_CMD" with
        | null | "" -> "build/gate/cmd.txt"
        | p -> p
    let blocks =
        File.ReadAllLines path
        |> Array.toList
        |> List.map commandTokens
        |> List.filter (fun t -> not t.IsEmpty)
        |> List.map (fun toks ->
            let body = runCommand toks
            String.Join("\n", ("begin " + String.Join(" ", toks)) :: body @ [ "end" ]))
    let out = Console.OpenStandardOutput()
    let bytes = Text.Encoding.ASCII.GetBytes(String.Join("\n", blocks) + "\n")
    out.Write(bytes, 0, bytes.Length)
    0

[<EntryPoint>]
let main argv =
    try
        match List.ofArray argv with
        | [ "run" ] -> run ()
        | [ "compare"; a; b ] -> Compare.compareFiles a b None
        | [ "compare"; a; b; tol ] -> Compare.compareFiles a b (Some tol)
        | [ "band"; p; f; b1; b2; z ] ->
            Compare.band (parseDec p) (parseDec f) (parseDec b1) (parseDec b2) (parseDec z)
        | _ ->
            eprintfn "usage: HelioOracle run | compare <A> <B> [tolfile] | band <p> <F> <B1> <B2> <z>"
            2
    with ex ->
        eprintfn "error: %s" ex.Message
        2
