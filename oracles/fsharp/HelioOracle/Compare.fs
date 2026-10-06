// Spec section 0.2: comparison of two protocol outputs, plus the Wilson-style band test.
module HelioOracle.Compare

open System
open System.IO
open System.Numerics
open System.Text.RegularExpressions
open HelioOracle.Token

type Tok =
    | NA
    | Int of BigInteger
    | Num of float
    | Word of string

let private reInt = Regex(@"^[+-]?\d+$", RegexOptions.Compiled)
let private reExact = Regex(@"^([+-])(\d+)p([+-])(\d+)$", RegexOptions.Compiled)
let private reDec = Regex(@"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?(f64)?$", RegexOptions.Compiled)

let classify (s: string) : Tok =
    if s = "NA" then NA
    elif s = "nan" then Num nan
    elif s = "+inf" || s = "inf" then Num infinity
    elif s = "-inf" then Num -infinity
    elif reInt.IsMatch s then Int(BigInteger.Parse s)
    else
        let m = reExact.Match s
        if m.Success then
            let e = int m.Groups.[4].Value
            let e = if m.Groups.[3].Value = "-" then -e else e
            Num(ofExactToken m.Groups.[1].Value (Int64.Parse m.Groups.[2].Value) e)
        elif reDec.IsMatch s then Num(parseDec (s.Replace("f64", "")))
        else Word s

/// Default absolute scale floor of spec 0.2 (overridable per tolerance row, 4th TSV column).
let defaultFloor = 1e-6

/// Relative difference of spec 0.2: |a-b| / max(|a|,|b|,floor).
let relDiff (floor: float) (a: float) (b: float) : float =
    if Double.IsNaN a && Double.IsNaN b then 0.0
    elif Double.IsNaN a || Double.IsNaN b then infinity
    elif a = b then 0.0
    elif Double.IsInfinity a || Double.IsInfinity b then infinity
    else abs (a - b) / max (max (abs a) (abs b)) floor

/// (agrees, relative difference) for one token pair.
let compareTok (tol: float, floor: float) (a: string) (b: string) : bool * float =
    match classify a, classify b with
    | NA, NA -> true, 0.0
    | Word x, Word y -> (x = y), (if x = y then 0.0 else infinity)
    | Int x, Int y -> (x = y), (if x = y then 0.0 else infinity)
    | (Int _ | Num _ as x), (Int _ | Num _ as y) ->
        let f = function Int i -> float i | Num v -> v | _ -> nan
        let r = relDiff floor (f x) (f y)
        (r <= tol), r
    | _ -> false, infinity

type Block = { Header: string; Body: string list }

let private norm (l: string) = String.Join(" ", l.Split([| ' '; '\t'; '\r' |], StringSplitOptions.RemoveEmptyEntries))

let parseBlocks (lines: string list) : Result<Block list, string> =
    let rec go acc cur ls =
        match ls with
        | [] ->
            (match cur with
             | None -> Ok(List.rev acc)
             | Some(h: string, _) -> Error(sprintf "unterminated block: %s" h))
        | l :: rest ->
            let t = norm l
            if t = "" then go acc cur rest
            else
                match cur with
                | None ->
                    if t = "begin" || t.StartsWith "begin " then go acc (Some(t, [])) rest
                    else Error(sprintf "line outside block: %s" t)
                | Some(h, body) ->
                    if t = "end" then go ({ Header = h; Body = List.rev body } :: acc) None rest
                    else go acc (Some(h, t :: body)) rest
    go [] None lines

type TolRow = { BlockPrefix: string; LabelPrefix: string; Tol: float; Floor: float }

let readTolfile (path: string) : TolRow list =
    File.ReadAllLines path
    |> Array.toList
    |> List.filter (fun l -> l.Trim() <> "" && not (l.TrimStart().StartsWith "#"))
    |> List.map (fun l ->
        let c = l.Split '\t'
        if c.Length < 3 then failwithf "bad tolfile row: %s" l
        let star (s: string) = if s.Trim() = "*" then "" else s.Trim()
        { BlockPrefix = star c.[0]; LabelPrefix = star c.[1]; Tol = parseDec (c.[2].Trim())
          Floor = (if c.Length >= 4 && c.[3].Trim() <> "" then parseDec (c.[3].Trim()) else defaultFloor) })

let defaultTol = 1e-12

