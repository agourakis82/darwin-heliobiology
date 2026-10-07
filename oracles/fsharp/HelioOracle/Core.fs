// Spec sections 4 (helio), 6 (calib), 8 (meta). Each returns the protocol body lines.
module HelioOracle.Core

open System
open System.IO
open HelioOracle.Token
open HelioOracle.Stats

let private tokens (line: string) : string list =
    let body = match line.IndexOf '#' with | -1 -> line | i -> line.Substring(0, i)
    body.Split([| ' '; '\t'; '\r' |], StringSplitOptions.RemoveEmptyEntries) |> List.ofArray

let private optNum (s: string) : float option =
    if s = "NA" then None else Some(parseDec s)

// ---------------------------------------------------------------- helio (4)

type Sample =
    | KpS of int64 * float option
    | DstS of int64 * float option
    | BzS of int64 * float option
    | WindS of int64 * float option * float option

let private sampleT = function
    | KpS(t, _) | DstS(t, _) | BzS(t, _) | WindS(t, _, _) -> t

type private CaseLine =
    | Now of int64
    | Smp of Sample

let private parseCaseLine (toks: string list) : CaseLine option =
    match toks with
    | [] -> None
    | [ "NOW"; t ] -> Some(Now(Int64.Parse t))
    | [ "KP"; t; v ] -> Some(Smp(KpS(Int64.Parse t, optNum v)))
    | [ "DST"; t; v ] -> Some(Smp(DstS(Int64.Parse t, optNum v)))
    | [ "BZ"; t; v ] -> Some(Smp(BzS(Int64.Parse t, optNum v)))
    | [ "WIND"; t; n; v ] -> Some(Smp(WindS(Int64.Parse t, optNum n, optNum v)))
    | _ -> failwithf "bad case line: %s" (String.Join(" ", toks))

let helio (path: string) : string list =
    let parsed = File.ReadAllLines path |> Array.toList |> List.map (tokens >> parseCaseLine) |> List.choose id
    let samples = parsed |> List.choose (function Smp s -> Some s | Now _ -> None)
    let now = parsed |> List.tryPick (function Now t -> Some t | Smp _ -> None)
    let tEnd =
        match samples with
        | [] -> (match now with Some t -> t | None -> failwith "no samples and no NOW line")
        | _ -> samples |> List.map sampleT |> List.max
    let inWin t = tEnd - 12L * 3600L < t && t <= tEnd
    let kps = samples |> List.choose (function KpS(t, Some v) when inWin t -> Some v | _ -> None) |> Array.ofList
    let dsts = samples |> List.choose (function DstS(t, Some v) when inWin t -> Some v | _ -> None) |> Array.ofList
    let bzs = samples |> List.choose (function BzS(t, Some v) when inWin t -> Some v | _ -> None) |> Array.ofList
    let winds =
        samples
        |> List.choose (function WindS(t, Some n, Some v) when inWin t -> Some(n, v) | _ -> None)
        |> Array.ofList
    let kp = if kps.Length = 0 then None else Some(clip01 (mean kps / 9.0))
    let dst = if dsts.Length = 0 then None else Some(clip01 (abs (min (Array.min dsts) 0.0) / 78.0))
    let bz = if bzs.Length = 0 then None else Some(clip01 (mean (bzs |> Array.map (fun b -> max (-b) 0.0)) / 8.7))
    let pressure =
        if winds.Length = 0 then None
        else Some(clip01 (mean (winds |> Array.map (fun (n, v) -> 1.6726e-6 * n * (v * v))) / 7.30))
    let variability = if kps.Length < 2 then None else Some(clip01 (std1 kps / 1.57))
    let score =
        match kp, dst, bz, pressure, variability with
        | Some a, Some b, Some c, Some d, Some e -> Some(clip01 (0.35 * a + 0.25 * b + 0.20 * c + 0.15 * d + 0.05 * e))
        | _ -> None
    let cls =
        match score with
        | None -> 3
        | Some s when s < 0.33 -> 0
        | Some s when s < 0.66 -> 1
        | Some _ -> 2
    let bit (v: float option) (thr: float) (b: int) =
        match v with
        | Some x when x >= thr -> b
        | _ -> 0
    let alerts = bit kp 0.7 1 + bit dst 0.6 2 + bit bz 0.5 4 + bit pressure 0.5 8 + bit variability 0.6 16
    [ sprintf "t_end %d" tEnd
      sprintf "n_window %d %d %d %d" kps.Length dsts.Length bzs.Length winds.Length
      sprintf "comp kp %s" (fmtOpt kp)
      sprintf "comp dst %s" (fmtOpt dst)
      sprintf "comp bz %s" (fmtOpt bz)
      sprintf "comp pressure %s" (fmtOpt pressure)
      sprintf "comp variability %s" (fmtOpt variability)
      sprintf "score %s" (fmtOpt score)
      sprintf "class %d" cls
      sprintf "alerts %d" alerts ]

// ---------------------------------------------------------------- calib (6)

