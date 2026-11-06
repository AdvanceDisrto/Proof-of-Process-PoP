(* Machine-checked synthetic integer-policy properties only.
   No homotopy type theory, univalence, device authenticity, physics or safety proof. *)
From Coq Require Import ZArith Bool Lia.
Open Scope Z_scope.

Definition nominal (frequency_millihz : Z) : Prop :=
  59900 <= frequency_millihz <= 60100.

Definition accept (frequency_millihz : Z) : bool :=
  (59900 <=? frequency_millihz) && (frequency_millihz <=? 60100).

Theorem accept_sound : forall hz : Z, accept hz = true -> nominal hz.
Proof.
  intros hz H.
  unfold accept in H.
  apply andb_true_iff in H.
  destruct H as [Hlo Hhi].
  apply Z.leb_le in Hlo.
  apply Z.leb_le in Hhi.
  unfold nominal; lia.
Qed.

Theorem accept_complete : forall hz : Z, nominal hz -> accept hz = true.
Proof.
  intros hz H.
  unfold nominal in H.
  destruct H as [Hlo Hhi].
  unfold accept.
  apply andb_true_iff; split.
  - apply Z.leb_le; exact Hlo.
  - apply Z.leb_le; exact Hhi.
Qed.

Theorem below_min_rejected : forall hz : Z, hz < 59900 -> accept hz = false.
Proof.
  intros hz H.
  unfold accept.
  assert (Hlt : (59900 <=? hz) = false).
  { apply Z.leb_gt; lia. }
  rewrite Hlt; reflexivity.
Qed.

Theorem above_max_rejected : forall hz : Z, hz > 60100 -> accept hz = false.
Proof.
  intros hz H.
  unfold accept.
  assert (Hlt : (hz <=? 60100) = false).
  { apply Z.leb_gt; lia. }
  rewrite Hlt.
  apply andb_false_r.
Qed.

Definition next_sequence (previous next : Z) : Prop :=
  next = previous + 1.

Theorem next_sequence_not_replay :
  forall previous next : Z, next_sequence previous next -> previous <> next.
Proof.
  intros previous next H.
  unfold next_sequence in H.
  lia.
Qed.

(* A reversible coordinate encoding does not imply a HoTT equivalence proof. *)
Definition increment (x : Z) : Z := x + 1.
Definition decrement (x : Z) : Z := x - 1.

Theorem encode_decode_roundtrip : forall x : Z, decrement (increment x) = x.
Proof. intros x; unfold increment, decrement; lia. Qed.
Theorem decode_encode_roundtrip : forall x : Z, increment (decrement x) = x.
Proof. intros x; unfold increment, decrement; lia. Qed.