/// Longest (block+label) matching prefix wins; ties -> later row.
let tolFor (rows: TolRow list) (blockHeader: string) (key: string) : float * float =
    let cmd = if blockHeader.StartsWith "begin " then blockHeader.Substring 6 else blockHeader
    rows
    |> List.filter (fun r -> cmd.StartsWith r.BlockPrefix && key.StartsWith r.LabelPrefix)
    |> List.fold (fun (best: (int * (float * float)) option) r ->
        let w = r.BlockPrefix.Length + r.LabelPrefix.Length
        match best with
        | Some(bw, _) when bw > w -> best
        | _ -> Some(w, (r.Tol, r.Floor))) None
    |> Option.map snd
    |> Option.defaultValue (defaultTol, defaultFloor)

/// Label key: leading tokens that are words ("comp kp", "count kp", "class").
let labelKey (toks: string[]) : string =
    toks |> Array.takeWhile (fun t -> match classify t with Word _ -> true | _ -> false) |> String.concat " "

type LineResult = { Key: string; Rel: float; Ok: bool; Msg: string option }

let private compareLine (rows: TolRow list) (header: string) (la: string) (lb: string) (idx: int) : LineResult =
    let ta = la.Split ' '
    let tb = lb.Split ' '
    let key = labelKey ta
    let (tol, floor) = tolFor rows header key
    let fail (why: string) (rel: float) =
        { Key = key; Rel = rel; Ok = false
          Msg = Some(sprintf "  [%s] body line %d (%s)\n    A: %s\n    B: %s" header idx why la lb) }
    if ta.Length <> tb.Length then fail "token count differs" infinity
    else
        let rs = Array.map2 (compareTok (tol, floor)) ta tb
        let maxRel = rs |> Array.map snd |> Array.fold max 0.0
        if rs |> Array.forall fst then { Key = key; Rel = maxRel; Ok = true; Msg = None }
        else fail (sprintf "rel=%.3e tol=%.1e floor=%.1e" maxRel tol floor) maxRel

let compareFiles (fileA: string) (fileB: string) (tolfile: string option) : int =
    let rows = tolfile |> Option.map readTolfile |> Option.defaultValue []
    let load p = parseBlocks (File.ReadAllLines p |> Array.toList)
    match load fileA, load fileB with
    | Error e, _ -> eprintfn "%s: %s" fileA e; 2
    | _, Error e -> eprintfn "%s: %s" fileB e; 2
    | Ok ba, Ok bb ->
        let structural =
            if ba.Length <> bb.Length then [ sprintf "block count differs: %d vs %d" ba.Length bb.Length ] else []
        let pairs = List.zip (List.truncate (min ba.Length bb.Length) ba) (List.truncate (min ba.Length bb.Length) bb)
        let results, structMsgs =
            pairs
            |> List.map (fun (a, b) ->
                if a.Header <> b.Header then [], [ sprintf "header differs:\n    A: %s\n    B: %s" a.Header b.Header ]
                elif a.Body.Length <> b.Body.Length then
                    [], [ sprintf "[%s] line count differs: %d vs %d" a.Header a.Body.Length b.Body.Length ]
                else
                    (List.mapi2 (fun i la lb -> compareLine rows a.Header la lb (i + 1)) a.Body b.Body), [])
            |> List.unzip
        let results = List.concat results
        let allStruct = structural @ List.concat structMsgs
        results |> List.iter (fun r -> r.Msg |> Option.iter (printfn "MISMATCH\n%s"))
        allStruct |> List.iter (printfn "STRUCTURE %s")
        let summary =
            results
            |> List.groupBy (fun r -> r.Key)
            |> List.map (fun (k, rs) -> sprintf "%s=%.3e" k (rs |> List.map (fun r -> r.Rel) |> List.fold max 0.0))
        printfn "summary: blocks=%d lines=%d max_rel_by_label: %s" ba.Length results.Length (String.Join("; ", summary))
        if allStruct.IsEmpty && results |> List.forall (fun r -> r.Ok) then
            printfn "AGREE"
            0
        else
            printfn "DISAGREE"
            1

/// exit 0 iff |F - p| <= z * sqrt(p(1-p)/B1 + p(1-p)/B2)
let band (p: float) (f: float) (b1: float) (b2: float) (z: float) : int =
    let v = p * (1.0 - p)
    let bound = z * sqrt (v / b1 + v / b2)
    let dev = abs (f - p)
    let ok = dev <= bound
    printfn "p=%s F=%s B1=%s B2=%s z=%s |F-p|=%s bound=%s %s"
        (p.ToString("R", inv)) (f.ToString("R", inv)) (b1.ToString("R", inv)) (b2.ToString("R", inv))
        (z.ToString("R", inv)) (dev.ToString("R", inv)) (bound.ToString("R", inv)) (if ok then "IN_BAND" else "OUT_OF_BAND")
    if ok then 0 else 1
