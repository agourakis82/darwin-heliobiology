// Spec section 2: OMNI2 parser (independent implementation).
module HelioOracle.Omni

open System
open System.IO
open HelioOracle.Token

type Record =
    { T: int64
      Bx: float option
      By: float option
      Bz: float option
      N: float option
      V: float option
      P: float option
      Kp: float option
      Dst: float option }

/// Days since 1970-01-01 of a proleptic-Gregorian civil date.
let daysFromCivil (y0: int64) (m: int64) (d: int64) : int64 =
    let y = if m <= 2L then y0 - 1L else y0
    let era = (if y >= 0L then y else y - 399L) / 400L
    let yoe = y - era * 400L
    let mp = (m + 9L) % 12L
    let doy = (153L * mp + 2L) / 5L + d - 1L
    let doe = yoe * 365L + yoe / 4L - yoe / 100L + doy
    era * 146097L + doe - 719468L

let private wholeInt (s: string) : int64 option =
    match Double.TryParse(s, Globalization.NumberStyles.Float, inv) with
    | true, v when v = floor v && abs v < 1e12 -> Some(int64 v)
    | _ -> None

let private present (fill: float) (v: float) : float option =
    if v >= fill then None else Some v

/// Ok record | Error () for a malformed line. Caller has removed blank lines.
let parseLine (line: string) : Result<Record, unit> =
    let cols = line.Split([| ' '; '\t' |], StringSplitOptions.RemoveEmptyEntries)
    if cols.Length < 41 then Error()
    else
        let num i = Double.TryParse(cols.[i], Globalization.NumberStyles.Float, inv)
        let field i = match num i with | true, v -> Some v | _ -> None
        match wholeInt cols.[0], wholeInt cols.[1], wholeInt cols.[2] with
        | Some year, Some doy, Some hour ->
            let ok = [ 12; 15; 16; 23; 24; 28; 38; 40 ] |> List.forall (fun i -> (field i).IsSome)
            if not ok then Error()
            else
                let get i fill = present fill (field i |> Option.get)
                Ok
                    { T = (daysFromCivil year 1L 1L + doy - 1L) * 86400L + hour * 3600L
                      Bx = get 12 999.9
                      By = get 15 999.9
                      Bz = get 16 999.9
                      N = get 23 999.9
                      V = get 24 9999.0
                      P = get 28 99.99
                      Kp = get 38 99.0 |> Option.map (fun k -> k / 10.0)
                      Dst = get 40 99999.0 }
        | _ -> Error()

/// Reads files in order; returns (records in file order, bad line count).
let readFiles (paths: string list) : Record[] * int =
    let results =
        paths
        |> List.collect (fun p -> File.ReadAllLines p |> List.ofArray)
        |> List.filter (fun l -> l.Trim() <> "")
        |> List.map parseLine
    let recs = results |> List.choose (function Ok r -> Some r | Error() -> None) |> Array.ofList
    let bad = results |> List.sumBy (function Error() -> 1 | Ok _ -> 0)
    recs, bad
