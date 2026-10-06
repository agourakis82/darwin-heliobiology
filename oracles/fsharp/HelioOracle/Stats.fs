// Spec section 0: the only arithmetic allowed: + - * /, sqrt, floor, comparisons.
module HelioOracle.Stats

let clip01 (x: float) : float = min 1.0 (max 0.0 x)

/// Sequential sum in the given order.
let sum (xs: float[]) : float = Array.fold (fun acc x -> acc + x) 0.0 xs

/// mean = sequential sum / count (caller guarantees n >= 1).
let mean (xs: float[]) : float = sum xs / float xs.Length

/// Sample standard deviation (ddof=1), two-pass; n >= 2.
let std1 (xs: float[]) : float =
    let m = mean xs
    let ss = xs |> Array.fold (fun acc x -> acc + (x - m) * (x - m)) 0.0
    sqrt (ss / float (xs.Length - 1))

/// Linear-interpolation quantile over an ascending-sorted array (spec 6).
let quantileSorted (xs: float[]) (q: float) : float =
    let n = xs.Length
    let h = q * float (n - 1)
    let lo = int (floor h)
    if lo = n - 1 then xs.[lo]
    else xs.[lo] + (h - float lo) * (xs.[lo + 1] - xs.[lo])

let quantile (xs: float[]) (q: float) : float =
    quantileSorted (Array.sort xs) q