/// kp_var for every record: std1 of the valid Kp with t_j in (t_i - 12h, t_i];
/// window members taken in file order. Records may be unsorted in time.
let private kpVarSeries (recs: Omni.Record[]) : float option[] =
    let sorted =
        recs
        |> Array.mapi (fun i r -> (r.T, i, r.Kp))
        |> Array.choose (fun (t, i, k) -> k |> Option.map (fun v -> (t, i, v)))
        |> Array.sortBy (fun (t, i, _) -> (t, i))
    let ts = sorted |> Array.map (fun (t, _, _) -> t)
    // first index whose t is strictly greater than x
    let upper (x: int64) =
        let rec go lo hi = if lo >= hi then lo else (let mid = (lo + hi) / 2 in if ts.[mid] > x then go lo mid else go (mid + 1) hi)
        go 0 ts.Length
    recs
    |> Array.map (fun r ->
        let lo = upper (r.T - 12L * 3600L)
        let hi = upper r.T
        let window = sorted.[lo .. hi - 1] |> Array.sortBy (fun (_, i, _) -> i) |> Array.map (fun (_, _, v) -> v)
        if window.Length < 2 then None else Some(std1 window))

let calib (paths: string list) : string list =
    let recs, _bad = Omni.readFiles paths
    let series : (string * float * float option[]) list =
        [ "kp", 9.0, recs |> Array.map (fun r -> r.Kp)
          "dst_abs", 78.0, recs |> Array.map (fun r -> r.Dst |> Option.map (fun d -> abs (min d 0.0)))
          "bz_south", 8.7, recs |> Array.map (fun r -> r.Bz |> Option.map (fun b -> max (-b) 0.0))
          "pressure", 7.30, recs |> Array.map (fun r -> match r.N, r.V with | Some n, Some v -> Some(1.6726e-6 * n * (v * v)) | _ -> None)
          "kp_var", 1.57, kpVarSeries recs ]
    let block (name: string, target: float, raw: float option[]) =
        let xs = raw |> Array.choose id
        let count = xs.Length
        let m = if count = 0 then None else Some(mean xs)
        let sorted = Array.sort xs
        let q p = if count = 0 then None else Some(quantileSorted sorted p)
        let p99 = q 0.99
        let suggested =
            if name = "kp" then Some 9.0
            else p99 |> Option.map (fun x -> max x 1.0)
        let ok =
            match suggested with
            | Some s when abs (s - target) <= 0.005 -> 1
            | _ -> 0
        [ sprintf "count %s %d" name count
          sprintf "mean %s %s" name (fmtOpt m)
          sprintf "p50 %s %s" name (fmtOpt (q 0.50))
          sprintf "p90 %s %s" name (fmtOpt (q 0.90))
          sprintf "p95 %s %s" name (fmtOpt (q 0.95))
          sprintf "p99 %s %s" name (fmtOpt p99)
          sprintf "suggested %s %s" name (fmtOpt suggested)
          sprintf "target_ok %s %d" name ok ]
    sprintf "n_records %d" recs.Length :: (series |> List.collect block)

// ---------------------------------------------------------------- meta (8)

let meta (path: string) : string list =
    let studies =
        File.ReadAllLines path
        |> Array.toList
        |> List.map tokens
        |> List.choose (function
            | [ "STUDY"; _; y; v ] -> Some(parseDec y, parseDec v)
            | [] -> None
            | other -> failwithf "bad meta line: %s" (String.Join(" ", other)))
        |> Array.ofList
    let k = studies.Length
    if k < 1 then failwith "meta needs k >= 1"
    let ys = studies |> Array.map fst
    let vs = studies |> Array.map snd
    let w = vs |> Array.map (fun v -> 1.0 / v)
    let sw = sum w
    let swy = sum (Array.map2 (fun wi yi -> wi * yi) w ys)
    let sw2 = sum (w |> Array.map (fun wi -> wi * wi))
    let yFE = swy / sw
    let q = sum (Array.map2 (fun wi yi -> wi * ((yi - yFE) * (yi - yFE))) w ys)
    let c = sw - sw2 / sw
    let df = float (k - 1)
    let tau2 = if c > 0.0 then max 0.0 ((q - df) / c) else 0.0
    let i2 = if q > 0.0 then max 0.0 ((q - df) / q) * 100.0 else 0.0
    let ws = vs |> Array.map (fun v -> 1.0 / (v + tau2))
    let sws = sum ws
    let yRE = sum (Array.map2 (fun wi yi -> wi * yi) ws ys) / sws
    let se = sqrt (1.0 / sws)
    let z = yRE / se
    let half = 1.959963984540054 * se
    [ sprintf "k %d" k
      sprintf "Q %s" (fmt q)
      sprintf "tau2 %s" (fmt tau2)
      sprintf "I2 %s" (fmt i2)
      sprintf "pooled_fe %s" (fmt yFE)
      sprintf "pooled_re %s" (fmt yRE)
      sprintf "se %s" (fmt se)
      sprintf "z %s" (fmt z)
      sprintf "ci_lo %s" (fmt (yRE - half))
      sprintf "ci_hi %s" (fmt (yRE + half)) ]
