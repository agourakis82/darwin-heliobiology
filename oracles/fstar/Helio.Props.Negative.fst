(*
  Helio.Props.Negative -- NEGATIVE CONTROL. Every lemma below is deliberately FALSE
  (a mutated variant of a Helio.Props theorem). `check.sh --negative` passes only if F*
  REJECTS each marked lemma (each NEG-n block is checked in isolation on top of the prelude) (NEG-1 .. NEG-5). It shows the
  positive proofs are not vacuous: the same machinery refuses the broken variants.
*)
module Helio.Props.Negative

open FStar.Real

let rmax (a b:real) : GTot real = if a >=. b then a else b
let rmin (a b:real) : GTot real = if a <=. b then a else b
let in01 (x:real) : GTot bool = 0.0R <=. x && x <=. 1.0R

let clip01 (x:real) : GTot real = rmin 1.0R (rmax 0.0R x)
type unit_real = x:real{0.0R <=. x /\ x <=. 1.0R}

(* NEG-1: clip01 without the lower bound is NOT in [0,1] *)
let clip01_nolower (x:real) : GTot real = rmin 1.0R x
val neg1_clip_in_unit_interval : x:real -> Lemma (in01 (clip01_nolower x))
let neg1_clip_in_unit_interval x = ()

(* NEG-2: score with a NEGATIVE weight on kp is NOT monotone in kp *)
let score_negw (kp dst:real) : GTot real = clip01 ((0.0R -. 0.35R) *. kp +. 0.25R *. dst)
val neg2_score_monotone_kp : c:unit_real -> c':unit_real -> dst:unit_real ->
  Lemma (requires c <=. c') (ensures score_negw c dst <=. score_negw c' dst)
let neg2_score_monotone_kp c c' dst = ()

(* NEG-3: weights that sum to 1.05 are not 1 *)
val neg3_weights_sum_to_one : unit -> Lemma (0.35R +. 0.25R +. 0.20R +. 0.15R +. 0.10R == 1.0R)
let neg3_weights_sum_to_one () = ()

(* NEG-4: ensure_kp_scale that only rescales when m > 90 does not land in [0,9] *)
let rec all_in (lo hi:real) (l:list real) : GTot bool (decreases l) =
  match l with
  | [] -> true
  | x :: t -> lo <=. x && x <=. hi && all_in lo hi t
let ensure_bad (m:real) (l:list real) : GTot (list real) =
  if m >. 90.0R then [] else l   (* m is the max; should rescale at m > 9 *)
val neg4_ensure_in_range : m:real -> l:list real ->
  Lemma (requires all_in 0.0R 90.0R l) (ensures all_in 0.0R 9.0R (ensure_bad m l))
let neg4_ensure_in_range m l = ()

(* NEG-5: counting storms over ALL readings but valid hours only over calm ones
   breaks storm <= valid *)
let rec valid_bad (l:list (option real)) : GTot nat (decreases l) =
  match l with
  | [] -> 0
  | None :: t -> valid_bad t
  | Some x :: t -> (if x <. 5.0R then 1 else 0) + valid_bad t
let rec storm (l:list (option real)) : GTot nat (decreases l) =
  match l with
  | [] -> 0
  | None :: t -> storm t
  | Some x :: t -> (if x >=. 5.0R then 1 else 0) + storm t
val neg5_storm_le_valid : l:list (option real) -> Lemma (storm l <= valid_bad l)
let rec neg5_storm_le_valid l =
  match l with
  | [] -> ()
  | _ :: t -> neg5_storm_le_valid t
