-- passport.fut -- independent reference oracle (Futhark 0.27.1) for the
-- "passport" block-permutation cross-correlation test, docs/SIO_CORE_SPEC.md §7.
--
-- ADR-009 criteria
--  (1) Written from docs/SIO_CORE_SPEC.md ONLY; never transliterated from the
--      Sounio sources, the Python code or the Sounio twin.
--  (2) Statically typed, purely functional language; the only "mutation" is
--      Futhark's uniqueness-typed in-place array update, which is
--      semantically a pure copy (no hidden state, no globals, no I/O).
--  (3) Toolchain pinned to Futhark 0.27.1 (run.sh refuses any other version).
--  (4) Rationale: the Sounio twin uses the same PRNG as the Sounio main
--      implementation, so it cannot reveal a PRNG bug.  A foreign
--      implementation that (a) reproduces the shared-seed SplitMix64 stream
--      EXACTLY (entry `shared`, bit-for-bit up to float summation order) and
--      (b) reproduces the null DISTRIBUTION with a DIFFERENT generator
--      (entry `own`, PCG-XSH-RR 64/32) gives independent evidence that both
--      the stream and the statistic are right.
--
-- Pearson is deliberately formulated differently from a z-score product:
-- centred sums  r = Σ(x-mx)(y-my) / sqrt(Σ(x-mx)² · Σ(y-my)²).
--
-- Spec decisions on ambiguities (see also run.sh):
--  * No valid lag  => T = 0, lag_obs = 0.
--  * Valid lag with |r| == 0 exactly and no better one => smallest such lag.
--  * Block permutation: y' is the concatenation of the (shuffled) blocks, so
--    if the short last block lands mid-sequence the later blocks shift left.
--  * Blocks are consecutive runs of 24 indices; K = ceil(n/24).
--  * B >= 1 is assumed for quantiles.

-- ------------------------------------------------------------------
-- SplitMix64 (spec §7)
-- ------------------------------------------------------------------
def golden : u64 = 0x9E3779B97F4A7C15u64

-- returns (new state, output)
def sm_next (state: u64) : (u64, u64) =
  let s = state + golden
  let z = (s ^ (s >> 30)) * 0xBF58476D1CE4E5B9u64
  let z = (z ^ (z >> 27)) * 0x94D049BB133111EBu64
  in (s, z ^ (z >> 31))

-- bounded(m) = (output >> 11) mod m
def sm_bounded (state: u64) (m: i64) : (u64, i64) =
  let (s, o) = sm_next state
  in (s, i64.u64 ((o >> 11) % u64.i64 m))

-- ------------------------------------------------------------------
-- PCG-XSH-RR 64/32 (own generator, NOT SplitMix64)
-- state = (state, inc)
-- ------------------------------------------------------------------
def pcg_mult : u64 = 6364136223846793005u64

def pcg_step (st: (u64, u64)) : (u64, u64) =
  let (s, inc) = st
  in (s * pcg_mult + inc, inc)

def pcg_out (old: u64) : u32 =
  let xs = u32.u64 (((old >> 18) ^ old) >> 27)
  let rot = u32.u64 (old >> 59)
  in (xs >> rot) | (xs << ((0u32 - rot) & 31u32))

-- pcg32_srandom(initstate, initseq)
def pcg_seed (initstate: u64) (initseq: u64) : (u64, u64) =
  let st = (0u64, (initseq << 1) | 1u64)
  let st = pcg_step st
  let st = (st.0 + initstate, st.1)
  in pcg_step st

-- 64 random bits from two consecutive 32-bit outputs
def pcg_next64 (st: (u64, u64)) : ((u64, u64), u64) =
  let hi = pcg_out st.0
  let st = pcg_step st
  let lo = pcg_out st.0
  let st = pcg_step st
  in (st, (u64.u32 hi << 32) | u64.u32 lo)

-- bias <= m / 2^64 (negligible)
def pcg_bounded (st: (u64, u64)) (m: i64) : ((u64, u64), i64) =
  let (st, v) = pcg_next64 st
  in (st, i64.u64 (v % u64.i64 m))

