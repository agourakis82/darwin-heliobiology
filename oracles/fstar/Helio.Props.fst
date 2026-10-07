(*
  Helio.Props -- machine-checked invariants of the numerical core (docs/SIO_CORE_SPEC.md,
  sections 0, 4, 5 and 9).

  ADR-009 criteria
  (1) Written from docs/SIO_CORE_SPEC.md ONLY. Nothing here was read from, or transliterated
      from, the Sounio core (sio/), the Python sources (src/) or the Sounio compiler.
  (2) Proof-carrying language: every claim below is a theorem checked by F* + Z3 for ALL
      inputs (universally quantified), with no admit / assume / assume val / lax mode.
  (3) Toolchain pinned: F* 2026.09.27 (check.sh reads `fstar.exe --version` and fails on any
      mismatch).
  (4) Why a Sounio twin is not enough: a twin only agrees with the core on the sampled
      examples of the gate; these are invariants over ALL inputs (e.g. score monotone in every
      component, ensure_kp_scale idempotent on every list in [0,90]).

  Modelling note. Values are modelled over FStar.Real (real numbers), as in spec section 9:
  the proof abstracts rounding because clip01, sums, and products by non-negative constants
  are monotone under round-to-nearest, so the properties transfer to binary64. FStar.Real was
  adequate (Z3 handles the linear real arithmetic with literal constants), so no rational
  encoding was needed.
*)
module Helio.Props

open FStar.Real

(* ---------------------------------------------------------------- basics (spec 0) *)

let rmax (a b:real) : GTot real = if a >=. b then a else b
let rmin (a b:real) : GTot real = if a <=. b then a else b

(* clip01(x) = min(1, max(0, x)) *)
let clip01 (x:real) : GTot real = rmin 1.0R (rmax 0.0R x)

let in01 (x:real) : GTot bool = 0.0R <=. x && x <=. 1.0R

val clip01_in_unit_interval : x:real -> Lemma (in01 (clip01 x))
let clip01_in_unit_interval x = ()

val clip01_monotone : x:real -> y:real -> Lemma (requires x <=. y) (ensures clip01 x <=. clip01 y)
let clip01_monotone x y = ()

(* ------------------------------------------------- component normalisers (spec 4) *)

type pos_real = d:real{d >. 0.0R}

let rabs_neg (d:real) : GTot real = if d <. 0.0R then 0.0R -. d else 0.0R   (* |min(d,0)| *)

let comp_kp (m:real) : GTot real = clip01 (m /. 9.0R)                    (* mean Kp / 9 *)
let comp_dst (d:real) : GTot real = clip01 (rabs_neg d /. 78.0R)         (* |min(d,0)| / 78 *)
let comp_bz (b:real) : GTot real = clip01 (b /. 8.7R)                    (* mean southward Bz / 8.7 *)
let comp_pressure (p:real) : GTot real = clip01 (p /. 7.30R)
let comp_variability (s:real) : GTot real = clip01 (s /. 1.57R)

(* generic form: clip01(a / d) with refined divisor d > 0 *)
let comp_generic (a:real) (d:pos_real) : GTot real = clip01 (a /. d)

val component_in_unit_interval_generic : a:real -> d:pos_real -> Lemma (in01 (comp_generic a d))
let component_in_unit_interval_generic a d = ()

val component_in_unit_interval_kp : m:real -> Lemma (in01 (comp_kp m))
let component_in_unit_interval_kp m = ()

val component_in_unit_interval_dst : d:real -> Lemma (in01 (comp_dst d))
let component_in_unit_interval_dst d = ()

(* b is the mean southward value, already non-negative *)
val component_in_unit_interval_bz : b:real{b >=. 0.0R} -> Lemma (in01 (comp_bz b))
let component_in_unit_interval_bz b = ()

val component_in_unit_interval_pressure : p:real -> Lemma (in01 (comp_pressure p))
let component_in_unit_interval_pressure p = ()

val component_in_unit_interval_variability : s:real -> Lemma (in01 (comp_variability s))
let component_in_unit_interval_variability s = ()

(* ------------------------------------------------------- strict score (spec 4) *)

let w_kp : real = 0.35R
let w_dst : real = 0.25R
let w_bz : real = 0.20R
let w_pr : real = 0.15R
let w_var : real = 0.05R

let score (kp dst bz pr var:real) : GTot real =
  clip01 (w_kp *. kp +. w_dst *. dst +. w_bz *. bz +. w_pr *. pr +. w_var *. var)

