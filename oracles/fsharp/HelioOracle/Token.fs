// Spec SIO_CORE_SPEC.md section 0.1: exact numeric tokens.
module HelioOracle.Token

open System
open System.Globalization

let inv = CultureInfo.InvariantCulture

/// Decimal text -> f64 (round-to-nearest, invariant culture).
let parseDec (s: string) : float =
    Double.Parse(s, NumberStyles.Float, inv)

/// Exact token of a f64 (spec 0.1).
let fmt (x: float) : string =
    if Double.IsNaN x then "nan"
    elif Double.IsPositiveInfinity x then "+inf"
    elif Double.IsNegativeInfinity x then "-inf"
    elif x = 0.0 then "0"
    else
        let bits = BitConverter.DoubleToInt64Bits x
        let negative = bits < 0L
        let biased = int ((bits >>> 52) &&& 0x7FFL)
        if biased = 0 then failwithf "subnormal value cannot be tokenised: %s" (x.ToString("R", inv))
        let n = (bits &&& 0xFFFFFFFFFFFFFL) ||| (1L <<< 52)
        let e = biased - 1023
        let sign = if negative then "-" else "+"
        let esign = if e < 0 then "-" else "+"
        sprintf "%s%dp%s%d" sign n esign (abs e)

let fmtOpt (x: float option) : string =
    match x with
    | Some v -> fmt v
    | None -> "NA"

/// Inverse of fmt for the "<s><n>p<e>" form: n * 2^(e-52), exact.
let ofExactToken (sign: string) (n: int64) (e: int) : float =
    let m = Math.ScaleB(float n, e - 52)
    if sign = "-" then -m else m