-- ------------------------------------------------------------------
-- Fisher-Yates over K blocks (generic in the generator)
-- ------------------------------------------------------------------
def shuffle_order 'r (K: i64) (st0: r) (bounded: r -> i64 -> (r, i64)) : [K]i64 =
  let (ord, _) =
    loop (ord, st) = (iota K, st0) for ii < i64.max 0 (K - 1) do
      let i = K - 1 - ii
      let (st', j) = bounded st (i + 1)
      let a = ord[i]
      let b = ord[j]
      let ord = ord with [i] = b
      let ord = ord with [j] = a
      in (ord, st')
  in ord

-- y' = concatenation of blocks of y in the order `ord`
def permute_y [n] [K] (y: [n]f64) (ord: [K]i64) : [n]f64 =
  let sz s = i64.min 24 (n - 24 * s)
  let sizes = map (\s -> sz s) ord
  let ends = scan (+) 0 sizes
  let starts = map2 (-) ends sizes
  let idx = map (\q -> let k = q / 24
                       let t = q % 24
                       in if t < sz ord[k] then starts[k] + t else -1) (iota (K * 24))
  let vals = map (\q -> let s = ord[q / 24]
                        let t = q % 24
                        in if t < sz s then y[24 * s + t] else 0.0) (iota (K * 24))
  in scatter (replicate n 0.0) idx vals

-- ------------------------------------------------------------------
-- Statistic T = max_l |r(l)|, smallest l on ties
-- ------------------------------------------------------------------
-- sequential mean and sum of squared deviations of a[off .. off+m-1]
def seg_stats [n] (a: [n]f64) (off: i64) (m: i64) : (f64, f64) =
  let s = loop acc = 0.0 for i < m do acc + a[off + i]
  let mu = s / f64.i64 m
  let ss = loop acc = 0.0 for i < m do
             let d = a[off + i] - mu
             in acc + d * d
  in (mu, ss)

def std_ok (ss: f64) (m: i64) : bool =
  f64.sqrt (ss / f64.i64 m) >= 1e-12

-- number of lags examined: l in 0 .. min(lag_max, n-10)
def n_lags (n: i64) (lag_max: i64) : i64 =
  i64.max 0 (i64.min lag_max (n - 10) + 1)

-- per-lag statistics of the x segment x[0..m-1] (independent of the permutation)
def x_info [n] (x: [n]f64) (lag_max: i64) : ([]f64, []f64, []bool) =
  let L = n_lags n lag_max
  let r = map (\l -> let m = n - l
                     let (mu, ss) = seg_stats x 0 m
                     in (mu, ss, std_ok ss m)) (iota L)
  in unzip3 r

-- |r(l)| of lag l, or (false, 0) if the lag is skipped
def lag_abs_r [n] (x: [n]f64) (xm: f64) (xss: f64) (xok: bool) (yv: [n]f64) (l: i64) : (bool, f64) =
  let m = n - l
  let (my, syy) = seg_stats yv l m
  in if !xok || !(std_ok syy m) then (false, 0.0)
     else let sxy = loop acc = 0.0 for i < m do
                      acc + (x[i] - xm) * (yv[l + i] - my)
          in (true, f64.abs (sxy / f64.sqrt (xss * syy)))

def tstat [n] [L] (x: [n]f64) (xm: [L]f64) (xss: [L]f64) (xok: [L]bool)
                  (yv: [n]f64) : (f64, i64) =
  let (_, bt, bl) =
    loop (found, bt, bl) = (false, 0.0, 0i64) for l < L do
      let (ok, a) = lag_abs_r x xm[l] xss[l] xok[l] yv l
      in if ok && (!found || a > bt) then (true, a, l) else (found, bt, bl)
  in (bt, bl)
-- ------------------------------------------------------------------
-- sorting / quantiles / helpers
-- ------------------------------------------------------------------
-- LSD radix sort on the IEEE bits; valid for non-negative doubles (T >= 0)
def sort_nonneg [N] (a: [N]f64) : [N]f64 =
  let bits = map f64.to_bits a
  let bits =
    loop bits for bit < 64 do
      let b = map (\v -> i64.u64 ((v >> u64.i32 bit) & 1u64)) bits
      let z = map (1 -) b
      let zpos = scan (+) 0 z
      let opos = scan (+) 0 b
      let nz = if N == 0 then 0 else zpos[N - 1]
      let dst = map3 (\bb zp op -> if bb == 0 then zp - 1 else nz + op - 1) b zpos opos
      in scatter (copy bits) dst bits
  in map f64.from_bits bits

-- spec §6 quantile rule on an ascending-sorted array
def quantile [N] (s: [N]f64) (q: f64) : f64 =
  let h = q * f64.i64 (N - 1)
  let lo = i64.f64 (f64.floor h)
  in if lo >= N - 1 then s[N - 1]
     else s[lo] + (h - f64.i64 lo) * (s[lo + 1] - s[lo])

-- ------------------------------------------------------------------
-- null statistics
-- ------------------------------------------------------------------
def nblocks (n: i64) : i64 = (n + 23) / 24

def order_shared (n: i64) (seed: u64) (b: i64) : []i64 =
  shuffle_order (nblocks n) (seed ^ (u64.i64 (b + 1) * golden)) sm_bounded

def own_init (seed: u64) (b: i64) : (u64, u64) =
  pcg_seed (seed ^ (u64.i64 b * 0xD1342543DE82EF95u64)) (u64.i64 b)

def order_own (n: i64) (seed: u64) (b: i64) : []i64 =
  shuffle_order (nblocks n) (own_init seed b) pcg_bounded

def null_shared [n] (x: [n]f64) (y: [n]f64) (lag_max: i64) (B: i64) (seed: u64) : ([]f64, f64, i64) =
  let (xm, xss, xok) = x_info x lag_max
  let (t_obs, lag_obs) = tstat x xm xss xok y
  let tb = map (\b -> (tstat x xm xss xok (permute_y y (order_shared n seed b))).0) (iota B)
  in (tb, t_obs, lag_obs)

def null_own [n] (x: [n]f64) (y: [n]f64) (lag_max: i64) (B: i64) (seed: u64) : []f64 =
  let (xm, xss, xok) = x_info x lag_max
  in map (\b -> (tstat x xm xss xok (permute_y y (order_own n seed b))).0) (iota B)

def pvalue [B] (tb: [B]f64) (t_obs: f64) : f64 =
  let c = i64.sum (map (\t -> if t >= t_obs - 1e-12 then 1i64 else 0i64) tb)
  in f64.i64 (1 + c) / f64.i64 (B + 1)

-- ------------------------------------------------------------------
-- entry points
-- ------------------------------------------------------------------
-- shared-seed SplitMix64 test: (T_obs, lag_obs, p, T_b for b = 0..B-1)
entry shared (x: []f64) (y: []f64) (lag_max: i64) (B: i64) (seed: u64)
    : (f64, i64, f64, []f64) =
  let (tb, t_obs, lag_obs) = null_shared x y lag_max B seed
  in (t_obs, lag_obs, pvalue tb t_obs, tb)

-- same plus the four quantiles (q50,q90,q95,q99) of {T_b} (used by run.sh)
entry shared_full (x: []f64) (y: []f64) (lag_max: i64) (B: i64) (seed: u64)
    : (f64, i64, f64, f64, f64, f64, f64, []f64) =
  let (tb, t_obs, lag_obs) = null_shared x y lag_max B seed
  let s = sort_nonneg tb
  in (t_obs, lag_obs, pvalue tb t_obs,
      quantile s 0.50, quantile s 0.90, quantile s 0.95, quantile s 0.99, tb)

-- independent-PRNG null (PCG-XSH-RR): q50,q90,q95,q99 and the null ECDF at xs
entry own (x: []f64) (y: []f64) (lag_max: i64) (B: i64) (seed: u64) (xs: []f64)
    : (f64, f64, f64, f64, []f64) =
  let tb = null_own x y lag_max B seed
  let s = sort_nonneg tb
  let ecdf = map (\v -> f64.i64 (i64.sum (map (\t -> if t <= v then 1i64 else 0i64) tb))
                        / f64.i64 B) xs
  in (quantile s 0.50, quantile s 0.90, quantile s 0.95, quantile s 0.99, ecdf)

-- T_obs / lag_obs only
entry observed (x: []f64) (y: []f64) (lag_max: i64) : (f64, i64) =
  let (xm, xss, xok) = x_info x lag_max
  in tstat x xm xss xok y

-- diagnostics ------------------------------------------------------
-- SplitMix64 test vector: first output from a given state (0 -> 0xE220A8397B1DCDAF)
entry sm64_first (s: u64) : u64 = (sm_next s).1

entry sm64_stream (s: u64) (n: i64) : []u64 =
  let (_, out) = loop (st, acc) = (s, replicate n 0u64) for i < n do
                   let (st', o) = sm_next st
                   in (st', acc with [i] = o)
  in out

-- block order of permutation b (shared stream) / (own stream)
entry shared_order (n: i64) (seed: u64) (b: i64) : []i64 = order_shared n seed b
entry own_order (n: i64) (seed: u64) (b: i64) : []i64 = order_own n seed b