val weights_sum_to_one : unit -> Lemma (w_kp +. w_dst +. w_bz +. w_pr +. w_var == 1.0R)
let weights_sum_to_one () = ()

val weights_nonneg : unit ->
  Lemma (w_kp >=. 0.0R /\ w_dst >=. 0.0R /\ w_bz >=. 0.0R /\ w_pr >=. 0.0R /\ w_var >=. 0.0R)
let weights_nonneg () = ()

(* components fixed in [0,1] *)
type unit_real = x:real{0.0R <=. x /\ x <=. 1.0R}

val score_in_unit_interval : kp:real -> dst:real -> bz:real -> pr:real -> var:real ->
  Lemma (in01 (score kp dst bz pr var))
let score_in_unit_interval kp dst bz pr var = ()

val score_monotone_kp : c:unit_real -> c':unit_real -> dst:unit_real -> bz:unit_real ->
  pr:unit_real -> var:unit_real ->
  Lemma (requires c <=. c') (ensures score c dst bz pr var <=. score c' dst bz pr var)
let score_monotone_kp c c' dst bz pr var = ()

val score_monotone_dst : kp:unit_real -> c:unit_real -> c':unit_real -> bz:unit_real ->
  pr:unit_real -> var:unit_real ->
  Lemma (requires c <=. c') (ensures score kp c bz pr var <=. score kp c' bz pr var)
let score_monotone_dst kp c c' bz pr var = ()

val score_monotone_bz : kp:unit_real -> dst:unit_real -> c:unit_real -> c':unit_real ->
  pr:unit_real -> var:unit_real ->
  Lemma (requires c <=. c') (ensures score kp dst c pr var <=. score kp dst c' pr var)
let score_monotone_bz kp dst c c' pr var = ()

val score_monotone_pressure : kp:unit_real -> dst:unit_real -> bz:unit_real -> c:unit_real ->
  c':unit_real -> var:unit_real ->
  Lemma (requires c <=. c') (ensures score kp dst bz c var <=. score kp dst bz c' var)
let score_monotone_pressure kp dst bz c c' var = ()

val score_monotone_variability : kp:unit_real -> dst:unit_real -> bz:unit_real -> pr:unit_real ->
  c:unit_real -> c':unit_real ->
  Lemma (requires c <=. c') (ensures score kp dst bz pr c <=. score kp dst bz pr c')
let score_monotone_variability kp dst bz pr c c' = ()

(* ------------------------------------------------ ensure_kp_scale (spec 9, item 3) *)

(* maximum of a non-empty list, as a left fold seeded with the head *)
let rec lmax_from (acc:real) (l:list real) : GTot real (decreases l) =
  match l with
  | [] -> acc
  | x :: t -> lmax_from (rmax acc x) t

let lmax (l:list real{Cons? l}) : GTot real = lmax_from (Cons?.hd l) (Cons?.tl l)

let rec map_div10 (l:list real) : Tot (list real) (decreases l) =
  match l with
  | [] -> []
  | x :: t -> (x /. 10.0R) :: map_div10 t

(* m = max; if m > 9.0 divide every element by 10, else unchanged; empty unchanged *)
let ensure_kp_scale (l:list real) : GTot (list real) =
  match l with
  | [] -> []
  | _ -> if lmax l >. 9.0R then map_div10 l else l

(* every element of l lies in [lo, hi] *)
let rec all_in (lo hi:real) (l:list real) : GTot bool (decreases l) =
  match l with
  | [] -> true
  | x :: t -> lo <=. x && x <=. hi && all_in lo hi t

(* lmax_from stays within [lo,hi] when the seed and all elements do *)
let rec lmax_from_bounds (lo hi acc:real) (l:list real)
  : Lemma (requires lo <=. acc /\ acc <=. hi /\ all_in lo hi l)
          (ensures lo <=. lmax_from acc l /\ lmax_from acc l <=. hi)
          (decreases l)
  = match l with
    | [] -> ()
    | x :: t -> lmax_from_bounds lo hi (rmax acc x) t

let lmax_bounds (lo hi:real) (l:list real{Cons? l})
  : Lemma (requires all_in lo hi l) (ensures lo <=. lmax l /\ lmax l <=. hi)
  = lmax_from_bounds lo hi (Cons?.hd l) (Cons?.tl l)

(* every element of l is <= b *)
let rec le_all (b:real) (l:list real) : GTot bool (decreases l) =
  match l with
  | [] -> true
  | x :: t -> x <=. b && le_all b t

let rec lmax_from_ge (acc:real) (l:list real)
  : Lemma (ensures acc <=. lmax_from acc l) (decreases l)
  = match l with
    | [] -> ()
    | x :: t -> lmax_from_ge (rmax acc x) t

(* the fold result bounds every element of the list from above *)
let rec lmax_from_le_all (acc:real) (l:list real)
  : Lemma (ensures le_all (lmax_from acc l) l) (decreases l)
  = match l with
    | [] -> ()
    | x :: t ->
      lmax_from_ge (rmax acc x) t;
      lmax_from_le_all (rmax acc x) t

let lmax_le_all (l:list real{Cons? l}) : Lemma (le_all (lmax l) l) =
  match l with
  | x :: t -> lmax_from_ge x t; lmax_from_le_all x t

let rec all_in_of_le_all (hi:real) (l:list real)
  : Lemma (requires all_in 0.0R 90.0R l /\ le_all hi l /\ hi <=. 9.0R)
          (ensures all_in 0.0R 9.0R l) (decreases l)
  = match l with
    | [] -> ()
    | _ :: t -> all_in_of_le_all hi t

let rec all_in_div10 (l:list real)
  : Lemma (requires all_in 0.0R 90.0R l) (ensures all_in 0.0R 9.0R (map_div10 l)) (decreases l)
  = match l with
    | [] -> ()
    | _ :: t -> all_in_div10 t

let map_div10_cons (l:list real)
  : Lemma (requires Cons? l) (ensures Cons? (map_div10 l)) = ()

val ensure_kp_scale_all_in : l:list real ->
  Lemma (requires all_in 0.0R 90.0R l) (ensures all_in 0.0R 9.0R (ensure_kp_scale l))
let ensure_kp_scale_all_in l =
  match l with
  | [] -> ()
  | _ ->
    lmax_le_all l;
    if lmax l >. 9.0R then all_in_div10 l
    else all_in_of_le_all (lmax l) l

let rec all_in_mem (lo hi:real) (l:list real)
  : Lemma (requires all_in lo hi l)
          (ensures forall (y:real). FStar.List.Tot.memP y l ==> (lo <=. y /\ y <=. hi))
          (decreases l)
  = match l with
    | [] -> ()
    | _ :: t -> all_in_mem lo hi t

(* (iii-a) for every list with all elements in [0,90], all elements of the result are in [0,9] *)
val ensure_kp_scale_in_range : l:list real ->
  Lemma (requires all_in 0.0R 90.0R l)
        (ensures all_in 0.0R 9.0R (ensure_kp_scale l) /\
                 (forall (y:real). FStar.List.Tot.memP y (ensure_kp_scale l) ==>
                                   (0.0R <=. y /\ y <=. 9.0R)))
let ensure_kp_scale_in_range l =
  ensure_kp_scale_all_in l;
  all_in_mem 0.0R 9.0R (ensure_kp_scale l)

(* (iii-b) idempotence, list equality *)
val ensure_kp_scale_idempotent : l:list real ->
  Lemma (requires all_in 0.0R 90.0R l)
        (ensures ensure_kp_scale (ensure_kp_scale l) == ensure_kp_scale l)
let ensure_kp_scale_idempotent l =
  match l with
  | [] -> ()
  | _ ->
    if lmax l >. 9.0R then begin
      let r = map_div10 l in
      map_div10_cons l;
      all_in_div10 l;
      lmax_bounds 0.0R 9.0R r
      (* lmax r <= 9, so ensure r = r *)
    end else ()

(* ------------------------------------------- storm_hours / valid_hours (spec 5, 9.4) *)

(* hourly Kp readings: None = absent, Some x = valid; storm iff x >= 5.0 *)
let rec valid_hours (l:list (option real)) : Tot nat (decreases l) =
  match l with
  | [] -> 0
  | None :: t -> valid_hours t
  | Some _ :: t -> 1 + valid_hours t

let rec storm_hours (l:list (option real)) : GTot nat (decreases l) =
  match l with
  | [] -> 0
  | None :: t -> storm_hours t
  | Some x :: t -> (if x >=. 5.0R then 1 else 0) + storm_hours t

val storm_hours_le_valid_hours : l:list (option real) -> Lemma (storm_hours l <= valid_hours l)
let rec storm_hours_le_valid_hours l =
  match l with
  | [] -> ()
  | _ :: t -> storm_hours_le_valid_hours t

val valid_hours_le_length : l:list (option real) -> Lemma (valid_hours l <= FStar.List.Tot.length l)
let rec valid_hours_le_length l =
  match l with
  | [] -> ()
  | _ :: t -> valid_hours_le_length t
